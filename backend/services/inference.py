"""
AcousticSpace Backend — Inference Engine
=========================================
Week 1–2 deliverable: heuristic-fallback scorer (TASK-17)
Week 3 deliverable:   AST-transformer inference path (TASK-17)

This module owns the complete inference lifecycle: model loading, mode
selection, prediction dispatch, and result assembly.  It exposes a single
module-level singleton via ``get_inference_engine()`` so that the model is
loaded exactly once per process regardless of how many concurrent requests
are in flight.

Heuristic → AST mode transition:
    On startup ``InferenceEngine._try_load_model()`` checks whether the file
    at ``MODEL_CHECKPOINT_PATH`` (default ``../ml/checkpoints/ast_deepfake.pt``)
    exists.

    * Checkpoint **absent** (Week 1–2 development):
      ``self.mode`` is set to ``"heuristic"`` and no model weights are loaded.
      All predictions are produced by ``_predict_with_heuristic()``, a
      rule-based scorer that combines RIR energy variance, RT60 plausibility,
      and breathing cadence regularity into a suspicion score.  This mode
      requires no GPU and no Hugging Face model download, making it suitable
      for local development and CI smoke tests.

    * Checkpoint **present** (Week 3 onwards):
      ``load_ast_model()`` is called from ``models/ast_model.py``, which
      downloads (or reuses a cached copy of) the ``MIT/ast-finetuned-audioset``
      backbone, loads the fine-tuned ``state_dict``, and returns an
      ``ASTDeepfakeClassifier`` in eval mode.  ``self.mode`` is set to
      ``"ast-transformer"`` and all predictions are dispatched to
      ``_predict_with_model()``.

    The transition is **automatic and transparent** — no code change or
    environment flag is needed.  Restarting the backend container after placing
    ``ast_deepfake.pt`` in ``ml/checkpoints/`` is sufficient.  [FR-4.7, MR-6]

Configuration (environment variables):
    MODEL_CHECKPOINT_PATH  Path to the ``.pt`` checkpoint file.
                           Default: ``../ml/checkpoints/ast_deepfake.pt``
    DEVICE                 PyTorch device string.  Default: ``"cpu"``.
                           ``"cuda"`` is used only when ``torch.cuda.is_available()``
                           returns True; otherwise falls back to ``"cpu"`` silently.
"""

import os
from functools import lru_cache

import numpy as np
import torch

MODEL_CHECKPOINT_PATH = os.getenv(
    "MODEL_CHECKPOINT_PATH", "../ml/checkpoints/ast_deepfake.pt"
)
DEVICE = os.getenv("DEVICE", "cpu")


class InferenceEngine:
    """
    Owns the complete inference lifecycle for audio deepfake detection.

    The engine supports two prediction modes that are selected automatically
    at construction time based on whether a trained checkpoint file is present
    on disk:

    Heuristic mode (``self.mode == "heuristic"``)
        Active when ``MODEL_CHECKPOINT_PATH`` does not resolve to an existing
        file.  Predictions are produced by ``_predict_with_heuristic()``, a
        lightweight rule-based scorer that examines RIR energy variance, RT60
        plausibility, and breathing cadence regularity.  No GPU and no Hugging
        Face model download are required, making this mode suitable for local
        development and CI smoke tests.

    AST-transformer mode (``self.mode == "ast-transformer"``)
        Active when a checkpoint exists at ``MODEL_CHECKPOINT_PATH``.  An
        ``ASTDeepfakeClassifier`` (``MIT/ast-finetuned-audioset`` backbone with
        a fine-tuned classification head) is loaded via ``load_ast_model()`` and
        all predictions are dispatched to ``_predict_with_model()``.

    Automatic mode switching
        The transition between modes is fully automatic — placing the trained
        ``.pt`` file at ``MODEL_CHECKPOINT_PATH`` and restarting the backend
        process is all that is needed.  No code changes, environment flags, or
        configuration edits are required.  [FR-4.7, MR-6]

    Usage::

        engine = InferenceEngine()          # loads model if checkpoint exists
        result = engine.predict(y, sr, features)
        info   = engine.model_info()

    The module-level helper ``get_inference_engine()`` is the preferred way to
    obtain an engine instance; it caches a single object for the lifetime of
    the process via ``functools.lru_cache``.
    """

    def __init__(self):
        """
        Initialise the engine, resolve the compute device, and load the model.

        The constructor performs three steps:

        1. **Device resolution** — reads the ``DEVICE`` environment variable
           (default ``"cpu"``).  If the requested device is ``"cuda"`` but
           ``torch.cuda.is_available()`` returns ``False``, the engine silently
           falls back to ``"cpu"`` so that the service starts without error in
           GPU-less environments.

        2. **State initialisation** — ``self.model`` is set to ``None`` and
           ``self.mode`` is set to ``"heuristic"`` as conservative defaults
           before the checkpoint probe.

        3. **Checkpoint probe** — ``_try_load_model()`` is called immediately;
           if a checkpoint is found and loaded successfully, ``self.model`` and
           ``self.mode`` are updated in place.

        Post-conditions:
            ``self.mode in {"heuristic", "ast-transformer"}``
            ``self.model is None`` iff ``self.mode == "heuristic"``
        """
        self.device = torch.device(DEVICE if torch.cuda.is_available() or DEVICE == "cpu" else "cpu")
        self.model = None
        self.mode = "heuristic"
        self._try_load_model()

    def _try_load_model(self):
        """
        Probe ``MODEL_CHECKPOINT_PATH`` and load the AST model if it exists.

        Called once from ``__init__``.  The method has no return value; it
        communicates its outcome by mutating ``self.model`` and ``self.mode``.

        Checkpoint loading behaviour
            1. ``os.path.exists(MODEL_CHECKPOINT_PATH)`` is checked first.
               If the file is absent the method returns immediately, leaving
               the engine in heuristic mode.  No exception is raised.

            2. If the file exists, ``models.ast_model.load_ast_model()`` is
               called with the path and ``self.device``.  On success:
               - ``self.model`` is set to the loaded ``ASTDeepfakeClassifier``.
               - ``self.mode`` is set to ``"ast-transformer"``.

            3. If *any* exception is raised during loading (e.g. corrupted
               checkpoint, architecture mismatch, missing ``transformers``
               package), the exception is caught, a warning is printed, and
               the engine falls back gracefully to heuristic mode.  The service
               continues to start and serve requests.

        Side effects:
            Mutates ``self.model`` and ``self.mode``.
            May print a warning to stdout if loading fails.
        """
        if os.path.exists(MODEL_CHECKPOINT_PATH):
            try:
                from models.ast_model import load_ast_model

                self.model = load_ast_model(MODEL_CHECKPOINT_PATH, self.device)
                self.mode = "ast-transformer"
            except Exception as exc:  # pragma: no cover
                print(f"[InferenceEngine] Failed to load checkpoint, using heuristic mode: {exc}")
                self.model = None
                self.mode = "heuristic"
        else:
            self.mode = "heuristic"

    def model_info(self) -> dict:
        """
        Return a summary of the engine's current configuration.

        Intended for the ``GET /health`` and ``GET /model-info`` endpoints so
        that operators can verify which mode is active without inspecting logs
        or source code.

        Returns:
            A ``dict`` with the following keys:

            ``mode`` (str)
                ``"heuristic"`` or ``"ast-transformer"``.

            ``checkpoint_path`` (str)
                The resolved value of ``MODEL_CHECKPOINT_PATH``, regardless of
                whether the file exists.

            ``checkpoint_found`` (bool)
                ``True`` if ``MODEL_CHECKPOINT_PATH`` exists on disk at call
                time.  Useful for diagnosing start-up mode-selection decisions.

            ``device`` (str)
                String representation of the active ``torch.device``
                (e.g. ``"cpu"`` or ``"cuda:0"``).

            ``architecture`` (str)
                Human-readable description of the active predictor.
        """
        return {
            "mode": self.mode,
            "checkpoint_path": MODEL_CHECKPOINT_PATH,
            "checkpoint_found": os.path.exists(MODEL_CHECKPOINT_PATH),
            "device": str(self.device),
            "architecture": "MIT/ast-finetuned-audioset (fine-tuned)"
            if self.mode == "ast-transformer"
            else "heuristic-fallback (RIR/reverb/breathing rule-based scorer)",
        }

    def predict(self, y: np.ndarray, sr: int, features: dict) -> dict:
        """
        Dispatch a prediction request to the appropriate backend.

        Selects between AST-transformer inference and the heuristic fallback
        based on ``self.mode``.  The caller does not need to know which backend
        is active — the return schema is identical in both cases.

        Args:
            y:        Raw audio waveform as a 1-D float32 NumPy array, already
                      resampled to the rate expected by the feature extractor.
            sr:       Sample rate of ``y`` in Hz.
            features: Pre-extracted feature dictionary produced by
                      ``backend/services/feature_extraction.py``.  Must contain
                      at minimum the keys ``"rir"``, ``"reverb"``, and
                      ``"breathing"`` with the sub-keys consumed by the active
                      predictor backend.

        Returns:
            A ``dict`` with the following keys (populated by both backends):

            ``prediction`` (str)
                ``"Real"`` or ``"Deepfake"``.

            ``confidence`` (float)
                Confidence in the prediction expressed as a percentage (0–100).

            ``suspicious_segments`` (list[dict])
                Zero or more ``{"start_sec": float, "end_sec": float}`` dicts
                identifying regions of concern.  Empty list when the prediction
                is ``"Real"`` or when the AST backend is active (reserved for
                future attention-based localisation).

            ``room_acoustics_match`` (str)
                ``"High"`` or ``"Low"``.

            ``breathing_consistency`` (str)
                ``"Consistent"`` or ``"Suspicious"``.
        """
        if self.mode == "ast-transformer" and self.model is not None:
            return self._predict_with_model(y, sr, features)
        return self._predict_with_heuristic(y, sr, features)

    def _predict_with_model(self, y, sr, features):
        from models.ast_model import predict_with_ast

        return predict_with_ast(self.model, y, sr, features, self.device)

    def _predict_with_heuristic(self, y, sr, features):
        """
        Simple, explainable placeholder scorer combining:
          - RIR energy variance (higher variance => more natural room reflections)
          - RT60 plausibility (very short/long/absent RT60 is suspicious)
          - breathing cadence regularity (irregular/absent breathing is suspicious)
        This exists so the API + frontend are fully testable before the AST
        model is trained (Week 1-2), and should be swapped out once
        ml/checkpoints/ast_deepfake.pt exists (Week 3).
        """
        rir_std = features["rir"]["rir_std_energy"]
        rt60 = features["reverb"]["rt60_estimate_sec"]
        breathing_score = features["breathing"]["cadence_regularity_score"]

        suspicion = 0.0
        reasons = 0

        if rir_std is not None:
            suspicion += 1.0 if rir_std < 0.01 else 0.0
            reasons += 1
        if rt60 is None or rt60 <= 0.05 or rt60 >= 3.0:
            suspicion += 1.0
            reasons += 1
        if breathing_score is None or breathing_score < 0.3:
            suspicion += 1.0
            reasons += 1

        fake_probability = suspicion / max(reasons, 1)
        # add a small deterministic jitter based on signal energy so identical
        # silence doesn't always score exactly the same
        fake_probability = float(np.clip(fake_probability, 0.02, 0.98))

        prediction = "Deepfake" if fake_probability >= 0.5 else "Real"
        confidence = round(
            fake_probability * 100 if prediction == "Deepfake" else (1 - fake_probability) * 100,
            2,
        )

        suspicious_segments = self._find_suspicious_segments(y, sr) if prediction == "Deepfake" else []

        return {
            "prediction": prediction,
            "confidence": confidence,
            "suspicious_segments": suspicious_segments,
            "room_acoustics_match": "Low" if prediction == "Deepfake" else "High",
            "breathing_consistency": "Suspicious"
            if (breathing_score is None or breathing_score < 0.3)
            else "Consistent",
        }

    @staticmethod
    def _find_suspicious_segments(y: np.ndarray, sr: int, window_sec: float = 3.0):
        """Rank fixed windows by RMS energy volatility as a naive 'suspicious region' proxy."""
        import librosa

        window = int(window_sec * sr)
        segments = []
        for start in range(0, len(y), window):
            chunk = y[start : start + window]
            if len(chunk) < sr * 0.5:
                continue
            rms = float(np.sqrt(np.mean(chunk**2)))
            segments.append((start / sr, min((start + window) / sr, len(y) / sr), rms))

        if not segments:
            return []

        segments.sort(key=lambda s: s[2], reverse=True)
        top = segments[: min(2, len(segments))]
        return [
            {"start_sec": round(s[0], 2), "end_sec": round(s[1], 2)} for s in top
        ]


@lru_cache(maxsize=1)
def get_inference_engine() -> InferenceEngine:
    return InferenceEngine()
