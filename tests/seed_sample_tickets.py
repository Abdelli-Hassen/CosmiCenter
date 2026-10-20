"""Données d'exemple pour contrôler visuellement les rapports.
   venv\Scripts\python.exe tests\seed_sample_tickets.py seed    # ajoute 140 tickets « ZZR… »
   venv\Scripts\python.exe tests\seed_sample_tickets.py clean   # les supprime (retour à la base d'origine)
"""
import os, sys, random
from datetime import datetime, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Ticket, Departement, PointDeVente, CategorieTicket

app = create_app("development")
random.seed(11)
with app.app_context():
    if sys.argv[1] == "clean":
        n = Ticket.query.filter(Ticket.numero.like("ZZR%")).delete(synchronize_session=False)
        db.session.commit(); print("removed", n, "total now", Ticket.query.count()); sys.exit()
    admin = Utilisateur.query.filter_by(email="admin@example.com").first() or Utilisateur.query.first()
    depts = Departement.query.filter_by(actif=True).all()[:5]
    pdvs = PointDeVente.query.all()
    cats = CategorieTicket.query.all()
    agents = Utilisateur.query.filter_by(actif=True).limit(4).all()
    now = datetime.utcnow()
    for i in range(140):
        created = now - timedelta(days=random.uniform(0, 29))
        created = created.replace(hour=random.choice([8, 9, 10, 10, 11, 14, 15, 16, 18]))
        d = random.choice(depts)
        dc = [c for c in cats if c.departement_id == d.id]
        statut = random.choices(["nouveau", "en_cours", "en_attente", "resolu", "ferme", "annule"], [3, 2, 1, 7, 3, 1])[0]
        due = created + timedelta(days=random.choice([1, 2, 3]))
        t = Ticket(numero=f"ZZR{i}", titre=f"Exemple de ticket {i}", description="x", type_ticket=random.choice(["incident", "incident", "demande", "besoin"]),
                   priorite=random.choice(["basse", "moyenne", "haute", "urgente"]), statut=statut, createur_id=admin.id, departement_id=d.id,
                   categorie_id=random.choice(dc).id if dc else None, assigne_a_id=random.choice(agents).id if random.random() > 0.2 else None,
                   date_creation=created, date_echeance=due, pdv_id=random.choice(pdvs).id if pdvs and random.random() > 0.25 else None,
                   temps_premiere_reponse_minutes=random.randint(5, 240))
        if statut in ("resolu", "ferme"):
            res = created + timedelta(hours=random.uniform(1, 60))
            t.date_resolution = res; t.date_fermeture = res
            t.temps_resolution_minutes = int((res - created).total_seconds() / 60)
            t.sla_respecte = res <= due
            if random.random() > 0.4:
                t.satisfaction = random.choice([1, 2, 4, 5, 5, 4, 3])
                t.commentaire_satisfaction = random.choice(["Rapide et efficace", "Trop long à résoudre", "Très bon suivi"]) if random.random() > 0.5 else None
        db.session.add(t)
    db.session.commit(); print("seeded; total", Ticket.query.count())
