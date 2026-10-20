"""Vérifie la connexion à la base PostgreSQL définie par DATABASE_URL (.env) et liste les tables."""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL n'est pas défini (voir .env).")
url = url.replace("postgresql+psycopg://", "postgresql://", 1)

with psycopg.connect(url, connect_timeout=5) as conn:
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Connexion OK - {len(tables)} table(s) : {', '.join(tables)}")
