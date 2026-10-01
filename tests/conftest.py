import pytest

from blog import create_app, bcrypt
from blog.models import db, User, Post, Tag

TEST_PASSWORD = 'password123'

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'WTF_CSRF_ENABLED': False,
        'BCRYPT_LOG_ROUNDS': 4,
    })
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def make_user(app):
    def make_user(username='alice', email=None, password=TEST_PASSWORD):
        user = User(
            username=username,
            email=email or f'{username}@example.com',
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
        )
        db.session.add(user)
        db.session.commit()
        return user
    return make_user

@pytest.fixture
def make_post(app):
    def make_post(author, title='Title', content='Some content', tags=()):
        post = Post(title=title, content=content, author=author)
        db.session.add(post)
        for name in tags:
            tag = Tag.query.filter_by(name=name).first() or Tag(name=name)
            post.tags.append(tag)
        db.session.commit()
        return post
    return make_post

@pytest.fixture
def login(client):
    def login(username='alice', password=TEST_PASSWORD):
        return client.post('/login', data={'username': username, 'password': password})
    return login
