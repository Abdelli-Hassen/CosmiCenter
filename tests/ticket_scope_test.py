"""Portée des actions sur les tickets : `tickets.<action>` (tous) et `tickets.<action>_mes` (mes tickets). Sans base."""
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.permissions import can_ticket  # noqa: E402

ok = 0
total = 0


def check(label, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(('PASS ' if cond else 'FAIL ') + label)


def user(*codes):
    return NS(id='u1', departement_id='d1', has_permission=lambda c: c in codes)


mine = NS(createur_id='u1', assigne_a_id=None, departement_id='d9', departements_collab=[], collaborateurs=[])
other = NS(createur_id='u2', assigne_a_id='u3', departement_id='d9', departements_collab=[], collaborateurs=[])
dept = NS(createur_id='u2', assigne_a_id=None, departement_id='d1', departements_collab=[], collaborateurs=[])

u_mes = user('tickets.assigner_mes')
check('_mes : mon ticket autorisé', can_ticket(u_mes, 'assigner', mine))
check('_mes : ticket de mon département autorisé', can_ticket(u_mes, 'assigner', dept))
check('_mes : ticket des autres refusé', not can_ticket(u_mes, 'assigner', other))
check('_mes : bouton visible (sans ticket)', can_ticket(u_mes, 'assigner'))
check('_mes : autre action refusée', not can_ticket(u_mes, 'cloturer', mine))
u_all = user('tickets.assigner')
check('tous : ticket des autres autorisé', can_ticket(u_all, 'assigner', other))
check('tous : n\'ouvre pas les autres actions', not can_ticket(u_all, 'modifier', other))
check('aucun droit : refusé', not can_ticket(user(), 'assigner', mine))
print(f'{ok}/{total} checks passed')
sys.exit(0 if ok == total else 1)
