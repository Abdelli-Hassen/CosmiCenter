from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, ArticleConnaissance, CategorieConnaissance

base_connaissance_bp = Blueprint('base_connaissance', __name__)

@base_connaissance_bp.route('/')
@login_required
def index():
    if not current_user.has_permission('base_connaissance.voir'):
        flash("Vous n'avez pas la permission d'accéder à cette page.", "danger")
        return redirect(url_for('tickets.mes_tickets'))
    categories = CategorieConnaissance.query.all()
    articles_recents = ArticleConnaissance.query.order_by(ArticleConnaissance.date_creation.desc()).limit(5).all()
    return render_template('base_connaissance/index.html', categories=categories, articles_recents=articles_recents)

@base_connaissance_bp.route('/categorie/<string:id>')
@login_required
def categorie(id):
    if not current_user.has_permission('base_connaissance.voir'):
        flash("Vous n'avez pas la permission d'accéder à cette page.", "danger")
        return redirect(url_for('tickets.mes_tickets'))

    cat = CategorieConnaissance.query.get_or_404(id)
    return render_template('base_connaissance/categorie.html', categorie=cat)

@base_connaissance_bp.route('/article/<string:id>')
@login_required
def article(id):
    if not current_user.has_permission('base_connaissance.voir'):
        flash("Vous n'avez pas la permission d'accéder à cette page.", "danger")
        return redirect(url_for('tickets.mes_tickets'))

    art = ArticleConnaissance.query.get_or_404(id)
    art.vues += 1
    db.session.commit()
    return render_template('base_connaissance/article.html', article=art)

@base_connaissance_bp.route('/article/nouveau', methods=['GET', 'POST'])
@login_required
def nouvel_article():
    if not current_user.has_permission('base_connaissance.creer'):
        flash("Vous n'avez pas la permission de créer des articles.", "danger")
        return redirect(url_for('base_connaissance.index'))

    categories = CategorieConnaissance.query.all()

    if request.method == 'POST':
        titre = request.form.get('titre')
        contenu = request.form.get('contenu')
        categorie_id = request.form.get('categorie_id')

        if not titre or not contenu or not categorie_id:
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template('base_connaissance/nouveau.html', categories=categories)

        nouvel_art = ArticleConnaissance(
            titre=titre,
            contenu=contenu,
            categorie_id=categorie_id,
            auteur_id=current_user.id
        )
        db.session.add(nouvel_art)
        db.session.commit()
        flash("Article créé avec succès.", "success")
        return redirect(url_for('base_connaissance.article', id=nouvel_art.id))

    return render_template('base_connaissance/nouveau.html', categories=categories)

@base_connaissance_bp.route('/article/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_article(id):
    if not current_user.has_permission('base_connaissance.modifier'):
        flash("Vous n'avez pas la permission de modifier des articles.", "danger")
        return redirect(url_for('base_connaissance.index'))

    art = ArticleConnaissance.query.get_or_404(id)
    categories = CategorieConnaissance.query.all()

    if request.method == 'POST':
        art.titre = request.form.get('titre', art.titre)
        art.contenu = request.form.get('contenu', art.contenu)
        art.categorie_id = request.form.get('categorie_id', art.categorie_id)

        db.session.commit()
        flash("Article mis à jour avec succès.", "success")
        return redirect(url_for('base_connaissance.article', id=art.id))

    return render_template('base_connaissance/modifier.html', article=art, categories=categories)

@base_connaissance_bp.route('/article/<string:id>/supprimer', methods=['POST'])
@login_required
def supprimer_article(id):
    if not current_user.has_permission('base_connaissance.supprimer'):
        flash("Vous n'avez pas la permission de supprimer des articles.", "danger")
        return redirect(url_for('base_connaissance.index'))

    art = ArticleConnaissance.query.get_or_404(id)
    db.session.delete(art)
    db.session.commit()
    flash("Article supprimé.", "success")
    return redirect(url_for('base_connaissance.index'))

@base_connaissance_bp.route('/categorie/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_categorie():
    if not current_user.has_permission('base_connaissance.creer'):
        flash("Vous n'avez pas la permission de créer des catégories.", "danger")
        return redirect(url_for('base_connaissance.index'))

    if request.method == 'POST':
        nom = request.form.get('nom')
        description = request.form.get('description', '')
        icone = request.form.get('icone', 'folder')

        if not nom:
            flash("Le nom de la catégorie est obligatoire.", "danger")
            return render_template('base_connaissance/nouvelle_categorie.html')

        nouvelle_cat = CategorieConnaissance(
            nom=nom,
            description=description,
            icone=icone
        )
        db.session.add(nouvelle_cat)
        db.session.commit()
        flash("Catégorie créée avec succès.", "success")
        return redirect(url_for('base_connaissance.index'))

    return render_template('base_connaissance/nouvelle_categorie.html')
