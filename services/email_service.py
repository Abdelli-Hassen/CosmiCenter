import smtplib
import re
import ssl
import logging
import threading
from email.message import EmailMessage
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _html_to_text(html_body):
    parser = _TextExtractor()
    try:
        parser.feed(html_body or '')
    except Exception:
        return re.sub(r'<[^>]+>', ' ', html_body or '')
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()


def _clean_header(value):
    """Supprime tout retour à la ligne (anti header-injection)."""
    return re.sub(r'[\r\n]+', ' ', value or '').strip()


def send_email_notification(app, subject, recipients, html_body):
    """
    Envoie un email en arrière-plan via SMTP.
    """
    recipients = [r for r in dict.fromkeys(recipients or []) if r and '@' in r]
    if not recipients:
        return

    def send_async():
        with app.app_context():
            sender = app.config.get('MAIL_DEFAULT_SENDER')
            mail_server = app.config.get('MAIL_SERVER')
            mail_port = app.config.get('MAIL_PORT')
            mail_user = app.config.get('MAIL_USERNAME')
            mail_pass = app.config.get('MAIL_PASSWORD')
            mail_use_tls = app.config.get('MAIL_USE_TLS', False)
            mail_use_ssl = app.config.get('MAIL_USE_SSL', False)
            timeout = app.config.get('MAIL_TIMEOUT', 20)

            if not mail_server or not mail_user or not mail_pass:
                logger.warning("Configuration SMTP manquante, email non envoyé.")
                return

            server = None
            try:
                context = ssl.create_default_context()
                if mail_use_ssl:
                    server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=timeout, context=context)
                else:
                    server = smtplib.SMTP(mail_server, mail_port, timeout=timeout)
                    if mail_use_tls:
                        server.starttls(context=context)

                server.login(mail_user, mail_pass)

                # Envoyer individuellement pour éviter qu'une mauvaise adresse bloque les autres
                for recipient in recipients:
                    msg = EmailMessage()
                    msg['Subject'] = _clean_header(subject)
                    msg['From'] = _clean_header(sender)
                    msg['To'] = _clean_header(recipient)

                    # Version texte (multipart/alternative) puis version HTML
                    msg.set_content(_html_to_text(html_body) or _clean_header(subject))
                    msg.add_alternative(html_body, subtype='html')

                    try:
                        server.send_message(msg)
                        logger.info("Email envoyé avec succès à %s", recipient)
                    except Exception as e:
                        logger.error("Erreur lors de l'envoi de l'email à %s : %s", recipient, e)
            except Exception as e:
                logger.error("Erreur globale de connexion SMTP : %s", e)
            finally:
                if server is not None:
                    try:
                        server.quit()
                    except Exception:
                        pass

    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()
