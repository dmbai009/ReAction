import re
from urllib.parse import urlsplit

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from .models import db, User
from . import bcrypt

auth = Blueprint('auth', __name__)

USERNAME_RE = re.compile(r'^[\w.-]{3,50}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD_LENGTH = 8

def is_safe_redirect(target):
    # only relative paths on this site; rejects absolute and scheme-relative ("//evil.com") URLs
    if not target:
        return False
    parts = urlsplit(target.replace('\\', '/'))
    return not parts.scheme and not parts.netloc and target.startswith('/')

def validate_registration(username, email, password):
    errors = []
    if not USERNAME_RE.match(username):
        errors.append("Ім'я користувача має містити 3–50 символів: літери, цифри, «_», «.» або «-».")
    elif User.query.filter(db.func.lower(User.username) == username.lower()).first():
        errors.append("Це ім'я користувача вже зайняте.")
    if len(email) > 255 or not EMAIL_RE.match(email):
        errors.append("Вкажіть коректну email-адресу.")
    elif User.query.filter(db.func.lower(User.email) == email.lower()).first():
        errors.append("Акаунт з цією email-адресою вже існує.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Пароль має містити щонайменше {MIN_PASSWORD_LENGTH} символів.")
    return errors

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        errors = validate_registration(username, email, password)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('register.html', username=username, email=email), 400
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Ви успішно увійшли на сайт.", "success")
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_redirect(next_page) else url_for('main.home'))
        else:
            flash("Неправильне ім'я користувача або пароль.", "danger")
    return render_template('login.html')

@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash("Ви вийшли зі свого акаунту.", "info")
    return redirect(url_for('main.home'))
