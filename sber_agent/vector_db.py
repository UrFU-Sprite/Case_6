import json
from typing import List, Dict, Optional, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


class VectorDB:
    """Simple vector DB wrapper using sentence-transformers + optional FAISS.
    Documents are dicts with keys: `id`, `text`, `meta`.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.docs: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self.index = None

    def add_documents(self, documents: List[Dict]):
        """Add documents and build/update index."""
        for d in documents:
            if "id" not in d:
                d["id"] = str(len(self.docs))
            self.docs.append(d)

        texts = [d["text"] for d in self.docs]
        self.embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        # normalize for cosine-sim
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)

    def query(self, text: str, k: int = 3) -> List[Tuple[Dict, float]]:
        q_emb = self.model.encode([text], convert_to_numpy=True)
        # normalize query for cosine
        q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)

        results: List[Tuple[Dict, float]] = []

        D, I = self.index.search(q_emb, k)
        # D are inner products because normalized -> cosine
        for idx, score in zip(I[0], D[0]):
            if idx < 0:
                continue
            results.append((self.docs[idx], float(score)))

        return results

    @classmethod
    def from_jsonl(cls, path: str, model_name: str = "all-MiniLM-L6-v2"):
        docs = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                docs.append(json.loads(line))
        inst = cls(model_name=model_name)
        inst.add_documents(docs)
        return inst
