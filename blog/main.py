from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from .models import Post, User, Tag, UserPostInteraction
from .recommender import get_user_recommendations

main = Blueprint('main', __name__)

# how much each kind of interaction contributes to the user's recommendation profile
INTERACTION_WEIGHTS = {'view': 1, 'like': 2}

@main.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    feed_type = request.args.get('feed', 'latest')

    pagination = None

    if feed_type == 'recommended' and current_user.is_authenticated:
        interactions = UserPostInteraction.query.filter_by(user_id=current_user.id).all()

        if not interactions:
            posts = []
            flash("Ваша історія порожня. Почитайте або вподобайте кілька статей, щоб ми могли запропонувати вам рекомендації!", "info")
        else:
            post_weights = defaultdict(int)
            for interaction in interactions:
                post_weights[interaction.post_id] += INTERACTION_WEIGHTS.get(interaction.interaction_type, 0)

            all_posts = Post.query.all()
            posts = get_user_recommendations(post_weights, all_posts)

    else:
        feed_type = 'latest'
        pagination = Post.query.order_by(Post.published_at.desc()).paginate(page=page, per_page=5, error_out=False)
        posts = pagination.items

    return render_template('home.html', posts=posts, feed_type=feed_type, pagination=pagination)

@main.route('/search')
def search():
    query = request.args.get('q', '').strip()

    if not query:
        return redirect(url_for('main.home'))

    # outer join: posts without tags must still be found by title, content or author
    results = Post.query.join(User).outerjoin(Post.tags).filter(
        or_(
            Post.title.contains(query, autoescape=True),
            Post.content.contains(query, autoescape=True),
            User.username.contains(query, autoescape=True),
            Tag.name.contains(query, autoescape=True)
        )
    ).distinct().order_by(Post.published_at.desc()).all()

    return render_template('search_results.html', posts=results, query=query)
