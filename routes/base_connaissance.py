from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db

base_connaissance_bp = Blueprint('base_connaissance', __name__)

@base_connaissance_bp.route('/')
@login_required
def index():
    if not current_user.has_permission('base_connaissance.voir'):
        flash("Vous n'avez pas la permission d'accéder à cette page.", "error")
        return redirect(url_for('tickets.mes_tickets'))
        
    """Page d'accueil de la base de connaissance"""
    return render_template('base_connaissance/index.html')
