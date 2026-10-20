import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app

app = create_app("production")           # exactement ce que serve.py exécute sur le serveur
print("debug:", app.debug, "| TEMPLATES_AUTO_RELOAD:", app.config["TEMPLATES_AUTO_RELOAD"], "| cookie secure:", app.config["SESSION_COOKIE_SECURE"])
r = app.test_client().get("/api/health")
print("health:", r.status_code, r.get_json()["data"]["database"])

# la clé par défaut doit être refusée en production
os.environ["SECRET_KEY"] = "dev-secret-key-change-in-production-cosmitto-2024"
import importlib, config
importlib.reload(config)
import app as app_module
try:
    importlib.reload(app_module)
    app_module.create_app("production")
    print("default SECRET_KEY refused: NO (problem)")
except RuntimeError as e:
    print("default SECRET_KEY refused: YES ->", str(e)[:60])
