from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE utilisateurs ADD COLUMN pdv_id VARCHAR(36) REFERENCES points_de_vente(id) ON DELETE SET NULL;'))
        db.session.execute(text('ALTER TABLE tickets ADD COLUMN pdv_id VARCHAR(36) REFERENCES points_de_vente(id) ON DELETE SET NULL;'))
        db.session.commit()
        print("Colonnes pdv_id ajoutees avec succes !")
    except Exception as e:
        print("Erreur:", e)
