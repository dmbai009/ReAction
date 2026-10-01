from flask import Flask
import markdown
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from .models import db, User

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Будь ласка, увійдіть, щоб отримати доступ до цієї сторінки."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    @app.template_filter('markdown')
    def markdown_filter(s):
        return markdown.markdown(s)
    
    app.config['SECRET_KEY'] = 'your_very_secret_key_123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .posts import posts as posts_blueprint
    app.register_blueprint(posts_blueprint)

    from .users import users as users_blueprint
    app.register_blueprint(users_blueprint)

    return app