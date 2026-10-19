import logging
import mimetypes
import os
import re
import uuid
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, url_for, send_file, current_app, abort
from flask_login import login_required, current_user
from models import db, Message, Utilisateur, Notification
from sqlalchemy import or_, and_, func
from utils.security import like_escape
from datetime import datetime, timedelta

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000
MAX_CHAT_FILE_BYTES = 25 * 1024 * 1024   # 25 Mo par fichier, tout type de fichier accepté
INLINE_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}  # affichées dans la page ; le reste est téléchargé


def chat_files_dir():
    path = os.path.join(current_app.instance_path, 'chat_files')  # hors du dossier public /static
    os.makedirs(path, exist_ok=True)
    return path


def chat_permission_required(f):
    """La messagerie est réservée aux rôles disposant de la permission messagerie.voir."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.has_permission('messagerie.voir'):
            if request.path.startswith('/chat/api/'):
                return jsonify({'error': 'Accès non autorisé'}), 403
            from flask import flash, redirect
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated


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
    messages = Message.query.filter(or_(Message.sender_id == me, Message.receiver_id == me)) \
        .order_by(Message.timestamp.desc()).all()

    last_by_contact = {}
    for m in messages:
        contact_id = m.receiver_id if m.sender_id == me else m.sender_id
        last_by_contact.setdefault(contact_id, m)

    if not last_by_contact:
        return jsonify([])

    unread = dict(
        db.session.query(Message.sender_id, func.count(Message.id))
        .filter(Message.receiver_id == me, Message.is_read == False)  # noqa: E712
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

    conversations.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    return jsonify(conversations)


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
    raw_content = data.get('content')
    content = raw_content.strip() if isinstance(raw_content, str) else ''

    if not receiver_id or (not content and upload is None):
        return jsonify({'error': 'Données invalides'}), 400
    if len(content) > MAX_MESSAGE_LENGTH:
        return jsonify({'error': f'Message trop long (max {MAX_MESSAGE_LENGTH} caractères)'}), 400
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
        db.session.add(Notification(
            utilisateur_id=receiver.id,
            titre="Nouveau message",
            message=f"{current_user.prenom} {current_user.nom} vous a envoyé " + ("un fichier." if upload is not None and not content else "un message."),
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
    """Sert le fichier d'un message, uniquement à l'expéditeur et au destinataire."""
    msg = Message.query.get_or_404(message_id)
    if current_user.id not in (msg.sender_id, msg.receiver_id) or not msg.fichier_chemin:
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
