from typing import Dict, Any

from .vector_db import VectorDB


class SupportAgent:
    """Support agent for Sber Инвестиции (1st-line).

    Behavior:
    - If vector DB returns a high-confidence match -> answer directly.
    - If moderate confidence -> escalate to 2nd line (L2).
    - If low-but-somewhat-related -> escalate to 3rd line (L3).
    - If unrelated -> mark out-of-scope.
    """

    def __init__(self, vdb: VectorDB,
                 answer_threshold: float = 0.65,
                 escalate_l2_threshold: float = 0.35,
                 escalate_l3_threshold: float = 0.15):
        self.vdb = vdb
        self.answer_threshold = answer_threshold
        self.escalate_l2_threshold = escalate_l2_threshold
        self.escalate_l3_threshold = escalate_l3_threshold

    def handle_query(self, query: str) -> Dict[str, Any]:
        results = self.vdb.query(query, k=3)
        top = results[0] if results else (None, 0.0)
        doc, score = top

        if doc is None:
            return {
                "action": "out_of_scope",
                "reason": "no_documents",
                "details": []
            }

        # Decision logic based on cosine-like score in [-1,1], realistically [0,1]
        if score >= self.answer_threshold:
            return {
                "action": "answer",
                "answer": doc["text"],
                "source": doc.get("meta", {}),
                "score": score
            }
        elif score >= self.escalate_l2_threshold:
            # give context to L2
            return {
                "action": "escalate",
                "level": "L2",
                "reason": "insufficient_confidence",
                "top_matches": [{"id": d[0]["id"], "score": d[1], "text": d[0]["text"]} for d in results]
            }
        elif score >= self.escalate_l3_threshold:
            return {
                "action": "escalate",
                "level": "L3",
                "reason": "only_weak_matches",
                "top_matches": [{"id": d[0]["id"], "score": d[1], "text": d[0]["text"]} for d in results]
            }
        else:
            return {
                "action": "out_of_scope",
                "reason": "not_relevant",
                "top_matches": [{"id": d[0]["id"], "score": d[1], "text": d[0]["text"]} for d in results]
            }
