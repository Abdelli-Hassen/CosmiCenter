from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE pieces_jointes ADD COLUMN commentaire_id VARCHAR(36) REFERENCES commentaires(id) ON DELETE CASCADE;'))
        db.session.commit()
        print("Success")
    except Exception as e:
        print("Error:", e)
