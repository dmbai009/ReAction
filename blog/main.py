from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from .models import Post
from recommender import get_user_recommendations
from .models import Post, User, Tag, UserPostInteraction
from sqlalchemy import or_ # Імпортуй or_ для складних запитів


main = Blueprint('main', __name__)

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
            weighted_history_ids = []
            for interaction in interactions:
                weighted_history_ids.append(interaction.post_id)
                if interaction.interaction_type == 'like':
                    weighted_history_ids.extend([interaction.post_id] * 2)

            user_history = Post.query.filter(Post.id.in_(weighted_history_ids)).all()
            all_posts = Post.query.all()
            
            posts = get_user_recommendations(user_history, all_posts)
            
    else:
        feed_type = 'latest'
        pagination = Post.query.order_by(Post.published_at.desc()).paginate(page=page, per_page=5, error_out=False)
        posts = pagination.items
        
    return render_template('home.html', posts=posts, feed_type=feed_type, pagination=pagination)

@main.route('/search')
def search():
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('main.home'))

    results = Post.query.join(User).join(Post.tags).filter(
        or_(
            Post.title.contains(query),
            Post.content.contains(query),
            User.username.contains(query),
            Tag.name.contains(query)
        )
    ).distinct().all()

    return render_template('search_results.html', posts=results, query=query)