from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_recommendations(current_post, all_posts, num_recommendations=3):
    
    post_texts = []
    index_to_post_id = {}
    current_post_index = -1

    for i, post in enumerate(all_posts):
        post_texts.append(post.title + " " + post.content)
        index_to_post_id[i] = post.id
        if post.id == current_post.id:
            current_post_index = i

    if current_post_index == -1:
        return []

    tfidf_vectorizer = TfidfVectorizer()
    
    tfidf_matrix = tfidf_vectorizer.fit_transform(post_texts)

    cosine_sim_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    similarity_scores = list(enumerate(cosine_sim_matrix[current_post_index]))

    sorted_scores = sorted(similarity_scores, key=lambda item: item[1], reverse=True)

    recommended_post_indices = []
    for index, score in sorted_scores:
        if index == current_post_index:
            continue
        recommended_post_indices.append(index)
        if len(recommended_post_indices) == num_recommendations:
            break
    
    recommended_posts = []
    for index in recommended_post_indices:
        post_id = index_to_post_id[index]
        rec_post = next((p for p in all_posts if p.id == post_id), None)
        if rec_post:
            recommended_posts.append(rec_post)

    return recommended_posts

def get_user_recommendations(user_history_posts, all_posts, num_recommendations=10):
    if not user_history_posts:
        return []

    post_texts = [p.title + " " + p.content for p in all_posts]
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(post_texts)
    
    post_id_to_index = {post.id: i for i, post in enumerate(all_posts)}

    history_indices = [post_id_to_index[p.id] for p in user_history_posts if p.id in post_id_to_index]
    if not history_indices:
        return []
        
    history_vectors = tfidf_matrix[history_indices]
    
    user_profile_vector = np.asarray(history_vectors.mean(axis=0))

    similarity_scores = cosine_similarity(user_profile_vector, tfidf_matrix)
    
    scores = list(enumerate(similarity_scores[0]))
    
    sorted_scores = sorted(scores, key=lambda item: item[1], reverse=True)

    recommended_posts = []
    history_post_ids = {p.id for p in user_history_posts}

    for index, score in sorted_scores:
        post_id = all_posts[index].id
        if post_id not in history_post_ids:
            recommended_posts.append(all_posts[index])
        
        if len(recommended_posts) >= num_recommendations:
            break
            
    return recommended_posts