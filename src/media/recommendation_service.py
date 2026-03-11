import numpy as np



class VideoRecommender:
    def cosine_similarity(self, A, B):
        dot_product = np.dot(A, B)
        norm_a = np.linalg.norm(A)
        norm_b = np.linalg.norm(B)
        return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0

    def get_recommendations(self, matrix, user_idx, idx_to_video, n=5):
        target_user = matrix[user_idx]
        similarities = []

        for i, other_user in enumerate(matrix):
            if i == user_idx: continue
            sim = self.cosine_similarity(target_user, other_user)
            similarities.append((i, sim))

        # Сортируем по схожести
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for sim_user_idx, _ in similarities:
            for v_idx, is_liked in enumerate(matrix[sim_user_idx]):
                # Если похожий лайкнул, а наш — нет
                if is_liked == 1 and target_user[v_idx] == 0:
                    video_uuid = idx_to_video[v_idx]
                    if video_uuid not in recommendations:
                        recommendations.append(video_uuid)
                if len(recommendations) >= n:
                    return recommendations
        return recommendations