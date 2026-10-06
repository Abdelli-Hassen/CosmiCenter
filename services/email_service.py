import smtplib
import logging
import threading
from email.message import EmailMessage
from flask import current_app

logger = logging.getLogger(__name__)

def send_email_notification(app, subject, recipients, html_body):
    """
    Envoie un email en arrière-plan via DavMail (proxy SMTP local).
    """
    def send_async():
        with app.app_context():
            sender = app.config.get('MAIL_DEFAULT_SENDER')
            mail_server = app.config.get('MAIL_SERVER')
            mail_port = app.config.get('MAIL_PORT')
            mail_user = app.config.get('MAIL_USERNAME')
            mail_pass = app.config.get('MAIL_PASSWORD')
            mail_use_tls = app.config.get('MAIL_USE_TLS', False)
            mail_use_ssl = app.config.get('MAIL_USE_SSL', False)

            if not mail_server or not mail_user or not mail_pass:
                logger.warning("Configuration SMTP manquante, email non envoyé.")
                return

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = ", ".join(recipients)
            msg.add_alternative(html_body, subtype='html')

            try:
                if mail_use_ssl:
                    server = smtplib.SMTP_SSL(mail_server, mail_port)
                else:
                    server = smtplib.SMTP(mail_server, mail_port)
                    if mail_use_tls:
                        server.starttls()

                server.login(mail_user, mail_pass)
                server.send_message(msg)
                server.quit()
                logger.info(f"Email envoyé avec succès à {recipients}")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email : {e}")

    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()


