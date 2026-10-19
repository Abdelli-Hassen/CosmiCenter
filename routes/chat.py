from functools import wraps

from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import login_required, current_user
from models import db, Message, Utilisateur, Notification
from sqlalchemy import or_, and_, func
from utils.security import like_escape
from datetime import datetime, timedelta

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

MAX_MESSAGE_LENGTH = 4000


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
            'last_message': last_msg.content,
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


@chat_bp.route('/api/send', methods=['POST'])
@login_required
@chat_permission_required
def send_message():
    data = request.get_json(silent=True) or {}
    receiver_id = data.get('receiver_id')
    content = (data.get('content') or '').strip() if isinstance(data.get('content'), str) else ''

    if not receiver_id or not content:
        return jsonify({'error': 'Données invalides'}), 400
    if len(content) > MAX_MESSAGE_LENGTH:
        return jsonify({'error': f'Message trop long (max {MAX_MESSAGE_LENGTH} caractères)'}), 400
    if receiver_id == current_user.id:
        return jsonify({'error': 'Vous ne pouvez pas vous écrire à vous-même'}), 400

    receiver = db.session.get(Utilisateur, receiver_id)
    if receiver is None or not receiver.actif:
        return jsonify({'error': 'Destinataire introuvable ou inactif'}), 404

    msg = Message(sender_id=current_user.id, receiver_id=receiver.id, content=content)
    db.session.add(msg)
    db.session.add(Notification(
        utilisateur_id=receiver.id,
        titre="Nouveau message",
        message=f"{current_user.prenom} {current_user.nom} vous a envoyé un message.",
        type_notification="chat",
        lien=url_for('chat.inbox')
    ))
    db.session.commit()

    return jsonify(msg.to_dict())


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
