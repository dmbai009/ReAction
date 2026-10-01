import re
import sqlite3

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from blog import create_app, render_markdown, markdown_excerpt
from blog.models import db, Like, UserPostInteraction

@pytest.mark.parametrize('payload', [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '[click](javascript:alert(1))',
    '<a href="javascript:alert(1)">x</a>',
    '<iframe src="https://evil.com"></iframe>',
    '<div style="background:url(x)" onclick="alert(1)">x</div>',
])
def test_markdown_is_sanitized(payload):
    html = str(render_markdown(payload)).lower()
    assert '<script' not in html
    assert 'onerror' not in html and 'onclick' not in html
    assert 'javascript:' not in html
    assert '<iframe' not in html

def test_markdown_formatting_is_kept():
    html = str(render_markdown('# Title\n\n**bold** [link](https://example.com)\n\n    code'))
    assert '<h1>Title</h1>' in html
    assert '<strong>bold</strong>' in html
    assert 'href="https://example.com"' in html
    assert '<pre><code>code' in html

def test_markdown_excerpt():
    assert markdown_excerpt('**short**') == 'short'
    assert markdown_excerpt('<script>alert(1)</script>text') == 'text'
    assert markdown_excerpt('one two three four', 9) == 'one two...'

def test_post_page_does_not_render_script(client, make_user, make_post):
    post = make_post(make_user('alice'), content='hello <script>alert("xss")</script>')
    html = client.get(f'/post/{post.id}').get_data(as_text=True)
    assert 'alert("xss")' not in html
    assert 'hello' in html

@pytest.fixture
def csrf_app():
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'BCRYPT_LOG_ROUNDS': 4,
    })
    with app.app_context():
        yield app
        db.drop_all()

def test_csrf_blocks_post_without_token(csrf_app):
    client = csrf_app.test_client()
    response = client.post('/register', data={'username': 'bob', 'email': 'bob@example.com', 'password': 'password123'})
    assert response.status_code == 400

def test_csrf_token_allows_post(csrf_app):
    client = csrf_app.test_client()
    html = client.get('/register').get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    response = client.post('/register', data={
        'csrf_token': token, 'username': 'bob', 'email': 'bob@example.com', 'password': 'password123',
    })
    assert response.status_code == 302

def test_every_post_form_has_csrf_token(client, make_user, make_post, login):
    alice = make_user('alice')
    post = make_post(alice)
    login()
    client.post(f'/post/{post.id}/comment', data={'comment_body': 'hi'})
    for url in ['/', f'/post/{post.id}', '/post/new', f'/post/{post.id}/edit']:
        html = client.get(url).get_data(as_text=True)
        forms = re.findall(r'<form[^>]*method="POST"[^>]*>(.*?)</form>', html, flags=re.S | re.I)
        assert forms, url
        for form in forms:
            assert 'name="csrf_token"' in form, url

def test_secret_key_from_environment(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'from-env')
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    app = create_app()
    assert app.config['SECRET_KEY'] == 'from-env'
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite://'

def test_missing_secret_key_is_random(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    first, second = create_app(), create_app()
    assert first.config['SECRET_KEY'] != second.config['SECRET_KEY']
    assert 'your_very_secret_key' not in first.config['SECRET_KEY']

def test_debug_is_off_by_default(monkeypatch):
    monkeypatch.delenv('FLASK_DEBUG', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    assert create_app().debug is False

def test_duplicate_like_is_rejected(app, make_user, make_post):
    alice = make_user('alice')
    post = make_post(alice)
    db.session.add_all([Like(user_id=alice.id, post_id=post.id), Like(user_id=alice.id, post_id=post.id)])
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

def test_duplicate_interaction_is_rejected(app, make_user, make_post):
    alice = make_user('alice')
    post = make_post(alice)
    db.session.add_all([
        UserPostInteraction(user_id=alice.id, post_id=post.id, interaction_type='view'),
        UserPostInteraction(user_id=alice.id, post_id=post.id, interaction_type='like'),
    ])
    db.session.commit()
    db.session.add(UserPostInteraction(user_id=alice.id, post_id=post.id, interaction_type='view'))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

def test_unique_indexes_added_to_existing_database(tmp_path):
    # a database created before the unique indexes existed
    path = tmp_path / 'old.db'
    connection = sqlite3.connect(path)
    connection.executescript('''
        CREATE TABLE "like" (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, post_id INTEGER NOT NULL);
        CREATE TABLE user_post_interaction (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL, interaction_type VARCHAR(20) NOT NULL, timestamp DATETIME NOT NULL);
    ''')
    connection.close()

    app = create_app({'SECRET_KEY': 'x', 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{path.as_posix()}'})
    with app.app_context():
        inspector = inspect(db.engine)
        assert {i['name'] for i in inspector.get_indexes('like')} == {'uq_like_user_post'}
        assert {i['name'] for i in inspector.get_indexes('user_post_interaction')} == {'uq_interaction_user_post_type'}
        db.engine.dispose()
