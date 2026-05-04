"""
Department classifier using sentence-transformers (all-MiniLM-L6-v2) cosine similarity.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

_department_profiles: Dict[str, str] = {
    "Education": "school examination board university teacher student scholarship RTE admission syllabus",
    "Revenue": "land revenue mutation tax collector stamp duty tribunal assessment encumbrance",
    "Police": " FIR investigation arrest custody superintendent law order security traffic",
    "Transport": "vehicle registration licence motor MV Act road transport highways traffic accident",
    "Municipal Administration": "corporation municipality ward civic drains sanitation building bye-law encroachment ULB",
    "Health": "hospital clinic medical negligence drug licence public health sanitary PHC",
    "Finance": "treasury disbursement pension budget allotment audit accountant payment",
    "Rural Development": "panchayat village rural scheme MGNREGA ICDS watershed agriculture cooperative",
}


from backend.services.sentence_encoder import get_minilm_encoder


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def classify_department(judgment_excerpt: str) -> Dict[str, Any]:
    """
    Embed excerpt and profiles; pick best cosine match.

    Returns department, confidence (0–1 compatible with cosine similarity of normalized STS vectors).
    """
    text = (judgment_excerpt or "").strip()
    if not text:
        return {"department": "", "confidence_score": 0.0}

    model = get_minilm_encoder()
    labels = list(_department_profiles.keys())
    profile_texts = [_department_profiles[k] for k in labels]

    excerpt_vec = model.encode(text[:8000], convert_to_numpy=True).tolist()
    profile_vecs = model.encode(profile_texts, convert_to_numpy=True)

    best_label = ""
    best_sim = -1.0
    for i, label in enumerate(labels):
        pv = profile_vecs[i].tolist()
        sim = _cosine_similarity(excerpt_vec, pv)
        if sim > best_sim:
            best_sim = sim
            best_label = label

    return {
        "department": best_label,
        "confidence_score": round(max(0.0, min(1.0, (best_sim + 1) / 2)), 4),
        "best_cosine_similarity": round(best_sim, 6),
        "alternative_llm_fallback": False,
    }


def pick_department(
    llm_department: Optional[str],
    excerpt: str,
    override_threshold: float = 0.75,
) -> Dict[str, Any]:
    """
    If classifier confidence > threshold, override LLM department; else keep LLM hint if any.
    """
    cls = classify_department(excerpt)
    conf = cls["confidence_score"]
    dept = cls["department"]

    llm_clean = (llm_department or "").strip()

    chosen = dept if conf > override_threshold and dept else llm_clean or dept
    overridden = bool(conf > override_threshold and dept and dept != llm_clean)

    return {
        "department": chosen,
        "classifier_confidence": conf,
        "classifier_raw_department": dept,
        "llm_department": llm_clean,
        "overridden": overridden,
    }
