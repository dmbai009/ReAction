from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user
from .models import db, User
from . import bcrypt

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash(f"Акаунт для {username} успішно створено!", "success")
        return redirect(url_for('main.home'))
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Ви успішно увійшли на сайт.", "success")
            return redirect(url_for('main.home'))
        else:
            flash("Неправильне ім'я користувача або пароль.", "danger")
    return render_template('login.html')

@auth.route('/logout')
def logout():
    logout_user()
    flash("Ви вийшли зі свого акаунту.", "info")
    return redirect(url_for('main.home'))