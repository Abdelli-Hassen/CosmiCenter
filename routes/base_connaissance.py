from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import db, ArticleConnaissance, CategorieConnaissance, ArticleVue

# Note : l'URL /article/nouveau est déclarée après /article/<id> ; Flask privilégie les routes statiques,
# « nouveau » n'est donc jamais interprété comme un identifiant d'article.

base_connaissance_bp = Blueprint('base_connaissance', __name__)


def peut_voir_lecteurs():
    """Seuls les gestionnaires de la base (création d'articles) voient qui a lu quoi."""
    return current_user.has_permission('base_connaissance.creer')


def enregistrer_lecture(article_id):
    """Compte la lecture : « vues » = nombre de personnes distinctes ; chaque personne a son propre compteur."""
    now = datetime.utcnow()
    updated = ArticleVue.query.filter_by(article_id=article_id, utilisateur_id=current_user.id).update(
        {'nb_vues': ArticleVue.nb_vues + 1, 'derniere_vue': now})
    if not updated:
        try:
            db.session.add(ArticleVue(article_id=article_id, utilisateur_id=current_user.id, nb_vues=1,
                                      premiere_vue=now, derniere_vue=now))
            ArticleConnaissance.query.filter_by(id=article_id).update({'vues': ArticleConnaissance.vues + 1})
            db.session.flush()
        except IntegrityError:  # deux onglets simultanés : l'autre a créé la ligne entre-temps
            db.session.rollback()
            ArticleVue.query.filter_by(article_id=article_id, utilisateur_id=current_user.id).update(
                {'nb_vues': ArticleVue.nb_vues + 1, 'derniere_vue': now})
    db.session.commit()


def lecteurs_par_article(article_ids):
    """{article_id: [{'nom', 'nb', 'derniere'}, …]} trié par nombre de lectures décroissant."""
    if not article_ids:
        return {}
    rows = (ArticleVue.query.filter(ArticleVue.article_id.in_(list(article_ids)))
            .order_by(ArticleVue.nb_vues.desc(), ArticleVue.derniere_vue.desc()).all())
    out = {}
    for r in rows:
        u = r.utilisateur
        out.setdefault(r.article_id, []).append({
            'nom': u.nom_complet if u else 'Utilisateur supprimé',
            'nb': r.nb_vues,
            'derniere': r.derniere_vue,
        })
    return out

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
    lecteurs = lecteurs_par_article([a.id for a in cat.articles]) if peut_voir_lecteurs() else {}
    return render_template('base_connaissance/categorie.html', categorie=cat, lecteurs=lecteurs,
                           can_see_viewers=peut_voir_lecteurs())

@base_connaissance_bp.route('/article/<string:id>')
@login_required
def article(id):
    if not current_user.has_permission('base_connaissance.voir'):
        flash("Vous n'avez pas la permission d'accéder à cette page.", "danger")
        return redirect(url_for('tickets.mes_tickets'))

    art = ArticleConnaissance.query.get_or_404(id)
    enregistrer_lecture(id)
    db.session.refresh(art)
    lecteurs = lecteurs_par_article([id]).get(id, []) if peut_voir_lecteurs() else []
    return render_template('base_connaissance/article.html', article=art, lecteurs=lecteurs,
                           can_see_viewers=peut_voir_lecteurs())

@base_connaissance_bp.route('/article/nouveau', methods=['GET', 'POST'])
@login_required
def nouvel_article():
    if not current_user.has_permission('base_connaissance.creer'):
        flash("Vous n'avez pas la permission de créer des articles.", "danger")
        return redirect(url_for('base_connaissance.index'))

    categories = CategorieConnaissance.query.all()

    if request.method == 'POST':
        titre = (request.form.get('titre') or '').strip()
        contenu = (request.form.get('contenu') or '').strip()
        categorie_id = request.form.get('categorie_id')

        if not titre or not contenu or not categorie_id:
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template('base_connaissance/nouveau.html', categories=categories)
        if len(titre) > 255:
            flash("Le titre est trop long (255 caractères maximum).", "danger")
            return render_template('base_connaissance/nouveau.html', categories=categories)
        if not db.session.get(CategorieConnaissance, categorie_id):
            flash("Catégorie introuvable.", "danger")
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
        titre = (request.form.get('titre', art.titre) or '').strip()
        contenu = (request.form.get('contenu', art.contenu) or '').strip()
        categorie_id = request.form.get('categorie_id', art.categorie_id)
        if not titre or not contenu or len(titre) > 255 or not db.session.get(CategorieConnaissance, categorie_id):
            flash("Titre, contenu et catégorie valides sont obligatoires.", "danger")
            return render_template('base_connaissance/modifier.html', article=art, categories=categories)
        art.titre = titre
        art.contenu = contenu
        art.categorie_id = categorie_id

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
        nom = (request.form.get('nom') or '').strip()
        description = request.form.get('description', '')
        icone = (request.form.get('icone', 'folder') or 'folder')[:50]

        if not nom:
            flash("Le nom de la catégorie est obligatoire.", "danger")
            return render_template('base_connaissance/nouvelle_categorie.html')
        if len(nom) > 100:
            flash("Le nom de la catégorie est trop long (100 caractères maximum).", "danger")
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
