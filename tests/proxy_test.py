import os
import sys

os.environ["BEHIND_PROXY"] = "true"      # doit être défini avant l'import de la configuration
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from flask import request
from app import create_app

app = create_app("development")
app.add_url_rule("/__whoami", "whoami", lambda: f"{request.remote_addr}|{request.scheme}|{request.host}")
c = app.test_client()
r = c.get("/__whoami", headers={"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "support.example.com"})
print("with proxy headers  ->", r.get_data(as_text=True))
ok = r.get_data(as_text=True) == "203.0.113.9|https|support.example.com"
print("ProxyFix active and correct:", ok)

os.environ["BEHIND_PROXY"] = "false"
sys.exit(0 if ok else 1)
