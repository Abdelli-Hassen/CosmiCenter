import logging
import mimetypes
import os
import re
import uuid
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, url_for, send_file, current_app, abort
from flask_login import login_required, current_user
from models import db, Message, Utilisateur, Notification, ChatGroupe, ChatGroupeMembre
from sqlalchemy import or_, and_, func
from utils.permissions import permission_required
from utils.security import like_escape
from datetime import datetime, timedelta

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000
MAX_GROUP_NAME = 60
MAX_CHAT_FILE_BYTES = 25 * 1024 * 1024   # 25 Mo par fichier, tout type de fichier accepté
INLINE_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}  # affichées dans la page ; le reste est téléchargé


def chat_files_dir():
    path = os.path.join(current_app.instance_path, 'chat_files')  # hors du dossier public /static
    os.makedirs(path, exist_ok=True)
    return path


chat_permission_required = permission_required('messagerie.voir')


def _initials(user):
    return f"{(user.prenom or '?')[0]}{(user.nom or '?')[0]}".upper()


@chat_bp.route('/')
@login_required
@chat_permission_required
def inbox():
    # Ouvrir la messagerie marque les notifications de chat comme lues
    if Notification.query.filter_by(utilisateur_id=current_user.id, type_notification='chat', lue=False) \
            .update({'lue': True, 'date_lecture': datetime.utcnow()}):
        db.session.commit()
    return render_template('chat/inbox.html')


@chat_bp.route('/api/conversations')
@login_required
@chat_permission_required
def get_conversations():
    me = current_user.id

    # Tous les contacts, avec le dernier message et le nombre de non lus, en un nombre fixe de requêtes
    messages = Message.query.filter(Message.groupe_id.is_(None), or_(Message.sender_id == me, Message.receiver_id == me)) \
        .order_by(Message.timestamp.desc()).all()

    last_by_contact = {}
    for m in messages:
        contact_id = m.receiver_id if m.sender_id == me else m.sender_id
        last_by_contact.setdefault(contact_id, m)

    groupes = _conversations_groupes(me)
    if not last_by_contact:
        return jsonify(sorted(groupes, key=lambda x: x['timestamp'] or '', reverse=True))

    unread = dict(
        db.session.query(Message.sender_id, func.count(Message.id))
        .filter(Message.receiver_id == me, Message.groupe_id.is_(None), Message.is_read == False)  # noqa: E712
        .group_by(Message.sender_id).all()
    )
    contacts = {u.id: u for u in Utilisateur.query.filter(Utilisateur.id.in_(list(last_by_contact))).all()}

    conversations = []
    for contact_id, last_msg in last_by_contact.items():
        contact = contacts.get(contact_id)
        if not contact:
            continue
        conversations.append({
            'contact_id': contact.id,
            'contact_name': f"{contact.prenom} {contact.nom}",
            'contact_initials': _initials(contact),
            'photo_profil': contact.photo_profil or None,
            'last_message': last_msg.content or ('📎 ' + (last_msg.fichier_nom or 'Fichier')),
            'timestamp': last_msg.timestamp.isoformat() + 'Z',
            'unread_count': unread.get(contact_id, 0)
        })

    conversations.extend(groupes)
    conversations.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    return jsonify(conversations)


def _conversations_groupes(me):
    """Les groupes de l'utilisateur, au même format que les conversations privées (+ is_group, nb_membres)."""
    memberships = ChatGroupeMembre.query.filter_by(utilisateur_id=me).all()
    if not memberships:
        return []
    ids = [m.groupe_id for m in memberships]
    last = {}
    for m in Message.query.filter(Message.groupe_id.in_(ids)).order_by(Message.timestamp.desc()).all():
        last.setdefault(m.groupe_id, m)
    counts = dict(db.session.query(ChatGroupeMembre.groupe_id, func.count(ChatGroupeMembre.id))
                  .filter(ChatGroupeMembre.groupe_id.in_(ids)).group_by(ChatGroupeMembre.groupe_id).all())
    out = []
    for ms in memberships:
        g = ms.groupe
        lm = last.get(g.id)
        unread = 0
        if lm is not None:
            unread = Message.query.filter(Message.groupe_id == g.id, Message.sender_id != me,
                                          Message.timestamp > (ms.dernier_lu or g.date_creation)).count()
            author = 'Vous' if lm.sender_id == me else (lm.sender.prenom if lm.sender else '')
            preview = f"{author} : " + (lm.content or ('📎 ' + (lm.fichier_nom or 'Fichier')))
        else:
            preview = 'Groupe créé'
        out.append({
            'contact_id': g.id,
            'is_group': True,
            'contact_name': g.nom,
            'contact_initials': (g.nom or '?')[:2].upper(),
            'photo_profil': None,
            'nb_membres': counts.get(g.id, 0),
            'last_message': preview,
            'timestamp': ((lm.timestamp if lm else g.date_creation) or datetime.utcnow()).isoformat() + 'Z',
            'unread_count': unread,
        })
    return out


@chat_bp.route('/api/messages/<contact_id>')
@login_required
@chat_permission_required
def get_messages(contact_id):
    contact = Utilisateur.query.get_or_404(contact_id)

    # Marquer comme lus les messages de ce contact et les notifications de chat
    unread_msgs = Message.query.filter_by(sender_id=contact_id, receiver_id=current_user.id, is_read=False).all()
    for msg in unread_msgs:
        msg.is_read = True

    chat_notifs = Notification.query.filter_by(
        utilisateur_id=current_user.id, type_notification="chat", lue=False).all()
    for n in chat_notifs:
        n.lue = True
        n.date_lecture = datetime.utcnow()

    if unread_msgs or chat_notifs:
        db.session.commit()

    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == contact_id),
            and_(Message.sender_id == contact_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    is_online = False
    if contact.derniere_activite:
        is_online = (datetime.utcnow() - contact.derniere_activite) < timedelta(minutes=5)

    return jsonify({
        'contact': {
            'id': contact.id,
            'name': f"{contact.prenom} {contact.nom}",
            'initials': _initials(contact),
            'photo_profil': contact.photo_profil or None,
            'is_online': is_online
        },
        'messages': [m.to_dict() for m in messages],
        'current_user_id': current_user.id
    })


def _clean_filename(name):
    """Nom affiché : sans chemin ni caractères de contrôle, tronqué ; le nom sur disque est aléatoire."""
    name = os.path.basename((name or '').replace('\\', '/')).replace('\x00', '')
    name = re.sub(r'[\r\n\t]', ' ', name).strip()
    return name[:200] or 'fichier'


@chat_bp.route('/api/send', methods=['POST'])
@login_required
@chat_permission_required
def send_message():
    # Deux formats : JSON (texte seul) ou multipart/form-data (texte et/ou fichier)
    upload = None
    if (request.content_type or '').startswith('multipart/'):
        data = request.form
        upload = request.files.get('file')
        if upload is not None and not upload.filename:
            upload = None
    else:
        data = request.get_json(silent=True) or {}

    receiver_id = data.get('receiver_id')
    groupe_id = data.get('groupe_id')
    raw_content = data.get('content')
    content = raw_content.strip() if isinstance(raw_content, str) else ''

    if not (receiver_id or groupe_id) or (not content and upload is None):
        return jsonify({'error': 'Données invalides'}), 400
    if len(content) > MAX_MESSAGE_LENGTH:
        return jsonify({'error': f'Message trop long (max {MAX_MESSAGE_LENGTH} caractères)'}), 400

    groupe, receiver, destinataires = None, None, []
    if groupe_id:
        groupe = db.session.get(ChatGroupe, groupe_id)
        if groupe is None or _membre(groupe.id) is None:
            return jsonify({'error': "Groupe introuvable ou vous n'en faites plus partie"}), 404
        destinataires = [m.utilisateur for m in groupe.membres
                         if m.utilisateur_id != current_user.id and m.utilisateur and m.utilisateur.actif]
        msg = Message(sender_id=current_user.id, groupe_id=groupe.id, content=content)
    else:
        if receiver_id == current_user.id:
            return jsonify({'error': 'Vous ne pouvez pas vous écrire à vous-même'}), 400
        receiver = db.session.get(Utilisateur, receiver_id)
        if receiver is None or not receiver.actif:
            return jsonify({'error': 'Destinataire introuvable ou inactif'}), 404
        msg = Message(sender_id=current_user.id, receiver_id=receiver.id, content=content)
    saved_path = None
    if upload is not None:
        original = _clean_filename(upload.filename)
        ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
        ext = ext if re.fullmatch(r'[a-z0-9]{1,8}', ext) else ''
        stored = uuid.uuid4().hex + (('.' + ext) if ext else '')
        saved_path = os.path.join(chat_files_dir(), stored)
        upload.save(saved_path)
        size = os.path.getsize(saved_path)
        if size == 0:
            os.remove(saved_path)
            return jsonify({'error': 'Le fichier est vide'}), 400
        if size > MAX_CHAT_FILE_BYTES:
            os.remove(saved_path)
            return jsonify({'error': f'Fichier trop volumineux (max {MAX_CHAT_FILE_BYTES // (1024 * 1024)} Mo)'}), 413
        msg.fichier_nom = original
        msg.fichier_chemin = stored
        msg.fichier_type = (upload.mimetype or mimetypes.guess_type(original)[0] or 'application/octet-stream')[:150]
        msg.fichier_taille = size

    try:
        db.session.add(msg)
        genre = "un fichier" if upload is not None and not content else "un message"
        if groupe is not None:
            # L'expéditeur a lu le groupe jusqu'ici ; les autres membres sont notifiés
            mine = _membre(groupe.id)
            if mine is not None:
                mine.dernier_lu = datetime.utcnow()
            for u in destinataires:
                db.session.add(Notification(
                    utilisateur_id=u.id, titre=f"Groupe « {groupe.nom} »",
                    message=f"{current_user.prenom} {current_user.nom} a envoyé {genre} dans le groupe.",
                    type_notification="chat", lien=url_for('chat.inbox')))
        else:
            db.session.add(Notification(
                utilisateur_id=receiver.id,
                titre="Nouveau message",
                message=f"{current_user.prenom} {current_user.nom} vous a envoyé {genre}.",
                type_notification="chat",
                lien=url_for('chat.inbox')
            ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if saved_path and os.path.isfile(saved_path):
            os.remove(saved_path)
        logger.error(f'Erreur envoi message: {e}', exc_info=True)
        return jsonify({'error': "Erreur lors de l'envoi"}), 500

    return jsonify(msg.to_dict())


@chat_bp.route('/fichier/<message_id>')
@login_required
@chat_permission_required
def telecharger_fichier(message_id):
    """Sert le fichier d'un message, uniquement à l'expéditeur et au destinataire (ou aux membres du groupe)."""
    msg = Message.query.get_or_404(message_id)
    if msg.groupe_id:
        autorise = _membre(msg.groupe_id) is not None
    else:
        autorise = current_user.id in (msg.sender_id, msg.receiver_id)
    if not autorise or not msg.fichier_chemin:
        abort(404)
    path = os.path.join(chat_files_dir(), os.path.basename(msg.fichier_chemin))
    if not os.path.isfile(path):
        abort(404)
    ext = msg.fichier_chemin.rsplit('.', 1)[-1].lower() if '.' in msg.fichier_chemin else ''
    inline = ext in INLINE_IMAGE_EXTENSIONS and request.args.get('download') != '1'
    resp = send_file(path, mimetype=mimetypes.guess_type('x.' + ext)[0] or 'application/octet-stream',
                     as_attachment=not inline, download_name=msg.fichier_nom or 'fichier')
    resp.headers['Content-Security-Policy'] = "sandbox; default-src 'none'; img-src 'self' data:"
    resp.headers['Cache-Control'] = 'private, max-age=3600'
    return resp

@chat_bp.route('/api/users')
@login_required
@chat_permission_required
def get_users():
    q = request.args.get('q', '').strip()
    query = Utilisateur.query.filter(Utilisateur.id != current_user.id, Utilisateur.actif == True)  # noqa: E712
    if q:
        like_pat = f"%{like_escape(q)}%"
        query = query.filter(
            or_(
                Utilisateur.prenom.ilike(like_pat, escape='\\'),
                Utilisateur.nom.ilike(like_pat, escape='\\'),
                (func.concat(Utilisateur.prenom, ' ', Utilisateur.nom)).ilike(like_pat, escape='\\'),
                (func.concat(Utilisateur.nom, ' ', Utilisateur.prenom)).ilike(like_pat, escape='\\'),
                Utilisateur.email.ilike(like_pat, escape='\\')
            )
        )
    users = query.order_by(Utilisateur.prenom.asc(), Utilisateur.nom.asc()).limit(200).all()
    return jsonify([{
        'id': u.id,
        'name': f"{u.prenom} {u.nom}",
        'initials': _initials(u),
        'photo_profil': u.photo_profil or None,
        'poste': u.poste or '',
        'departement': u.departement.nom if u.departement else (u.pdv.nom if u.pdv else '')
    } for u in users])


# ───────────────────────── Groupes de discussion ─────────────────────────
def _membre(groupe_id, user_id=None):
    """Appartenance de l'utilisateur (par défaut l'utilisateur connecté) au groupe, ou None."""
    return ChatGroupeMembre.query.filter_by(groupe_id=groupe_id, utilisateur_id=user_id or current_user.id).first()


def _groupe_ou_404(groupe_id, admin=False):
    """Le groupe si l'utilisateur en est membre (et administrateur si `admin`), sinon 404 / 403."""
    groupe = db.session.get(ChatGroupe, groupe_id)
    mine = _membre(groupe_id) if groupe else None
    if groupe is None or mine is None:
        abort(404)
    if admin and not mine.est_admin:
        abort(403)
    return groupe, mine


def _groupe_dict(groupe, mine):
    me = current_user.id
    membres = sorted([m for m in groupe.membres if m.utilisateur],
                     key=lambda m: ((m.utilisateur.prenom or '').lower(), (m.utilisateur.nom or '').lower()))
    return {
        'id': groupe.id,
        'name': groupe.nom,
        'initials': (groupe.nom or '?')[:2].upper(),
        'is_admin': bool(mine.est_admin),
        'nb_membres': len(membres),
        'createur': f"{groupe.createur.prenom} {groupe.createur.nom}" if groupe.createur else None,
        'date_creation': (groupe.date_creation.isoformat() + 'Z') if groupe.date_creation else None,
        'membres': [{
            'id': m.utilisateur_id,
            'name': f"{m.utilisateur.prenom} {m.utilisateur.nom}",
            'initials': _initials(m.utilisateur),
            'photo_profil': m.utilisateur.photo_profil or None,
            'est_admin': bool(m.est_admin),
            'est_moi': m.utilisateur_id == me,
        } for m in membres],
    }


def _utilisateurs_valides(ids):
    """Utilisateurs actifs correspondant aux identifiants reçus (doublons et valeurs invalides ignorés)."""
    if not isinstance(ids, list):
        return []
    propres = list({i for i in ids if isinstance(i, str)})[:200]
    if not propres:
        return []
    return Utilisateur.query.filter(Utilisateur.id.in_(propres), Utilisateur.actif == True).all()  # noqa: E712


def _nom_groupe(data):
    nom = re.sub(r'\s+', ' ', str((data or {}).get('nom') or '')).strip()
    if not nom:
        return None, "Donnez un nom au groupe."
    if len(nom) > MAX_GROUP_NAME:
        return None, f"Nom trop long ({MAX_GROUP_NAME} caractères maximum)."
    return nom, None


def _notifier_ajout(user, groupe):
    db.session.add(Notification(
        utilisateur_id=user.id, titre="Nouveau groupe",
        message=f"{current_user.prenom} {current_user.nom} vous a ajouté au groupe « {groupe.nom} ».",
        type_notification="chat", lien=url_for('chat.inbox')))


@chat_bp.route('/api/groupes', methods=['POST'])
@login_required
@chat_permission_required
def creer_groupe():
    data = request.get_json(silent=True) or {}
    nom, err = _nom_groupe(data)
    if err:
        return jsonify({'error': err}), 400
    autres = [u for u in _utilisateurs_valides(data.get('membres')) if u.id != current_user.id]
    if not autres:
        return jsonify({'error': "Choisissez au moins une personne à ajouter."}), 400
    try:
        groupe = ChatGroupe(nom=nom, createur_id=current_user.id)
        db.session.add(groupe)
        db.session.flush()
        db.session.add(ChatGroupeMembre(groupe_id=groupe.id, utilisateur_id=current_user.id, est_admin=True))
        for u in autres:
            db.session.add(ChatGroupeMembre(groupe_id=groupe.id, utilisateur_id=u.id))
            _notifier_ajout(u, groupe)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Création de groupe impossible: {e}', exc_info=True)
        return jsonify({'error': "Erreur lors de la création du groupe"}), 500
    return jsonify({'id': groupe.id, 'name': groupe.nom})


@chat_bp.route('/api/groupe/<groupe_id>')
@login_required
@chat_permission_required
def get_groupe(groupe_id):
    """Messages et membres d'un groupe ; l'ouvrir le marque comme lu."""
    groupe, mine = _groupe_ou_404(groupe_id)
    mine.dernier_lu = datetime.utcnow()
    if not any(m.est_admin for m in groupe.membres):  # l'administrateur a été supprimé : le plus ancien membre le devient
        ancien = min(groupe.membres, key=lambda m: m.date_ajout or datetime.utcnow())
        ancien.est_admin = True
        if ancien.utilisateur_id == current_user.id:
            mine.est_admin = True
    for n in Notification.query.filter_by(utilisateur_id=current_user.id, type_notification="chat", lue=False).all():
        n.lue = True
        n.date_lecture = datetime.utcnow()
    db.session.commit()
    messages = Message.query.filter_by(groupe_id=groupe.id).order_by(Message.timestamp.asc()).all()
    return jsonify({
        'groupe': _groupe_dict(groupe, mine),
        'messages': [m.to_dict() for m in messages],
        'current_user_id': current_user.id,
    })


@chat_bp.route('/api/groupe/<groupe_id>/renommer', methods=['POST'])
@login_required
@chat_permission_required
def renommer_groupe(groupe_id):
    groupe, _ = _groupe_ou_404(groupe_id, admin=True)
    nom, err = _nom_groupe(request.get_json(silent=True))
    if err:
        return jsonify({'error': err}), 400
    groupe.nom = nom
    db.session.commit()
    return jsonify({'ok': True, 'name': nom})


@chat_bp.route('/api/groupe/<groupe_id>/membres', methods=['POST'])
@login_required
@chat_permission_required
def ajouter_membres(groupe_id):
    groupe, _ = _groupe_ou_404(groupe_id, admin=True)
    deja = {m.utilisateur_id for m in groupe.membres}
    nouveaux = [u for u in _utilisateurs_valides((request.get_json(silent=True) or {}).get('membres')) if u.id not in deja]
    if not nouveaux:
        return jsonify({'error': "Aucune nouvelle personne à ajouter."}), 400
    for u in nouveaux:
        db.session.add(ChatGroupeMembre(groupe_id=groupe.id, utilisateur_id=u.id))
        _notifier_ajout(u, groupe)
    db.session.commit()
    return jsonify({'ok': True, 'ajoutes': len(nouveaux)})


def _supprimer_fichiers(chemins):
    for chemin in chemins:
        path = os.path.join(chat_files_dir(), os.path.basename(chemin))
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                logger.warning('Fichier de chat non supprimé: %s', path)


def _fichiers_du_groupe(groupe):
    return [m.fichier_chemin for m in Message.query.filter_by(groupe_id=groupe.id).all() if m.fichier_chemin]


def _retirer(groupe, membre):
    """Retire un membre ; sans administrateur restant, le plus ancien membre le devient ; groupe vide = supprimé.
    Renvoie les fichiers à effacer du disque après le commit."""
    db.session.delete(membre)
    db.session.flush()
    restants = ChatGroupeMembre.query.filter_by(groupe_id=groupe.id).order_by(ChatGroupeMembre.date_ajout.asc()).all()
    if not restants:
        fichiers = _fichiers_du_groupe(groupe)
        db.session.delete(groupe)
        return fichiers
    if not any(m.est_admin for m in restants):
        restants[0].est_admin = True
    return []


@chat_bp.route('/api/groupe/<groupe_id>/retirer', methods=['POST'])
@login_required
@chat_permission_required
def retirer_membre(groupe_id):
    """Un administrateur retire un autre membre."""
    groupe, _ = _groupe_ou_404(groupe_id, admin=True)
    user_id = (request.get_json(silent=True) or {}).get('user_id')
    cible = _membre(groupe.id, user_id) if isinstance(user_id, str) else None
    if cible is None or user_id == current_user.id:
        return jsonify({'error': "Membre introuvable."}), 404
    _retirer(groupe, cible)
    db.session.commit()
    return jsonify({'ok': True})


@chat_bp.route('/api/groupe/<groupe_id>/quitter', methods=['POST'])
@login_required
@chat_permission_required
def quitter_groupe(groupe_id):
    groupe, mine = _groupe_ou_404(groupe_id)
    fichiers = _retirer(groupe, mine)
    db.session.commit()
    _supprimer_fichiers(fichiers)
    return jsonify({'ok': True})


@chat_bp.route('/api/groupe/<groupe_id>/supprimer', methods=['POST'])
@login_required
@chat_permission_required
def supprimer_groupe(groupe_id):
    """Supprime le groupe, ses messages et leurs fichiers (administrateur)."""
    groupe, _ = _groupe_ou_404(groupe_id, admin=True)
    fichiers = _fichiers_du_groupe(groupe)
    db.session.delete(groupe)
    db.session.commit()
    _supprimer_fichiers(fichiers)
    return jsonify({'ok': True})
