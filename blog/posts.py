from urllib.parse import urlsplit

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import db, Post, Tag, Comment, UserPostInteraction, Like
from .recommender import get_recommendations
import json

posts = Blueprint('posts', __name__)

MAX_TITLE_LENGTH = 255
MAX_TAG_LENGTH = 50

def parse_tag_names(tags_json):
    """Tag names from Tagify's JSON ([{"value": "..."}]): trimmed, lowercased, deduplicated."""
    try:
        tags_list = json.loads(tags_json or '[]')
    except json.JSONDecodeError:
        return []
    if not isinstance(tags_list, list):
        return []

    tag_names = []
    for tag in tags_list:
        if not isinstance(tag, dict) or not isinstance(tag.get('value'), str):
            continue
        # "/" would break the /tag/<name> URL
        name = tag['value'].replace('/', ' ').strip().lower()[:MAX_TAG_LENGTH].strip()
        if name and name not in tag_names:
            tag_names.append(name)
    return tag_names

def set_post_tags(post, tags_json):
    post.tags.clear()
    for name in parse_tag_names(tags_json):
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
        post.tags.append(tag)

def validate_post(title, content):
    if not title or not content:
        return "Заголовок та зміст статті не можуть бути порожніми."
    if len(title) > MAX_TITLE_LENGTH:
        return f"Заголовок не може бути довшим за {MAX_TITLE_LENGTH} символів."
    return None

def existing_tag_names():
    return [tag.name for tag in Tag.query.order_by(Tag.name).all()]

def safe_referrer():
    # the Referer header is client-controlled: only follow it back to this site
    referrer = request.referrer
    if referrer and urlsplit(referrer).netloc == request.host:
        return referrer
    return None

@posts.route('/post/new', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        error = validate_post(title, content)
        if error:
            flash(error, "danger")
            return render_template('create_post.html', existing_tags=existing_tag_names(), title=title, content=content), 400

        new_post = Post(title=title, content=content, author=current_user)
        db.session.add(new_post)
        set_post_tags(new_post, request.form.get('tags'))
        db.session.commit()
        flash("Вашу статтю успішно опубліковано!", "success")
        return redirect(url_for('main.home'))

    return render_template('create_post.html', existing_tags=existing_tag_names())

@posts.route('/post/<int:post_id>')
def post(post_id):
    post_to_show = db.get_or_404(Post, post_id)

    if current_user.is_authenticated:
        interaction_exists = UserPostInteraction.query.filter_by(
            user_id=current_user.id,
            post_id=post_to_show.id,
            interaction_type='view'
        ).first()

        if not interaction_exists:
            new_view = UserPostInteraction(user_id=current_user.id, post_id=post_to_show.id, interaction_type='view')
            db.session.add(new_view)
            db.session.commit()

    all_posts = Post.query.all()
    recommendations = get_recommendations(post_to_show, all_posts)

    return render_template('post.html', post=post_to_show, recommendations=recommendations)

@posts.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post_to_edit = db.get_or_404(Post, post_id)
    if post_to_edit.author != current_user:
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        error = validate_post(title, content)
        if error:
            flash(error, "danger")
            return render_template('edit_post.html', post=post_to_edit, existing_tags=existing_tag_names()), 400

        post_to_edit.title = title
        post_to_edit.content = content
        set_post_tags(post_to_edit, request.form.get('tags'))

        db.session.commit()
        flash("Вашу статтю успішно оновлено!", "success")
        return redirect(url_for('posts.post', post_id=post_to_edit.id))

    return render_template('edit_post.html', post=post_to_edit, existing_tags=existing_tag_names())

@posts.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post_to_delete = db.get_or_404(Post, post_id)
    if post_to_delete.author != current_user:
        abort(403)
    db.session.delete(post_to_delete)
    db.session.commit()
    flash("Вашу статтю було видалено.", "success")
    return redirect(url_for('main.home'))

@posts.route('/tag/<string:tag_name>')
def posts_by_tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    posts_list = Post.query.filter(Post.tags.any(name=tag.name)).order_by(Post.published_at.desc()).all()
    return render_template('tag_posts.html', posts=posts_list, tag_name=tag.name)

@posts.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = db.get_or_404(Post, post_id)
    comment_body = request.form.get('comment_body', '').strip()
    if comment_body:
        new_comment = Comment(body=comment_body, author=current_user, post=post)
        db.session.add(new_comment)
        db.session.commit()
        flash('Ваш коментар додано.', 'success')
    return redirect(url_for('posts.post', post_id=post_id))

@posts.route('/comment/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    if comment.author != current_user:
        abort(403)

    new_body = request.form.get('comment_body', '').strip()
    if new_body:
        comment.body = new_body
        db.session.commit()
        flash('Ваш коментар оновлено.', 'success')

    return redirect(url_for('posts.post', post_id=comment.post_id))


@posts.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    if comment.author != current_user:
        abort(403)

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash('Ваш коментар видалено.', 'success')

    return redirect(url_for('posts.post', post_id=post_id))

@posts.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_action(post_id):
    post = db.get_or_404(Post, post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    like_interaction = UserPostInteraction.query.filter_by(
        user_id=current_user.id,
        post_id=post.id,
        interaction_type='like'
    ).first()

    if like:
        db.session.delete(like)
        # an unliked post should stop boosting the user's recommendations
        if like_interaction:
            db.session.delete(like_interaction)
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post.id))
        if not like_interaction:
            db.session.add(UserPostInteraction(user_id=current_user.id, post_id=post.id, interaction_type='like'))
    db.session.commit()

    return redirect(safe_referrer() or url_for('posts.post', post_id=post.id))
