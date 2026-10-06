from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, CategorieConnaissance, ArticleConnaissance

base_connaissance_bp = Blueprint('base_connaissance', __name__)

@base_connaissance_bp.route('/')
@login_required
def index():
    if not current_user.has_permission('base_connaissance.voir'):
        flash("Vous n'avez pas la permission d'accéder à cette page.", "error")
        return redirect(url_for('tickets.mes_tickets'))
    categories = CategorieConnaissance.query.all()
    articles_recents = ArticleConnaissance.query.order_by(ArticleConnaissance.date_creation.desc()).limit(5).all()
    return render_template('base_connaissance/index.html', categories=categories, articles_recents=articles_recents)

@base_connaissance_bp.route('/categorie/<string:id>')
@login_required
def categorie(id):
    cat = CategorieConnaissance.query.get_or_404(id)
    return render_template('base_connaissance/categorie.html', categorie=cat)

@base_connaissance_bp.route('/article/<string:id>')
@login_required
def article(id):
    art = ArticleConnaissance.query.get_or_404(id)
    art.vues += 1
    db.session.commit()
    return render_template('base_connaissance/article.html', article=art)

@base_connaissance_bp.route('/categorie/nouvelle', methods=['POST'])
@login_required
def nouvelle_categorie():
    nom = request.form.get('nom')
    description = request.form.get('description', '')
    icone = request.form.get('icone', 'folder')
    if nom:
        cat = CategorieConnaissance(nom=nom, description=description, icone=icone)
        db.session.add(cat)
        db.session.commit()
        flash('Catégorie créée avec succès', 'success')
    return redirect(url_for('base_connaissance.index'))

@base_connaissance_bp.route('/article/nouveau', methods=['POST'])
@login_required
def nouvel_article():
    titre = request.form.get('titre')
    contenu = request.form.get('contenu')
    categorie_id = request.form.get('categorie_id')
    if titre and contenu and categorie_id:
        art = ArticleConnaissance(titre=titre, contenu=contenu, categorie_id=categorie_id, auteur_id=current_user.id)
        db.session.add(art)
        db.session.commit()
        flash('Article publié avec succès', 'success')
        return redirect(url_for('base_connaissance.article', id=art.id))
    flash('Erreur lors de la création de l\'article', 'error')
    return redirect(url_for('base_connaissance.categorie', id=categorie_id))
