from types import SimpleNamespace

import pytest

from blog.recommender import build_tfidf_matrix, get_recommendations, get_user_recommendations

def post(id, title, content=''):
    return SimpleNamespace(id=id, title=title, content=content)

@pytest.fixture
def corpus():
    return [
        post(1, 'Python Flask', 'python flask web development'),
        post(2, 'Flask tutorial', 'flask web python routes'),
        post(3, 'Gardening', 'tomatoes soil water garden'),
        post(4, 'Garden tips', 'garden soil tomatoes'),
        post(5, 'Cooking', 'pasta sauce recipe'),
    ]

def ids(posts):
    return [p.id for p in posts]

def test_similar_posts_ranked_by_content(corpus):
    assert ids(get_recommendations(corpus[0], corpus, 1)) == [2]
    assert ids(get_recommendations(corpus[2], corpus, 1)) == [4]

def test_similar_posts_exclude_current_and_unrelated(corpus):
    result = ids(get_recommendations(corpus[0], corpus, 10))
    assert 1 not in result
    assert result == [2]  # posts with zero similarity are not "similar"

def test_similar_posts_edge_cases(corpus):
    assert get_recommendations(corpus[0], [], 3) == []
    assert get_recommendations(corpus[0], [corpus[0]], 3) == []
    assert get_recommendations(post(99, 'missing'), corpus, 3) == []
    assert get_recommendations(corpus[0], corpus, 0) == []

@pytest.mark.parametrize('texts', [
    [('!!!', '???'), ('...', '---')],
    [('', ''), ('', '')],
    [('a', 'b'), ('🙂', '🙂')],
])
def test_texts_without_words_do_not_crash(texts):
    posts = [post(i, title, content) for i, (title, content) in enumerate(texts)]
    assert build_tfidf_matrix(posts) is None
    assert get_recommendations(posts[0], posts) == []
    assert get_user_recommendations({posts[0].id: 1}, posts) == []

def test_none_fields_do_not_crash():
    posts = [post(1, None, None), post(2, 'flask web', None), post(3, 'flask python', 'web')]
    assert ids(get_recommendations(posts[1], posts)) == [3]

def test_cyrillic_text_is_tokenized():
    posts = [
        post(1, 'Машинне навчання', 'нейронні мережі навчання моделі'),
        post(2, 'Нейронні мережі', 'навчання нейронні мережі'),
        post(3, 'Борщ', 'буряк капуста рецепт'),
    ]
    assert ids(get_recommendations(posts[0], posts, 1)) == [2]

def test_user_recommendations_exclude_history(corpus):
    result = ids(get_user_recommendations({1: 1}, corpus))
    assert result == [2]

def test_user_recommendations_respect_weights(corpus):
    # mostly gardening with a little python: gardening posts should come first
    result = ids(get_user_recommendations({3: 3, 1: 1}, corpus))
    assert result[0] == 4
    assert 2 in result
    # the like weight flips the order
    result = ids(get_user_recommendations({3: 1, 1: 3}, corpus))
    assert result[0] == 2

def test_user_recommendations_edge_cases(corpus):
    assert get_user_recommendations({}, corpus) == []
    assert get_user_recommendations({1: 1}, []) == []
    assert get_user_recommendations({99: 1}, corpus) == []
    assert get_user_recommendations({1: 0}, corpus) == []
    assert get_user_recommendations({1: 1}, corpus, 0) == []

def test_user_recommendations_limit(corpus):
    many = corpus + [post(10 + i, f'flask {i}', 'python web') for i in range(20)]
    assert len(get_user_recommendations({1: 1}, many, 5)) == 5
