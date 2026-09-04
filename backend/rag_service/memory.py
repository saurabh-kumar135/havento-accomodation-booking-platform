import re
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional
import numpy as np
from config import settings

logger = logging.getLogger(__name__)

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / (norm + 1e-8))

def is_meta_query(query: str) -> bool:
    patterns = [
        r"previous(ly)?",
        r"earlier",
        r"last (question|time|search|prompt|stay|message)",
        r"what did i (ask|say|search|look)",
        r"remember",
        r"before",
        r"history"
    ]
    q_lower = query.lower()
    return any(re.search(pat, q_lower) for pat in patterns)

class RAGMemoryService:
    def __init__(self):
        self._embedder = None
        
    def _get_embedder(self):
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding
                self._embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            except Exception:
                try:
                    from sentence_transformers import SentenceTransformer
                    self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                except Exception:
                    self._embedder = None
        return self._embedder

    def embed(self, text: str) -> List[float]:
        emb = self._get_embedder()
        if emb is None:
            vec = np.zeros(128, dtype=np.float32)
            for i, c in enumerate(text.lower()[:128]):
                vec[i % 128] += ord(c)
            norm = np.linalg.norm(vec)
            return (vec / (norm + 1e-8)).tolist()
            
        try:
            if hasattr(emb, "embed"):
                vec = list(emb.embed([text]))[0]
                norm = np.linalg.norm(vec)
                return (vec / (norm + 1e-8)).tolist()
            else:
                return emb.encode(text, normalize_embeddings=True).tolist()
        except Exception:
            return [0.0] * 384

    async def save_memory(self, user_id: str, user_msg: str, agent_res: str):
        if not user_id or not user_msg or not agent_res:
            return
            
        try:
            from utils.databaseUtil import db
            if not db.client:
                return
            coll = db.client[settings.DATABASE_NAME]["user_memories"]
            combined = f"User: {user_msg.strip()}\nAgent: {agent_res.strip()}"
            vector = self.embed(combined)
            
            await coll.insert_one({
                "user_id": str(user_id),
                "user_message": user_msg.strip(),
                "agent_response": agent_res.strip(),
                "combined_text": combined,
                "embedding": vector,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.warning(f"Could not save RAG memory: {e}")

    async def get_context(self, user_id: str, query: str, top_k: int = 3) -> str:
        if not user_id or not query:
            return ""
            
        try:
            from utils.databaseUtil import db
            if not db.client:
                return ""
            coll = db.client[settings.DATABASE_NAME]["user_memories"]
            cursor = coll.find({"user_id": str(user_id)}).sort("timestamp", -1).limit(30)
            docs = await cursor.to_list(length=30)
            
            if not docs:
                return ""
                
            q_vec = self.embed(query)
            meta = is_meta_query(query)
            
            scored = []
            for d in docs:
                if "embedding" in d and d["embedding"]:
                    sim = cosine_similarity(q_vec, d["embedding"])
                    scored.append((sim, d))
                    
            scored.sort(key=lambda x: x[0], reverse=True)
            
            selected = []
            for sim, doc in scored[:top_k]:
                if sim >= 0.3 or meta:
                    selected.append(doc)
                    
            if not selected and docs:
                selected = docs[:2]
                
            if not selected:
                return ""
                
            lines = ["\n📚 RELEVANT USER MEMORY & PREVIOUS INTERACTIONS:"]
            for i, doc in enumerate(selected, 1):
                lines.append(f"\n--- Past Memory {i} ---")
                lines.append(f"User asked: {doc.get('user_message')}")
                lines.append(f"Assistant answered: {doc.get('agent_response', '')[:250]}")
                
            lines.append("\n(Use this memory to answer questions like 'what did I ask before?' or retain preferences)\n")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Could not retrieve memory context: {e}")
            return ""

rag_memory_service = RAGMemoryService()
