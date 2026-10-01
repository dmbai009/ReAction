import os
import secrets

import markdown
import nh3
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from .models import db, User

bcrypt = Bcrypt()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Будь ласка, увійдіть, щоб отримати доступ до цієї сторінки."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def render_markdown(text):
    # Python-Markdown passes raw HTML through, so the output must be sanitized before it reaches the page
    return Markup(nh3.clean(markdown.markdown(text or '')))

def markdown_excerpt(text, length=300):
    plain = render_markdown(text).striptags()
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(' ', 1)[0] + '...'

def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///blog.db'),
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if test_config:
        app.config.update(test_config)

    if not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = secrets.token_hex(32)
        app.logger.warning("SECRET_KEY не задано: згенеровано тимчасовий ключ, сесії скинуться після перезапуску.")

    app.add_template_filter(render_markdown, 'markdown')
    app.add_template_filter(markdown_excerpt, 'excerpt')

    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .posts import posts as posts_blueprint
    app.register_blueprint(posts_blueprint)

    from .users import users as users_blueprint
    app.register_blueprint(users_blueprint)

    with app.app_context():
        db.create_all()
        # create_all() skips tables that already exist, so indexes added to the models later
        # (e.g. the unique ones on likes and interactions) have to be created separately
        for table in db.metadata.sorted_tables:
            for index in table.indexes:
                index.create(db.engine, checkfirst=True)

    return app
