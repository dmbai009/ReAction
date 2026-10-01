from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def build_tfidf_matrix(all_posts):
    """TF-IDF matrix with one row per post, or None if the posts contain no recognizable words."""
    post_texts = [f"{post.title or ''} {post.content or ''}" for post in all_posts]
    if not post_texts:
        return None
    try:
        return TfidfVectorizer().fit_transform(post_texts)
    except ValueError:
        # raised when the vocabulary is empty: only punctuation, emoji, one-letter words, etc.
        return None

def get_recommendations(current_post, all_posts, num_recommendations=3):
    post_index = {post.id: i for i, post in enumerate(all_posts)}
    current_post_index = post_index.get(current_post.id)
    if current_post_index is None or num_recommendations <= 0:
        return []

    tfidf_matrix = build_tfidf_matrix(all_posts)
    if tfidf_matrix is None:
        return []

    # only the current post's row is needed, not the full N x N similarity matrix
    scores = cosine_similarity(tfidf_matrix[current_post_index], tfidf_matrix)[0]

    recommended_posts = []
    for index in np.argsort(-scores, kind='stable'):
        if index == current_post_index:
            continue
        if scores[index] <= 0:
            break
        recommended_posts.append(all_posts[index])
        if len(recommended_posts) == num_recommendations:
            break
    return recommended_posts

def get_user_recommendations(post_weights, all_posts, num_recommendations=10):
    """Recommend posts close to the user's profile.

    post_weights maps post id -> weight of the user's interactions with it (e.g. view = 1, like = 3);
    the profile is the weighted mean of those posts' TF-IDF vectors.
    """
    post_index = {post.id: i for i, post in enumerate(all_posts)}
    history = {post_id: weight for post_id, weight in post_weights.items()
               if post_id in post_index and weight > 0}
    if not history or num_recommendations <= 0:
        return []

    tfidf_matrix = build_tfidf_matrix(all_posts)
    if tfidf_matrix is None:
        return []

    history_indices = [post_index[post_id] for post_id in history]
    weights = np.array(list(history.values()), dtype=float)
    user_profile_vector = np.asarray(
        tfidf_matrix[history_indices].multiply(weights[:, None]).sum(axis=0) / weights.sum()
    )
    if not user_profile_vector.any():
        return []

    scores = cosine_similarity(user_profile_vector, tfidf_matrix)[0]

    recommended_posts = []
    for index in np.argsort(-scores, kind='stable'):
        if scores[index] <= 0:
            break
        if all_posts[index].id in history:
            continue
        recommended_posts.append(all_posts[index])
        if len(recommended_posts) >= num_recommendations:
            break
    return recommended_posts
