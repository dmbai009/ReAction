import pytest

@pytest.fixture
def posts(make_user, make_post):
    alice = make_user('alice')
    bob = make_user('bob')
    make_post(alice, title='Untagged title', content='plain body')
    make_post(alice, title='Tagged', content='other body', tags=['machinelearning', 'python'])
    make_post(bob, title='By bob', content='something')
    make_post(bob, title='Percent', content='100% done')

def titles(client, query):
    html = client.get('/search', query_string={'q': query}).get_data(as_text=True)
    return {title for title in ['Untagged title', 'Tagged', 'By bob', 'Percent'] if title in html}

def test_search_finds_post_without_tags(client, posts):
    assert titles(client, 'Untagged') == {'Untagged title'}
    assert titles(client, 'plain body') == {'Untagged title'}

def test_search_by_tag_author_and_content(client, posts):
    assert titles(client, 'machinelearning') == {'Tagged'}
    assert titles(client, 'bob') == {'By bob', 'Percent'}
    assert titles(client, 'other body') == {'Tagged'}

def test_search_returns_each_post_once(client, posts):
    html = client.get('/search', query_string={'q': 'Tagged'}).get_data(as_text=True)
    assert html.count('<h5 class="card-title">Tagged</h5>') == 1

def test_search_treats_wildcards_literally(client, posts):
    assert titles(client, '%') == {'Percent'}
    assert titles(client, '_') == set()

def test_empty_search_redirects_home(client):
    assert client.get('/search?q=%20').status_code == 302

def test_search_query_is_escaped(client, posts):
    html = client.get('/search', query_string={'q': '<script>x</script>'}).get_data(as_text=True)
    assert '<script>x</script>' not in html
