"""Raccourci clavier dans la console du serveur : touche R = redémarrage complet.

Le processus se termine avec le code RESTART_EXIT_CODE :
- production (run_prod.bat) : la boucle du .bat relance serve.py ;
- développement (run_dev.bat) : le rechargeur de Werkzeug relance le serveur.
Windows uniquement (msvcrt) ; ailleurs (Ubuntu / systemd), systemctl restart suffit.
"""
import os
import sys
import threading
import time

RESTART_EXIT_CODE = 3


def start_restart_listener():
    """Lance l'écoute de la touche R si la console est interactive. Sans effet sinon."""
    try:
        import msvcrt
    except ImportError:
        return False
    if not (sys.stdin and sys.stdin.isatty()):
        return False

    def _listen():
        while True:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getwch()
                    if key.lower() == 'r':
                        print("\n [R] Redemarrage du serveur...", flush=True)
                        os._exit(RESTART_EXIT_CODE)
                else:
                    time.sleep(0.2)
            except Exception:
                return

    threading.Thread(target=_listen, name='restart-key', daemon=True).start()
    return True
