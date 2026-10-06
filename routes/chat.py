from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Message, Utilisateur
from sqlalchemy import or_, and_, func, desc
from datetime import datetime

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/')
@login_required
def inbox():
    return render_template('chat/inbox.html')

@chat_bp.route('/api/conversations')
@login_required
def get_conversations():
    # Find all users the current user has chatted with
    # This involves finding distinct sender_ids when receiver=current and distinct receiver_ids when sender=current
    sent_to = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id)
    received_from = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id)
    
    contact_ids = set([r[0] for r in sent_to.all()] + [r[0] for r in received_from.all()])
    
    conversations = []
    for contact_id in contact_ids:
        contact = Utilisateur.query.get(contact_id)
        if not contact:
            continue
            
        # Get last message
        last_msg = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == contact_id),
                and_(Message.sender_id == contact_id, Message.receiver_id == current_user.id)
            )
        ).order_by(Message.timestamp.desc()).first()
        
        # Count unread
        unread_count = Message.query.filter_by(sender_id=contact_id, receiver_id=current_user.id, is_read=False).count()
        
        conversations.append({
            'contact_id': contact.id,
            'contact_name': f"{contact.prenom} {contact.nom}",
            'contact_initials': f"{contact.prenom[0]}{contact.nom[0]}".upper(),
            'photo_profil': contact.photo_profil if contact.photo_profil else None,
            'last_message': last_msg.content if last_msg else '',
            'timestamp': last_msg.timestamp.isoformat() + 'Z' if last_msg else None,
            'unread_count': unread_count
        })
        
    # Sort by recent message
    conversations.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    return jsonify(conversations)

@chat_bp.route('/api/messages/<contact_id>')
@login_required
def get_messages(contact_id):
    # Mark messages as read
    unread_msgs = Message.query.filter_by(sender_id=contact_id, receiver_id=current_user.id, is_read=False).all()
    for msg in unread_msgs:
        msg.is_read = True
        
    from models import Notification
    chat_notifs = Notification.query.filter_by(
        utilisateur_id=current_user.id, 
        type_notification="chat", 
        lue=False
    ).all()
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
    
    contact = Utilisateur.query.get_or_404(contact_id)
    
    is_online = False
    if contact.derniere_activite:
        is_online = (datetime.utcnow() - contact.derniere_activite) < timedelta(minutes=5)
        
    return jsonify({
        'contact': {
            'id': contact.id,
            'name': f"{contact.prenom} {contact.nom}",
            'initials': f"{contact.prenom[0]}{contact.nom[0]}".upper(),
            'photo_profil': contact.photo_profil if contact.photo_profil else None,
            'is_online': is_online
        },
        'messages': [m.to_dict() for m in messages],
        'current_user_id': current_user.id
    })

@chat_bp.route('/api/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not receiver_id or not content:
        return jsonify({'error': 'Données invalides'}), 400
        
    msg = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(msg)
    
    # Create notification for chat
    from models import Notification
    from flask import url_for
    notif = Notification(
        utilisateur_id=receiver_id,
        titre="Nouveau message",
        message=f"{current_user.prenom} {current_user.nom} vous a envoyé un message.",
        type_notification="chat",
        lien=url_for('chat.inbox')
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify(msg.to_dict())

@chat_bp.route('/api/users')
@login_required
def get_users():
    users = Utilisateur.query.filter(Utilisateur.id != current_user.id, Utilisateur.actif == True).all()
    return jsonify([{
        'id': u.id,
        'name': f"{u.prenom} {u.nom}",
        'initials': f"{u.prenom[0]}{u.nom[0]}".upper(),
        'photo_profil': u.photo_profil if u.photo_profil else None
    } for u in users])
