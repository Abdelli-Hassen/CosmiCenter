"""Requêtes SQL en lecture seule : venv\Scripts\python.exe tests\dbq.py "select ..." "select ..." """
import os
import sys

import psycopg
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url = dotenv_values(os.path.join(ROOT, ".env"))["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, options="-c default_transaction_read_only=on") as c:
    for q in sys.argv[1:]:
        cur = c.execute(q)
        print("-- " + q[:110])
        for r in cur.fetchall():
            print("  ", r)