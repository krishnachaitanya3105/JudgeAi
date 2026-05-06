"""
Embedding generation (384-d MiniLM aligned with classifier model).
"""

from __future__ import annotations

from typing import List

from backend.services.sentence_encoder import get_minilm_encoder


def generate_embedding(text: str) -> List[float]:
    """
    Produce a normalized 384-float embedding suitable for pgvector cosine search.
    """
    t = (text or "").strip()
    if not t:
        return [0.0] * 384
    encoder = get_minilm_encoder()
    # MiniLM only uses the first ~512 tokens anyway (approx 2000-3000 chars)
    # Truncating early saves significant RAM and tokenizer overhead
    vec = encoder.encode(t[:3000], convert_to_numpy=True)
    import numpy as np
    import gc

    v = vec.astype(np.float64)
    n = np.linalg.norm(v)
    if n > 0:
        v = v / n
        
    result = v.tolist()
    
    # Cleanup memory
    del vec
    del v
    gc.collect()
    
    return result


def embedding_dimensions() -> int:
    return 384
