from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import db, Post, Tag, Comment, UserPostInteraction, Like
from recommender import get_recommendations
import json

posts = Blueprint('posts', __name__)

@posts.route('/post/new', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash("Заголовок та зміст статті не можуть бути порожніми.", "danger")
            all_tags = Tag.query.all()
            existing_tags = [tag.name for tag in all_tags]
            return render_template('create_post.html', existing_tags=existing_tags, title=title, content=content) 
        
        new_post = Post(title=title, content=content, author=current_user)
        
        tags_json = request.form.get('tags', '[]')
        tag_names = []
        try:
            tags_list = json.loads(tags_json)
            tag_names = [tag['value'].strip().lower() for tag in tags_list if tag.get('value')]
        except json.JSONDecodeError:
            pass

        if tag_names:
            for name in tag_names:
                if not name: continue
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                new_post.tags.append(tag)
        
        db.session.add(new_post)
        db.session.commit()
        flash("Вашу статтю успішно опубліковано!", "success")
        return redirect(url_for('main.home'))
    
    all_tags = Tag.query.all()
    existing_tags = [tag.name for tag in all_tags]
    return render_template('create_post.html', existing_tags=existing_tags)

@posts.route('/post/<int:post_id>')
def post(post_id):
    post_to_show = Post.query.get_or_404(post_id)
    
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

    from recommender import get_recommendations
    all_posts = Post.query.all()
    recommendations = get_recommendations(post_to_show, all_posts)
    
    return render_template('post.html', post=post_to_show, recommendations=recommendations)

@posts.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post_to_edit = Post.query.get_or_404(post_id)
    if post_to_edit.author != current_user:
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash("Заголовок та зміст статті не можуть бути порожніми.", "danger")
            all_tags = Tag.query.all()
            existing_tags = [tag.name for tag in all_tags]
            return render_template('edit_post.html', post=post_to_edit, existing_tags=existing_tags)

        post_to_edit.title = title
        post_to_edit.content = content
        
        post_to_edit.tags.clear()
        tags_json = request.form.get('tags', '[]')
        tag_names = []
        try:
            tags_list = json.loads(tags_json)
            tag_names = [tag['value'].strip().lower() for tag in tags_list if tag.get('value')]
        except json.JSONDecodeError:
            pass

        if tag_names:
            for name in tag_names:
                if not name: continue
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                post_to_edit.tags.append(tag)
        
        db.session.commit()
        flash("Вашу статтю успішно оновлено!", "success")
        return redirect(url_for('posts.post', post_id=post_to_edit.id))
        
    all_tags = Tag.query.all()
    existing_tags = [tag.name for tag in all_tags]
    return render_template('edit_post.html', post=post_to_edit, existing_tags=existing_tags)

@posts.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post_to_delete = Post.query.get_or_404(post_id)
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
    post = Post.query.get_or_404(post_id)
    comment_body = request.form.get('comment_body')
    if comment_body:
        new_comment = Comment(body=comment_body, author=current_user, post=post)
        db.session.add(new_comment)
        db.session.commit()
        flash('Ваш коментар додано.', 'success')
    return redirect(url_for('posts.post', post_id=post_id))

@posts.route('/comment/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    
    new_body = request.form.get('comment_body')
    if new_body:
        comment.body = new_body
        db.session.commit()
        flash('Ваш коментар оновлено.', 'success')
    
    return redirect(url_for('posts.post', post_id=comment.post_id))


@posts.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
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
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        new_like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(new_like)
        db.session.commit()
        
        interaction_exists = UserPostInteraction.query.filter_by(
            user_id=current_user.id, 
            post_id=post.id,
            interaction_type='like'
        ).first()
        if not interaction_exists:
            new_interaction = UserPostInteraction(user_id=current_user.id, post_id=post.id, interaction_type='like')
            db.session.add(new_interaction)
            db.session.commit()

    return redirect(request.referrer or url_for('main.home'))