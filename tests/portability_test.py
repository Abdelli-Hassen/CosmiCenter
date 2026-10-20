"""Vérifie que le projet est portable : AUCUN chemin absolu (C:\\..., /Users/..., /home/nom/...)
ni dans le code/les gabarits/les scripts, ni dans les données de la base, ni dans le .env.

    venv\\Scripts\\python.exe tests\\portability_test.py

Exceptions assumées : `deploy/` (emplacements standards du serveur Ubuntu : /opt, /etc, /var, configurables par variable),
`tests/` (ce fichier contient les motifs recherchés) et les fichiers générés (venv, logs, uploads).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))


SKIP_DIRS = {"venv", ".git", "logs", "instance", "__pycache__", "node_modules", "tests", "deploy"}
SKIP_PREFIXES = (os.path.join("static", "uploads"), os.path.join("static", "images"))
EXTENSIONS = {".py", ".html", ".js", ".css", ".bat", ".sh", ".md", ".txt", ".json", ".yml", ".yaml", ".cfg", ".ini", ".example"}
# lecteur Windows (C:\ ou C:/ – jamais « https:// »), dossiers utilisateur Windows/Mac/Linux, partage réseau
ABS = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])|[\"'`\s(=]/(Users|home)/[A-Za-z0-9_.-]+|\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_$.-]+")

hits = []
scanned = 0
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    rel_base = os.path.relpath(base, ROOT)
    if rel_base.startswith(SKIP_PREFIXES):
        dirs[:] = []
        continue
    for name in files:
        ext = os.path.splitext(name)[1].lower()
        if ext not in EXTENSIONS and name not in (".env.example", ".gitignore", ".gitattributes"):
            continue
        path = os.path.join(base, name)
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            if ABS.search(line):
                hits.append(f"{os.path.relpath(path, ROOT)}:{n}: {line.strip()[:90]}")
check("source files scanned", scanned > 100, scanned)
check("no absolute path in code, templates, scripts or docs", not hits, "; ".join(hits[:5]))

# .env : aucune valeur ne doit ressembler à un chemin absolu (clés seules affichées, jamais les valeurs)
env_path = os.path.join(ROOT, ".env")
if os.path.exists(env_path):
    from dotenv import dotenv_values
    bad = [k for k, v in dotenv_values(env_path).items() if v and ABS.search(" " + v)]
    check(".env has no absolute path value", not bad, ", ".join(bad))
    upload = dotenv_values(env_path).get("UPLOAD_FOLDER") or "static/uploads"
    check("UPLOAD_FOLDER is relative and inside static/", not os.path.isabs(upload) and upload.replace("\\", "/").startswith("static/"), upload)

# Base de données : aucune valeur texte ne doit contenir un chemin absolu
from app import create_app
from models import db

app = create_app("development")
with app.app_context():
    cols = db.session.execute(db.text(
        "select table_name, column_name from information_schema.columns "
        "where table_schema='public' and data_type in ('character varying','text')")).fetchall()
    found = []
    for table, col in cols:
        n = db.session.execute(db.text(
            f'select count(*) from "{table}" where "{col}" ~ :p'),
            {"p": r"(^|[\s\"'])([A-Za-z]:[\\/]|/(Users|home|opt|var|tmp)/|\\\\[A-Za-z0-9_.-]+\\)"}).scalar()
        if n:
            found.append(f"{table}.{col}={n}")
    check(f"no absolute path stored in the database ({len(cols)} text columns checked)", not found, ", ".join(found))

    # chemins de fichiers enregistrés : relatifs, et les fichiers existent bien dans le dossier du projet
    missing = []
    for table, col, base in (("utilisateurs", "photo_profil", os.path.join("static", "uploads")),
                             ("pieces_jointes", "chemin", "static"),
                             ("messages", "fichier_chemin", os.path.join("instance", "chat_files"))):
        for (value,) in db.session.execute(db.text(f'select "{col}" from "{table}" where "{col}" is not null and "{col}" <> \'\'')):
            if not os.path.exists(os.path.join(ROOT, base, value)):
                missing.append(f"{table}:{value}")
    check("every file referenced in the database exists under the project folder", not missing, ", ".join(missing[:5]))

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
