"""
Weighted fusion of subsystem confidence signals with audit-grade transparency.

Final score = Σ (weight_k × clamp01(input_k)):
  LLM extraction, timeline parser, department classifier, appeal classifier.

Weights sum to 1.0. Missing subsystem inputs use documented neutral_imputation_value
(so the score is deterministic and explainable, not heuristic).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "llm": 0.35,
    "timeline": 0.25,
    "department": 0.20,
    "appeal": 0.20,
}


def default_fusion_weights() -> Dict[str, float]:
    return dict(_DEFAULT_WEIGHTS)


# Neutral draw when a signal is unavailable (explicit in API / UI disclosure)
NEUTRAL_IMPUTATION = 5.0 / 17.0  # ~0.294; distinct from subjective “0.5 guess”


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def fuse_action_plan_confidence(
    llm_score: Optional[float],
    timeline_score: Optional[float],
    department_score: Optional[float],
    appeal_score: Optional[float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    w = weights or dict(_DEFAULT_WEIGHTS)
    out = summarize_fusion_inputs(llm_score, timeline_score, department_score, appeal_score, w)
    return float(out["final_action_plan_confidence"])


def summarize_fusion_inputs(
    llm_score: Optional[float],
    timeline_score: Optional[float],
    department_score: Optional[float],
    appeal_score: Optional[float],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    w = weights or dict(_DEFAULT_WEIGHTS)
    wt_sum = sum(w.values())
    if abs(wt_sum - 1.0) > 1e-9:
        w = {k: v / wt_sum for k, v in w.items()}

    raw = {
        "llm": llm_score,
        "timeline": timeline_score,
        "department": department_score,
        "appeal": appeal_score,
    }

    effective: Dict[str, float] = {}
    imputed_flags: Dict[str, bool] = {}
    neutral = NEUTRAL_IMPUTATION

    # LLM: default 0.0 if absent (unknown extraction)
    lm_raw = raw["llm"]
    if lm_raw is None:
        effective["llm"] = neutral
        imputed_flags["llm"] = True
        lm_eff = neutral
    else:
        lm_eff = _clamp01(float(lm_raw))
        effective["llm"] = lm_eff
        imputed_flags["llm"] = False

    for key in ("timeline", "department", "appeal"):
        val = raw[key]
        if val is None:
            effective[key] = neutral
            imputed_flags[key] = True
            eff_val = neutral
        else:
            eff_val = _clamp01(float(val))
            effective[key] = eff_val
            imputed_flags[key] = False

    contributions = {
        "llm_weighted": round(effective["llm"] * w["llm"], 10),
        "timeline_weighted": round(effective["timeline"] * w["timeline"], 10),
        "department_weighted": round(effective["department"] * w["department"], 10),
        "appeal_weighted": round(effective["appeal"] * w["appeal"], 10),
    }
    total = round(
        contributions["llm_weighted"]
        + contributions["timeline_weighted"]
        + contributions["department_weighted"]
        + contributions["appeal_weighted"],
        10,
    )
    fused = round(max(0.0, min(1.0, total)), 6)
    wllm, wtl, wde, wap = w["llm"], w["timeline"], w["department"], w["appeal"]
    formula = (
        f"final = {wllm:.4g}×LLM + {wtl:.4g}×Timeline + {wde:.4g}×Department + {wap:.4g}×Appeal "
        "(effective terms clamped to [0,1]; missing subsystem → neutral imputation)."
    )

    return {
        "llm_confidence_raw": lm_raw if lm_raw is not None else None,
        "timeline_confidence_raw": raw["timeline"],
        "department_classifier_confidence_raw": raw["department"],
        "appeal_classifier_confidence_raw": raw["appeal"],
        "fusion_inputs_effective_clamped01": effective,
        "subsystem_imputed_default": imputed_flags,
        "neutral_imputation_value": neutral,
        "weights": dict(w),
        "weighted_contribution": contributions,
        "weighted_sum_precheck": total,
        "final_action_plan_confidence": fused,
        "fusion_formula": formula,
    }
