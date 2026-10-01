import json

import pytest

from blog.models import db, Post, Tag, Comment, Like, UserPostInteraction
from blog.posts import parse_tag_names

def tags_json(*names):
    return json.dumps([{'value': name} for name in names])

def test_create_post_with_tags(client, make_user, login):
    make_user('alice')
    login()
    response = client.post('/post/new', data={
        'title': '  First post ', 'content': 'Hello', 'tags': tags_json('Python', ' python ', 'Flask'),
    })
    assert response.status_code == 302
    post = Post.query.one()
    assert post.title == 'First post'
    assert sorted(tag.name for tag in post.tags) == ['flask', 'python']

def test_create_post_reuses_existing_tags(client, make_user, make_post, login):
    alice = make_user('alice')
    make_post(alice, tags=['python'])
    login()
    client.post('/post/new', data={'title': 'Second', 'content': 'x', 'tags': tags_json('python')})
    assert Tag.query.count() == 1

@pytest.mark.parametrize('title, content', [('', 'text'), ('Title', ''), ('   ', '   '), ('x' * 256, 'text')])
def test_create_post_validation(client, make_user, login, title, content):
    make_user('alice')
    login()
    response = client.post('/post/new', data={'title': title, 'content': content})
    assert response.status_code == 400
    assert Post.query.count() == 0

def test_create_post_requires_login(client):
    assert client.post('/post/new', data={'title': 't', 'content': 'c'}).status_code == 302
    assert Post.query.count() == 0

@pytest.mark.parametrize('raw, expected', [
    (tags_json('A', 'a', ' b '), ['a', 'b']),
    (tags_json('c/d'), ['c d']),
    (tags_json('x' * 80), ['x' * 50]),
    (tags_json('', '   '), []),
    ('not json', []),
    ('{"value": "a"}', []),
    ('[1, {"value": 5}, {"other": "a"}]', []),
    (None, []),
])
def test_parse_tag_names(raw, expected):
    assert parse_tag_names(raw) == expected

def test_edit_post_by_author(client, make_user, make_post, login):
    alice = make_user('alice')
    post = make_post(alice, tags=['old'])
    login()
    response = client.post(f'/post/{post.id}/edit', data={'title': 'New', 'content': 'Body', 'tags': tags_json('new')})
    assert response.status_code == 302
    db.session.refresh(post)
    assert post.title == 'New'
    assert [tag.name for tag in post.tags] == ['new']

def test_edit_and_delete_post_forbidden_for_others(client, make_user, make_post, login):
    alice = make_user('alice')
    make_user('mallory')
    post = make_post(alice)
    login('mallory')
    assert client.get(f'/post/{post.id}/edit').status_code == 403
    assert client.post(f'/post/{post.id}/edit', data={'title': 'x', 'content': 'y'}).status_code == 403
    assert client.post(f'/post/{post.id}/delete').status_code == 403
    assert db.session.get(Post, post.id).title == 'Title'

def test_delete_post_cascades(client, make_user, make_post, login):
    alice = make_user('alice')
    post = make_post(alice)
    login()
    client.get(f'/post/{post.id}')
    client.post(f'/like/{post.id}')
    client.post(f'/post/{post.id}/comment', data={'comment_body': 'hi'})
    assert client.post(f'/post/{post.id}/delete').status_code == 302
    assert Post.query.count() == Comment.query.count() == Like.query.count() == UserPostInteraction.query.count() == 0

def test_missing_post_returns_404(client):
    assert client.get('/post/999').status_code == 404

def test_view_is_recorded_once(client, make_user, make_post, login):
    alice = make_user('alice')
    post = make_post(alice)
    login()
    client.get(f'/post/{post.id}')
    client.get(f'/post/{post.id}')
    assert UserPostInteraction.query.filter_by(interaction_type='view').count() == 1

def test_like_toggle_updates_like_and_interaction(client, make_user, make_post, login):
    alice = make_user('alice')
    make_user('bob')
    post = make_post(alice)
    login('bob')

    client.post(f'/like/{post.id}')
    assert Like.query.count() == 1
    assert UserPostInteraction.query.filter_by(interaction_type='like').count() == 1

    client.post(f'/like/{post.id}')
    assert Like.query.count() == 0
    assert UserPostInteraction.query.filter_by(interaction_type='like').count() == 0

def test_like_redirects_only_to_own_site(client, make_user, make_post, login):
    alice = make_user('alice')
    post = make_post(alice)
    login()
    response = client.post(f'/like/{post.id}', headers={'Referer': 'https://evil.com/'})
    assert response.headers['Location'] == f'/post/{post.id}'
    response = client.post(f'/like/{post.id}', headers={'Referer': 'http://localhost/?page=2'})
    assert response.headers['Location'] == 'http://localhost/?page=2'

def test_like_button_visible_to_non_author(client, make_user, make_post, login):
    alice = make_user('alice')
    make_user('bob')
    post = make_post(alice)
    login('bob')
    html = client.get(f'/post/{post.id}').get_data(as_text=True)
    assert f'/like/{post.id}' in html
    assert f'/post/{post.id}/edit' not in html

def test_like_button_hidden_for_anonymous(client, make_user, make_post):
    post = make_post(make_user('alice'))
    html = client.get(f'/post/{post.id}').get_data(as_text=True)
    assert f'/like/{post.id}' not in html
    assert '0 вподобань' in html

def test_comment_add_edit_delete(client, make_user, make_post, login):
    alice = make_user('alice')
    post = make_post(alice)
    login()
    client.post(f'/post/{post.id}/comment', data={'comment_body': '  first  '})
    comment = Comment.query.one()
    assert comment.body == 'first'

    client.post(f'/comment/{comment.id}/edit', data={'comment_body': 'edited'})
    assert db.session.get(Comment, comment.id).body == 'edited'

    client.post(f'/comment/{comment.id}/delete')
    assert Comment.query.count() == 0

def test_empty_comment_is_ignored(client, make_user, make_post, login):
    post = make_post(make_user('alice'))
    login()
    client.post(f'/post/{post.id}/comment', data={'comment_body': '   '})
    assert Comment.query.count() == 0

def test_comment_edit_and_delete_forbidden_for_others(client, make_user, make_post, login):
    alice = make_user('alice')
    make_user('mallory')
    post = make_post(alice)
    db.session.add(Comment(body='mine', author=alice, post=post))
    db.session.commit()
    comment = Comment.query.one()

    login('mallory')
    assert client.post(f'/comment/{comment.id}/edit', data={'comment_body': 'hacked'}).status_code == 403
    assert client.post(f'/comment/{comment.id}/delete').status_code == 403
    assert db.session.get(Comment, comment.id).body == 'mine'

def test_posts_by_tag(client, make_user, make_post):
    alice = make_user('alice')
    make_post(alice, title='Tagged', tags=['python'])
    make_post(alice, title='Other')
    html = client.get('/tag/python').get_data(as_text=True)
    assert 'Tagged' in html and 'Other' not in html
    assert client.get('/tag/missing').status_code == 404

def test_profile_page(client, make_user, make_post):
    make_post(make_user('alice'), title='Alice post')
    html = client.get('/user/alice').get_data(as_text=True)
    assert 'Alice post' in html
    assert 'Статей: 1' in html
    assert client.get('/user/nobody').status_code == 404

def test_home_feeds(client, make_user, make_post, login):
    alice = make_user('alice')
    for i in range(7):
        make_post(alice, title=f'Post {i}')
    html = client.get('/').get_data(as_text=True)
    assert 'Post 6' in html and 'Post 1' not in html
    assert 'Post 1' in client.get('/?page=2').get_data(as_text=True)

    login()
    html = client.get('/?feed=recommended', follow_redirects=True).get_data(as_text=True)
    assert 'Ваша історія порожня' in html

def test_recommended_feed_for_anonymous_falls_back_to_latest(client, make_user, make_post):
    make_post(make_user('alice'), title='Visible')
    assert 'Visible' in client.get('/?feed=recommended').get_data(as_text=True)

def test_recommended_feed_shows_similar_unseen_posts(client, make_user, make_post, login):
    alice = make_user('alice')
    seen = make_post(alice, title='Python flask', content='python flask web framework')
    make_post(alice, title='Flask tips', content='flask web python tricks')
    make_post(alice, title='Gardening', content='tomatoes soil water')
    login()
    client.get(f'/post/{seen.id}')
    html = client.get('/?feed=recommended').get_data(as_text=True)
    assert 'Flask tips' in html
    assert 'Gardening' not in html

def test_home_excerpt_is_plain_text(client, make_user, make_post):
    make_post(make_user('alice'), content='**bold** ' + 'word ' * 100)
    html = client.get('/').get_data(as_text=True)
    assert '<strong>bold</strong>' not in html
    assert 'bold word' in html
    assert '...' in html
