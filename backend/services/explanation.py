"""
AcousticSpace — Explainable AI (XAI) Layer
===========================================
Pure explanation layer — never touches the prediction algorithm.

``build_explanation()`` receives the *already-computed* prediction result and
the extracted acoustic features and returns a structured explanation dict that
is attached to the API response.  The prediction itself is never re-computed
or altered here.

Explanation fields
------------------
reason                  : str   — one-sentence plain-English verdict summary
confidence_explanation  : str   — what the confidence value means in context
room_mismatch_explanation: str  — why room acoustics matched or mismatched
breathing_explanation   : str   — what the breathing cadence pattern indicates
rt60_explanation        : str   — what the reverberation time value means
rir_explanation         : str   — what the RIR energy distribution indicates
risk_level              : str   — "Low" | "Medium" | "High" | "Critical"
recommendation          : str   — actionable next step for the user

Design rules
------------
- No imports from services.inference, services.audio_processing, or any ML lib.
- All thresholds are read from the feature dict, not recomputed.
- Returns a plain dict so it can be JSON-serialised directly.
- Every branch resolves to a non-empty string for every field.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Thresholds (documented for auditability)
# ---------------------------------------------------------------------------
_RT60_NATURAL_MIN = 0.10   # seconds — below this is suspiciously anechoic
_RT60_NATURAL_MAX = 2.50   # seconds — above this is suspiciously long
_RT60_IDEAL_MIN   = 0.20   # comfortable human speech environment lower bound
_RT60_IDEAL_MAX   = 0.80   # comfortable human speech environment upper bound

_RIR_STD_LOW      = 0.005  # near-zero std → flat/synthetic room response
_RIR_STD_HIGH     = 0.05   # high std → lively, variable room reflections

_BREATHING_HIGH   = 0.65   # regularity score ≥ this → natural cadence
_BREATHING_LOW    = 0.30   # regularity score < this → irregular / absent

_CONF_CERTAIN     = 85.0   # confidence ≥ this → "high certainty"
_CONF_MODERATE    = 60.0   # confidence ≥ this → "moderate certainty"
# below _CONF_MODERATE → borderline / low certainty


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _risk(prediction: str, confidence: float) -> str:
    """
    Map prediction + confidence to a four-level risk label.

    Real predictions:
        Low      — high-confidence authentic
        Low      — moderate-confidence authentic  (still low risk)
        Low      — borderline authentic

    Deepfake predictions:
        Medium   — low-confidence deepfake detection (borderline)
        High     — moderate-confidence deepfake detection
        Critical — high-confidence deepfake detection
    """
    if prediction == "Real":
        return "Low"
    # Deepfake path
    if confidence >= _CONF_CERTAIN:
        return "Critical"
    if confidence >= _CONF_MODERATE:
        return "High"
    return "Medium"


def _confidence_explanation(prediction: str, confidence: float) -> str:
    pct = f"{confidence:.1f}%"
    if prediction == "Real":
        if confidence >= _CONF_CERTAIN:
            return (
                f"The model is highly certain ({pct}) that this audio is authentic. "
                f"All acoustic indicators align strongly with a genuine recording."
            )
        if confidence >= _CONF_MODERATE:
            return (
                f"The model is moderately confident ({pct}) that the audio is authentic. "
                f"Most acoustic indicators are consistent with a real recording, though "
                f"one or more features showed minor irregularities."
            )
        return (
            f"The model leans toward authentic ({pct}), but the margin is narrow. "
            f"Several acoustic features produced ambiguous signals — independent "
            f"verification is advisable."
        )
    else:  # Deepfake
        if confidence >= _CONF_CERTAIN:
            return (
                f"The model is highly certain ({pct}) that this audio is synthetic. "
                f"Multiple acoustic indicators deviate strongly from natural recording "
                f"patterns, leaving little room for doubt."
            )
        if confidence >= _CONF_MODERATE:
            return (
                f"The model is moderately confident ({pct}) that this audio is synthetic. "
                f"Key room-acoustic and/or breathing features show suspicious patterns, "
                f"though not all indicators are conclusive."
            )
        return (
            f"The model suspects synthesis ({pct}), but with low certainty. "
            f"The acoustic evidence is mixed — this result should be treated as "
            f"a flag for further investigation rather than a definitive finding."
        )


def _room_explanation(room_match: str, rt60: float | None, rir_std: float) -> str:
    if room_match == "High":
        if rt60 is not None:
            return (
                f"Room acoustics match a genuine environment. The reverberation time "
                f"(RT60 ≈ {rt60:.2f}s) and RIR energy profile are consistent with a "
                f"real recording space. No anomalous reflection patterns were detected."
            )
        return (
            "Room acoustics are consistent with a genuine recording environment. "
            "The RIR energy profile shows natural reflection variance, and no "
            "anomalous room-acoustic artifacts were detected."
        )
    else:  # Low match
        parts: list[str] = []
        if rt60 is None:
            parts.append("the reverberation decay curve could not be resolved (silent or flat signal)")
        elif rt60 <= _RT60_NATURAL_MIN:
            parts.append(
                f"the RT60 ({rt60:.3f}s) is abnormally short — typical of an anechoic "
                f"or post-processed signal rather than a real room"
            )
        elif rt60 >= _RT60_NATURAL_MAX:
            parts.append(
                f"the RT60 ({rt60:.3f}s) is abnormally long — inconsistent with normal "
                f"speech recording environments"
            )
        if rir_std < _RIR_STD_LOW:
            parts.append(
                "the room impulse response energy is nearly flat "
                "(std ≈ {:.4f}), suggesting an anechoic or synthesised environment".format(rir_std)
            )
        if not parts:
            parts.append("one or more room-acoustic indicators deviate from natural patterns")
        joined = "; ".join(parts).capitalize()
        return (
            f"Room acoustics do not match a genuine recording environment. "
            f"{joined}. Synthetic audio is often generated in anechoic conditions "
            f"and lacks the natural reverberant tail of a real room."
        )


def _breathing_explanation(
    breathing_consistency: str,
    events: int,
    avg_gap: float | None,
    regularity: float | None,
) -> str:
    if breathing_consistency == "Consistent":
        if events == 0:
            return (
                "No distinct breathing gaps were detected, but the overall silence "
                "pattern between speech segments is consistent with natural human "
                "pacing. This does not raise a concern on its own."
            )
        reg_str = f"{regularity:.2f}" if regularity is not None else "—"
        gap_str = f"{avg_gap:.2f}s" if avg_gap is not None else "—"
        return (
            f"{events} inter-speech gap{'s' if events != 1 else ''} detected "
            f"(avg {gap_str}, regularity score {reg_str}/1.0). "
            f"The cadence is consistent with natural human breathing and pausing "
            f"patterns. No anomalies in respiratory pacing were found."
        )
    else:  # Suspicious
        if events == 0:
            return (
                "No breathing gaps were detected between speech segments. "
                "Natural human speech always contains micro-pauses and breathing events. "
                "Their complete absence is a strong indicator of text-to-speech (TTS) "
                "or voice-cloning synthesis."
            )
        reg_str = f"{regularity:.2f}" if regularity is not None else "—"
        gap_str = f"{avg_gap:.2f}s" if avg_gap is not None else "—"
        return (
            f"{events} inter-speech gap{'s' if events != 1 else ''} detected "
            f"(avg {gap_str}, regularity score {reg_str}/1.0). "
            f"The cadence is irregular or unnaturally uniform — synthetic voices "
            f"often produce either perfectly periodic silence (looped padding) or "
            f"erratic gaps that do not follow human breathing rhythms."
        )


def _rt60_explanation(rt60: float | None) -> str:
    if rt60 is None:
        return (
            "The RT60 (reverberation time) could not be estimated from this signal. "
            "This typically occurs with very short, nearly silent, or heavily compressed "
            "audio. Without a measurable decay curve, the reverberant environment "
            "cannot be characterised — this ambiguity is factored into the overall score."
        )
    if rt60 < _RT60_NATURAL_MIN:
        return (
            f"RT60 = {rt60:.3f}s — abnormally short. "
            f"Natural speech environments (offices, studios, living rooms) typically "
            f"produce RT60 values between {_RT60_IDEAL_MIN}s and {_RT60_IDEAL_MAX}s. "
            f"Values below {_RT60_NATURAL_MIN}s suggest the audio was either recorded "
            f"in a fully anechoic chamber (rare) or more likely generated synthetically "
            f"without environmental room modelling."
        )
    if rt60 > _RT60_NATURAL_MAX:
        return (
            f"RT60 = {rt60:.3f}s — abnormally long. "
            f"Reverberation times above {_RT60_NATURAL_MAX}s are uncommon in speech "
            f"recordings and may indicate artificial reverb added in post-processing "
            f"to mask synthesis artefacts, or a cavernous space inconsistent with "
            f"typical speech contexts."
        )
    if _RT60_IDEAL_MIN <= rt60 <= _RT60_IDEAL_MAX:
        return (
            f"RT60 = {rt60:.3f}s — within the natural speech range "
            f"({_RT60_IDEAL_MIN}–{_RT60_IDEAL_MAX}s). "
            f"This reverberation time is consistent with a typical indoor recording "
            f"environment such as an office, home studio, or meeting room."
        )
    # Acceptable but outside the ideal window
    qualifier = "slightly short" if rt60 < _RT60_IDEAL_MIN else "slightly long"
    return (
        f"RT60 = {rt60:.3f}s — {qualifier} for typical speech but still within "
        f"acceptable natural bounds ({_RT60_NATURAL_MIN}–{_RT60_NATURAL_MAX}s). "
        f"This value alone is not conclusive evidence of synthesis."
    )


def _rir_explanation(rir_mean: float, rir_std: float) -> str:
    mean_str = f"{rir_mean:.4f}"
    std_str  = f"{rir_std:.4f}"
    if rir_std < _RIR_STD_LOW:
        return (
            f"RIR energy: mean={mean_str}, std={std_str}. "
            f"The room impulse response energy is nearly flat — the standard deviation "
            f"({std_str}) is below {_RIR_STD_LOW}. "
            f"A real room produces varying percussive/reflection energy as sound "
            f"bounces off surfaces. Near-zero variance indicates an anechoic or "
            f"synthetically generated signal with no acoustic environment modelling."
        )
    if rir_std >= _RIR_STD_HIGH:
        return (
            f"RIR energy: mean={mean_str}, std={std_str}. "
            f"High room impulse response energy variance (std={std_str}) is consistent "
            f"with a lively, reverberant recording environment. Natural rooms produce "
            f"this kind of variable reflection energy, supporting authenticity."
        )
    return (
        f"RIR energy: mean={mean_str}, std={std_str}. "
        f"Room impulse response energy shows moderate variance, consistent with a "
        f"lightly damped indoor recording space. This is a neutral indicator — "
        f"neither strongly supporting nor contradicting synthesis."
    )


def _recommendation(prediction: str, risk_level: str, confidence: float) -> str:
    if prediction == "Real":
        if confidence >= _CONF_CERTAIN:
            return (
                "No action required. The audio exhibits strong markers of authenticity "
                "across all acoustic dimensions. It is safe to treat this recording "
                "as genuine."
            )
        return (
            "The audio is likely authentic, but confidence is not conclusive. "
            "If this recording will be used in a high-stakes context (legal, forensic, "
            "compliance), consider requesting a second analysis with additional context "
            "or a longer audio sample."
        )
    # Deepfake
    if risk_level == "Critical":
        return (
            "Do not use or distribute this audio without independent verification. "
            "High-confidence deepfake indicators were detected across multiple "
            "acoustic dimensions. Treat this recording as synthetic until proven "
            "otherwise. Report to relevant stakeholders immediately if received "
            "from an external source."
        )
    if risk_level == "High":
        return (
            "Exercise caution. Multiple acoustic anomalies consistent with synthetic "
            "generation were detected. Do not rely on this audio for consequential "
            "decisions without corroborating evidence. A forensic audio specialist "
            "review is recommended."
        )
    # Medium
    return (
        "This result is inconclusive. Some acoustic features suggest possible "
        "synthesis, but the evidence is not strong enough for a definitive finding. "
        "Collect additional audio samples from the same source and re-analyse, "
        "or consult a specialist for a manual review."
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_explanation(
    result: dict,
    features: dict,
    inference_mode: str,
) -> dict:
    """
    Build a structured XAI explanation for a completed analysis.

    This function is **purely additive** — it never modifies ``result`` and
    never invokes any prediction logic.  It reads the already-computed values
    from ``result`` and ``features`` and produces human-readable explanations.

    Parameters
    ----------
    result : dict
        The dict returned by ``InferenceEngine.predict()``.  Must contain:
        ``prediction``, ``confidence``, ``room_acoustics_match``,
        ``breathing_consistency``.

    features : dict
        The dict returned by ``extract_all_features()``.  Must contain:
        ``reverb.rt60_estimate_sec``, ``rir.rir_mean_energy``,
        ``rir.rir_std_energy``, ``breathing.breathing_events_detected``,
        ``breathing.avg_gap_sec``, ``breathing.cadence_regularity_score``.

    inference_mode : str
        ``"heuristic"`` or ``"ast-transformer"``.  Used for contextual notes.

    Returns
    -------
    dict with exactly 8 keys:
        reason, confidence_explanation, room_mismatch_explanation,
        breathing_explanation, rt60_explanation, rir_explanation,
        risk_level, recommendation
    """
    prediction: str   = result["prediction"]
    confidence: float = float(result["confidence"])
    room_match: str   = result["room_acoustics_match"]
    breathing_con: str = result["breathing_consistency"]

    # Extract acoustic sub-feature values defensively
    rt60: float | None     = features.get("reverb", {}).get("rt60_estimate_sec")
    rir_mean: float        = float(features.get("rir", {}).get("rir_mean_energy", 0.0))
    rir_std: float         = float(features.get("rir", {}).get("rir_std_energy", 0.0))
    breath_events: int     = int(features.get("breathing", {}).get("breathing_events_detected", 0))
    avg_gap: float | None  = features.get("breathing", {}).get("avg_gap_sec")
    regularity: float | None = features.get("breathing", {}).get("cadence_regularity_score")

    risk = _risk(prediction, confidence)

    # ---- Build the reason sentence -----------------------------------------
    mode_note = (
        "via AST-transformer model"
        if inference_mode == "ast-transformer"
        else "via heuristic acoustic analysis"
    )
    if prediction == "Real":
        reason = (
            f"This audio was classified as authentic ({mode_note}). "
            f"Room acoustics, reverberation characteristics, and breathing patterns "
            f"are all consistent with a genuine human recording in a natural environment."
        )
    else:
        factors: list[str] = []
        if room_match == "Low":
            factors.append("anomalous room acoustics")
        if breathing_con == "Suspicious":
            factors.append("irregular/absent breathing cadence")
        if rt60 is not None and (rt60 < _RT60_NATURAL_MIN or rt60 > _RT60_NATURAL_MAX):
            factors.append("out-of-range reverberation time")
        if rir_std < _RIR_STD_LOW:
            factors.append("near-flat room impulse response")
        if not factors:
            factors.append("acoustic feature deviations")
        factor_str = ", ".join(factors)
        reason = (
            f"This audio was classified as a deepfake ({mode_note}) "
            f"based on: {factor_str}. "
            f"The combination of these indicators deviates from patterns observed "
            f"in authentic human recordings."
        )

    return {
        "reason":                    reason,
        "confidence_explanation":    _confidence_explanation(prediction, confidence),
        "room_mismatch_explanation": _room_explanation(room_match, rt60, rir_std),
        "breathing_explanation":     _breathing_explanation(
                                         breathing_con, breath_events, avg_gap, regularity
                                     ),
        "rt60_explanation":          _rt60_explanation(rt60),
        "rir_explanation":           _rir_explanation(rir_mean, rir_std),
        "risk_level":                risk,
        "recommendation":            _recommendation(prediction, risk, confidence),
    }
