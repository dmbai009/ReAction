import pytest

from blog.auth import is_safe_redirect
from blog.models import User

def register(client, username='bob', email='bob@example.com', password='password123'):
    return client.post('/register', data={'username': username, 'email': email, 'password': password})

def test_register_creates_user_and_logs_in(client):
    response = register(client)
    assert response.status_code == 302
    user = User.query.filter_by(username='bob').one()
    assert user.email == 'bob@example.com'
    assert user.password_hash != 'password123'
    assert 'Вийти' in client.get('/').get_data(as_text=True)

def test_register_normalizes_email(client):
    register(client, email='  Bob@Example.COM ')
    assert User.query.filter_by(username='bob').one().email == 'bob@example.com'

@pytest.mark.parametrize('username, email', [
    ('alice', 'other@example.com'),
    ('ALICE', 'other@example.com'),
    ('other', 'alice@example.com'),
    ('other', 'ALICE@example.com'),
])
def test_register_rejects_duplicate_username_or_email(client, make_user, username, email):
    make_user('alice')
    response = register(client, username=username, email=email)
    assert response.status_code == 400
    assert User.query.count() == 1

@pytest.mark.parametrize('username, email, password', [
    ('', 'bob@example.com', 'password123'),
    ('ab', 'bob@example.com', 'password123'),
    ('bad name', 'bob@example.com', 'password123'),
    ('x' * 51, 'bob@example.com', 'password123'),
    ('bob', '', 'password123'),
    ('bob', 'not-an-email', 'password123'),
    ('bob', 'bob@example.com', ''),
    ('bob', 'bob@example.com', 'short'),
])
def test_register_rejects_invalid_input(client, username, email, password):
    response = register(client, username=username, email=email, password=password)
    assert response.status_code == 400
    assert User.query.count() == 0

def test_register_keeps_entered_values_on_error(client):
    response = register(client, password='short')
    html = response.get_data(as_text=True)
    assert 'value="bob"' in html
    assert 'value="bob@example.com"' in html

def test_register_missing_fields_does_not_crash(client):
    assert client.post('/register', data={}).status_code == 400

def test_login_success_and_failure(client, make_user, login):
    make_user('alice')
    assert 'Неправильне' in client.post('/login', data={'username': 'alice', 'password': 'wrong'},
                                        follow_redirects=True).get_data(as_text=True)
    response = login()
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

def test_login_redirects_to_safe_next(client, make_user):
    make_user('alice')
    response = client.post('/login?next=/post/new', data={'username': 'alice', 'password': 'password123'})
    assert response.headers['Location'] == '/post/new'

@pytest.mark.parametrize('next_url', ['https://evil.com/', '//evil.com/', '/\\evil.com', 'javascript:alert(1)'])
def test_login_ignores_unsafe_next(client, make_user, next_url):
    make_user('alice')
    response = client.post('/login', query_string={'next': next_url},
                           data={'username': 'alice', 'password': 'password123'})
    assert response.headers['Location'] == '/'

def test_login_required_page_passes_next(client):
    response = client.get('/post/new')
    assert response.status_code == 302
    assert '/login?next=' in response.headers['Location']

@pytest.mark.parametrize('target, expected', [
    ('/post/1', True),
    ('/', True),
    ('', False),
    (None, False),
    ('post/1', False),
    ('http://evil.com', False),
    ('//evil.com', False),
    ('\\\\evil.com', False),
])
def test_is_safe_redirect(target, expected):
    assert is_safe_redirect(target) is expected

def test_logout_requires_post(client, make_user, login):
    make_user('alice')
    login()
    assert client.get('/logout').status_code == 405
    assert 'Вийти' in client.get('/').get_data(as_text=True)

    response = client.post('/logout')
    assert response.status_code == 302
    assert 'Увійти' in client.get('/').get_data(as_text=True)
