import smtplib
import imaplib
import email
import re
import ssl
import time
import logging
import threading
from email.message import EmailMessage
from email.header import decode_header, make_header
from email.utils import parseaddr
from html import escape
from html.parser import HTMLParser

from models import db, Ticket, Utilisateur, Commentaire, CategorieTicket

logger = logging.getLogger(__name__)

_NUMERO_RE = re.compile(r'\[#?(\d+)\]')


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
    Envoie le même email à plusieurs destinataires, en arrière-plan via SMTP.
    """
    recipients = [r for r in dict.fromkeys(recipients or []) if r and '@' in r]
    send_email_batch(app, subject, [(r, html_body) for r in recipients])


def send_email_batch(app, subject, items):
    """
    Envoie un email par destinataire, chacun avec son propre corps HTML (une seule connexion SMTP).
    `items` : liste de (adresse, corps_html). Même sujet pour tous.
    """
    items = [(r, h) for r, h in items if r and '@' in r]
    if not items:
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
                for recipient, html_body in items:
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


def send_ticket_emails(app, ticket, createur, destinataires, ticket_url=None):
    """
    Deux e-mails complets pour un nouveau ticket :
      - « Ticket envoyé » pour le créateur (toujours) ;
      - « Ticket reçu » pour chaque destinataire qui n'a pas coupé les notifications e-mail.
    À appeler dans un contexte d'application ; le ticket doit déjà être enregistré (checklist, pièces jointes).
    """
    from flask import render_template
    morceaux = []
    if ticket.assigne_a:
        morceaux.append(ticket.assigne_a.nom_complet)
    elif ticket.departement:
        morceaux.append(f"tout le département {ticket.departement.nom}")
    if ticket.departements_collab:
        morceaux.append("département(s) " + ', '.join(d.nom for d in ticket.departements_collab))
    if ticket.collaborateurs:
        morceaux.append(', '.join(u.nom_complet for u in ticket.collaborateurs))
    a_qui = ' ; '.join(morceaux)

    def corps(mode, destinataire):
        return render_template('emails/ticket.html', ticket=ticket, mode=mode, destinataire=destinataire,
                               a_qui=a_qui, ticket_url=ticket_url)

    send_email_batch(app, f"Ticket envoyé : [#{ticket.numero}] {ticket.titre}",
                     [(createur.email, corps('envoye', createur))])
    recus = [u for u in destinataires if u.email and u.id != createur.id and u.notifications_email is not False]
    send_email_batch(app, f"Ticket reçu : [#{ticket.numero}] {ticket.titre}",
                     [(u.email, corps('recu', u)) for u in recus])


def _extract_body(msg):
    """Corps texte brut d'un message (première partie text/plain), robuste aux pièces jointes."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if payload is not None:
                    return payload.decode(part.get_content_charset() or 'utf-8', errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or 'utf-8', errors="replace") if payload else ""


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

        mail = None
        try:
            if imap_ssl:
                mail = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=ssl.create_default_context(),
                                         timeout=30)
            else:
                mail = imaplib.IMAP4(imap_server, imap_port, timeout=30)

            mail.login(imap_user, imap_pass)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                return

            for num in messages[0].split():
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue

                for response_part in msg_data:
                    if not isinstance(response_part, tuple):
                        continue
                    msg = email.message_from_bytes(response_part[1])
                    try:
                        subject = str(make_header(decode_header(msg.get("Subject") or "")))
                    except Exception:
                        subject = msg.get("Subject") or ""
                    sender_email = parseaddr(msg.get("From") or "")[1].strip().lower()
                    if not sender_email:
                        continue
                    process_incoming_email(app, sender_email, subject, _extract_body(msg))
        except Exception as e:
            logger.error("Erreur lors de la récupération IMAP : %s", e)
        finally:
            if mail is not None:
                try:
                    mail.logout()
                except Exception:
                    pass


def process_incoming_email(app, sender_email, subject, body):
    """
    Transforme un email en ticket, ou l'attache comme commentaire si c'est une réponse.
    Seuls les expéditeurs correspondant à un utilisateur actif sont acceptés.
    """
    with app.app_context():
        utilisateur = Utilisateur.query.filter(
            db.func.lower(Utilisateur.email) == sender_email.lower(), Utilisateur.actif.is_(True)
        ).first()
        if not utilisateur:
            logger.info("Email ignoré : expéditeur inconnu ou inactif (%s).", sender_email)
            return

        subject = _clean_header(subject)
        ticket_match = _NUMERO_RE.search(subject)

        if ticket_match:
            ticket = Ticket.query.filter_by(numero=ticket_match.group(1)).first()
            if ticket:
                from utils.permissions import can_access_ticket
                if can_access_ticket(utilisateur, ticket):
                    commentaire = Commentaire(
                        contenu=(body or '').strip()[:10000] or "(Pas de contenu)",
                        auteur_id=utilisateur.id,
                        ticket_id=ticket.id
                    )
                    db.session.add(commentaire)
                    db.session.commit()
                    logger.info("Email ajouté comme commentaire au ticket %s", ticket.numero)
                    return
                logger.warning("Email refusé : l'expéditeur n'a pas accès au ticket %s", ticket.numero)
                return

        numero = Ticket.generer_numero()

        default_cat = CategorieTicket.query.filter_by(actif=True).first()
        nouveau_ticket = Ticket(
            titre=(subject[:190] if subject else "(Sans sujet)"),
            description=(body or '').strip() or "(Pas de contenu)",
            type_ticket='demande',
            priorite='moyenne',
            createur_id=utilisateur.id,
            categorie_id=default_cat.id if default_cat else None,
            departement_id=default_cat.departement_id if default_cat else None,
            numero=numero,
            statut='nouveau'
        )
        db.session.add(nouveau_ticket)
        db.session.commit()
        logger.info("Nouveau ticket créé via email : %s", numero)

        dest = []
        if nouveau_ticket.departement_id:
            from models import Departement
            dept = db.session.get(Departement, nouveau_ticket.departement_id)
            dest = [u for u in (dept.membres if dept else []) if u.actif]
        base = app.config.get('PUBLIC_BASE_URL')
        url = (base + '/tickets/' + nouveau_ticket.id) if base else None
        send_ticket_emails(app, nouveau_ticket, utilisateur, dest, url)


def start_imap_polling(app):
    """
    Lance un thread en arrière-plan pour interroger IMAP régulièrement.
    """
    poll_interval = app.config.get('IMAP_POLL_INTERVAL', 60)

    def poll_loop():
        time.sleep(5)
        while True:
            try:
                fetch_emails_and_create_tickets(app)
            except Exception as e:
                logger.error("Erreur inattendue dans la boucle IMAP : %s", e)
            time.sleep(poll_interval)

    thread = threading.Thread(target=poll_loop)
    thread.daemon = True
    thread.start()
    logger.info("Service IMAP polling démarré.")
