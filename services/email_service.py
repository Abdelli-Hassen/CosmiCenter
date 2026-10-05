import smtplib
import imaplib
import email
import time
import logging
import threading
from email.message import EmailMessage
from email.header import decode_header
from flask import current_app
from models import db, Ticket, Utilisateur, Commentaire, CategorieTicket
from datetime import datetime

logger = logging.getLogger(__name__)

def send_email_notification(app, subject, recipients, html_body):
    """
    Envoie un email en arrière-plan.
    """
    def send_async():
        with app.app_context():
            sender = app.config.get('MAIL_DEFAULT_SENDER')
            mail_server = app.config.get('MAIL_SERVER')
            mail_port = app.config.get('MAIL_PORT')
            mail_user = app.config.get('MAIL_USERNAME')
            mail_pass = app.config.get('MAIL_PASSWORD')
            mail_use_tls = app.config.get('MAIL_USE_TLS')
            
            if not mail_server or not mail_user or not mail_pass:
                logger.warning("Configuration SMTP manquante, email non envoyé.")
                return

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = ", ".join(recipients)
            msg.add_alternative(html_body, subtype='html')
            
            try:
                if mail_use_tls:
                    server = smtplib.SMTP(mail_server, mail_port)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(mail_server, mail_port)
                    
                server.login(mail_user, mail_pass)
                server.send_message(msg)
                server.quit()
                logger.info(f"Email envoyé avec succès à {recipients}")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email : {e}")

    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()


def fetch_emails_and_create_tickets(app):
    """
    Se connecte en IMAP, lit les emails non lus, et crée des tickets ou des commentaires.
    """
    with app.app_context():
        imap_server = app.config.get('IMAP_SERVER')
        imap_port = app.config.get('IMAP_PORT')
        imap_user = app.config.get('IMAP_USERNAME')
        imap_pass = app.config.get('IMAP_PASSWORD')
        imap_ssl = app.config.get('IMAP_USE_SSL')
        
        if not imap_server or not imap_user or not imap_pass:
            logger.warning("Configuration IMAP manquante, arrêt du polling.")
            return
            
        try:
            if imap_ssl:
                mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            else:
                mail = imaplib.IMAP4(imap_server, imap_port)
                
            mail.login(imap_user, imap_pass)
            mail.select("inbox")
            
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                mail.logout()
                return
                
            for num in messages[0].split():
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8", errors="replace")
                            
                        sender_raw = msg.get("From")
                        # Basic parsing of email address
                        import re
                        email_match = re.search(r'<(.+?)>', sender_raw)
                        sender_email = email_match.group(1) if email_match else sender_raw.strip()
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors="replace")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode(errors="replace")
                            
                        process_incoming_email(app, sender_email, subject, body)
                
            mail.logout()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération IMAP : {e}")


def process_incoming_email(app, sender_email, subject, body):
    """
    Transforme un email en ticket, ou l'attache comme commentaire si c'est une réponse.
    """
    with app.app_context():
        # Find user
        utilisateur = Utilisateur.query.filter_by(email=sender_email).first()
        if not utilisateur:
            logger.info(f"Email ignoré : l'expéditeur {sender_email} n'est pas un utilisateur connu.")
            return
            
        # Chercher s'il y a un tag de ticket dans le sujet comme [TICK-20240501-123]
        import re
        ticket_match = re.search(r'\[(TICK-\d+-\w+)\]', subject)
        
        if ticket_match:
            numero = ticket_match.group(1)
            ticket = Ticket.query.filter_by(numero=numero).first()
            if ticket:
                # Ajouter un commentaire
                commentaire = Commentaire(
                    contenu=body.strip(),
                    auteur_id=utilisateur.id,
                    ticket_id=ticket.id
                )
                db.session.add(commentaire)
                db.session.commit()
                logger.info(f"Email ajouté comme commentaire au {ticket.numero} par {utilisateur.email}")
                return
                
        # Sinon, créer un nouveau ticket
        from uuid import uuid4
        numero = f"TICK-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        
        # Trouver une catégorie par défaut, ou None
        default_cat = CategorieTicket.query.first()
        cat_id = default_cat.id if default_cat else None
        
        nouveau_ticket = Ticket(
            titre=subject[:150] if subject else "(Sans sujet)",
            description=body.strip() if body else "(Pas de contenu)",
            priorite='MOYENNE',
            createur_id=utilisateur.id,
            categorie_id=cat_id,
            numero=numero,
            statut='NOUVEAU'
        )
        db.session.add(nouveau_ticket)
        db.session.commit()
        logger.info(f"Nouveau ticket créé via Email : {numero} par {utilisateur.email}")
        
        # Envoi d'une notification de confirmation
        send_email_notification(
            app,
            f"Ticket Créé : [{numero}] {nouveau_ticket.titre}",
            [utilisateur.email],
            f"<p>Bonjour {utilisateur.prenom},</p><p>Votre ticket <b>{numero}</b> a bien été créé depuis votre email.</p>"
        )


def start_imap_polling(app):
    """
    Lance un thread en arrière-plan pour interroger IMAP régulièrement.
    """
    poll_interval = app.config.get('IMAP_POLL_INTERVAL', 60)
    
    def poll_loop():
        # Attendre un peu avant de commencer pour laisser l'app démarrer
        time.sleep(5)
        while True:
            try:
                fetch_emails_and_create_tickets(app)
            except Exception as e:
                logger.error(f"Erreur inattendue dans la boucle IMAP : {e}")
            time.sleep(poll_interval)
            
    thread = threading.Thread(target=poll_loop)
    thread.daemon = True
    thread.start()
    logger.info("Service IMAP polling démarré.")
