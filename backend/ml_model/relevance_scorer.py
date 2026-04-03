import os
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Scorer running on: {device}")


class RelevanceScorer:
    def __init__(self):
        # saved_path = "ml_model/saved_model"
        saved_path = "ml_model/saved_model2"
        if os.path.exists(saved_path):
            print("Loading fine-tuned E5 model...")
            self.model = SentenceTransformer(saved_path, device=device)
        else:
            print("Loading base E5 model...")
            self.model = SentenceTransformer("intfloat/e5-base-v2", device=device)

    def score(self, instruction, query, paper):
        title    = paper.get("title") or ""
        abstract = paper.get("abstract") or ""
        paper_text = f"{title} {abstract}".strip()

        if not paper_text:
            # fall back to title + venue if no abstract
            paper_text = f"{title} {paper.get('venue', '')}".strip()

        if not paper_text:
            return 0.0

        try:
            query_vec = self.model.encode([f"query: {instruction}"])
            paper_vec = self.model.encode([f"passage: {paper_text}"])
            return float(cosine_similarity(query_vec, paper_vec)[0][0])
        except Exception as e:
            print(f"Scoring error: {e}")
            return 0.0

    def classify(self, instruction, query, paper):
        score = self.score(instruction, query, paper)
        # if score >= 0.87:
        #     return "ml_relevant"
        # elif score >= 0.70:
        #     return "ml_less_relevant"
        # else:
        #     return "ml_irrelevant"
        
        if score >= 0.55:
            return "ml_relevant"
        elif score >= 0.20:
            return "ml_less_relevant"
        else:
            return "ml_irrelevant"
        
    def classify_from_score(self, score):
        if score >= 0.55:
            return "ml_relevant"
        elif score >= 0.25:
            return "ml_less_relevant"
        else:
            return "ml_irrelevant"


_scorer_instance = None

def get_scorer():
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = RelevanceScorer()
    return _scorer_instance

def score_paper(instruction, query, paper):
    return get_scorer().score(instruction, query, paper)

def classify_paper(instruction, query, paper):
    return get_scorer().classify(instruction, query, paper)