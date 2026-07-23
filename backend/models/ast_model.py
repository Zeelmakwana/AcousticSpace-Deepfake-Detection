"""
AcousticSpace Backend — Model Definitions
==========================================
Week 2 deliverable (TASK-14): CNNBaseline architecture definition.
Week 3 deliverable (TASK-14): ASTDeepfakeClassifier architecture definition,
    load_ast_model(), predict_with_ast().

This module contains only architecture definitions and helper functions.
No weights are loaded at import time — loading is deferred to
``load_ast_model()`` which is called by ``backend/services/inference.py``
when ``MODEL_CHECKPOINT_PATH`` resolves to an existing checkpoint file.

Classes:
    CNNBaseline             — 3-block Conv2d baseline over log-mel spectrograms.
    ASTDeepfakeClassifier   — Hugging Face ASTModel backbone + classification head.

Functions:
    load_ast_model          — Load a saved checkpoint into ASTDeepfakeClassifier.
    predict_with_ast        — Run one inference pass and return the prediction dict.

Train with: ml/training/train.py
Inference:  loaded automatically by backend/services/inference.py when
            MODEL_CHECKPOINT_PATH points at a saved checkpoint.

References: FR-11.6, FR-11.7, MR-6, TDD §5.3, §5.4
"""

import os

import numpy as np
import torch
import torch.nn as nn


class CNNBaseline(nn.Module):
    """
    Simple CNN baseline over log-mel spectrograms.  [FR-11.6, TDD §5.3]

    Architecture:
        Conv block 1: Conv2d(1→16, 3×3, pad=1) → BatchNorm2d → ReLU → MaxPool2d(2)
        Conv block 2: Conv2d(16→32, 3×3, pad=1) → BatchNorm2d → ReLU → MaxPool2d(2)
        Conv block 3: Conv2d(32→64, 3×3, pad=1) → BatchNorm2d → ReLU → AdaptiveAvgPool2d(4,4)
        Classifier:   Flatten → Linear(1024→128) → ReLU → Dropout(0.3) → Linear(128→num_classes)

    Input shape:  (N, 1, H, W)  — single-channel log-mel spectrogram.
    Output shape: (N, num_classes) — raw logits (no softmax applied).

    A (1, 1, 128, 128) input tensor produces a (1, 2) output tensor.

    Args:
        n_mels:      Number of mel frequency bins (height dimension of input).
                     Unused in the convolutional path; kept for API consistency.
        num_classes: Number of output classes.  Default 2 (Real / Deepfake).
    """

    def __init__(self, n_mels: int = 128, num_classes: int = 2):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        return self.classifier(x)


class ASTDeepfakeClassifier(nn.Module):
    """
    Audio Spectrogram Transformer (AST) fine-tuned for real/deepfake classification.
    [FR-11.7, TDD §5.4]

    Purpose
        Leverages a pre-trained ``MIT/ast-finetuned-audioset`` backbone — which
        has already learned rich audio representations from the AudioSet corpus —
        and attaches a lightweight classification head so that only the head (and
        optionally the top transformer layers) needs to be fine-tuned on the
        deepfake detection task.  This transfer-learning approach is well-suited
        to settings where labelled deepfake audio data is scarce.

    Architecture overview
        1. **Backbone** — ``transformers.ASTModel`` loaded from the Hugging Face
           Hub checkpoint ``MIT/ast-finetuned-audioset-10-10-0.4593``.  The model
           processes a 2-D log-mel spectrogram via patch embedding followed by
           12 transformer encoder layers, and returns a pooled representation
           vector of size ``hidden_size`` (768 for the default checkpoint).

        2. **Classification head**::

               LayerNorm(hidden_size)
               → Linear(hidden_size → 256)
               → ReLU
               → Dropout(p=0.2)
               → Linear(256 → num_classes)

           Raw logits are returned; the caller is responsible for applying
           softmax when probabilities are required.

    Constructor arguments
        num_classes (int):
            Number of output classes.  Default ``2`` (index 0 = Real,
            index 1 = Deepfake).  Must match the label count in the training
            data and in any saved checkpoint.
        pretrained_name (str):
            Hugging Face Hub identifier for the AST backbone checkpoint.
            Default ``"MIT/ast-finetuned-audioset-10-10-0.4593"``.  Override
            to use a locally cached or alternative backbone.

    Input shape
        ``input_values``: ``(N, n_mels, T)`` float32 tensor — a batch of
        log-mel spectrograms with ``n_mels`` frequency bins and ``T`` time
        frames, as produced by ``transformers.ASTFeatureExtractor`` with
        default settings (``n_mels=128``, ``T=1024`` for 10 s clips).

    Output shape
        ``(N, num_classes)`` float32 tensor of raw logits.  No activation is
        applied; pass through ``torch.softmax(logits, dim=-1)`` to obtain
        class probabilities.
    """

    def __init__(self, num_classes: int = 2, pretrained_name: str = "MIT/ast-finetuned-audioset-10-10-0.4593"):
        super().__init__()
        from transformers import ASTModel

        self.backbone = ASTModel.from_pretrained(pretrained_name)
        hidden_size = self.backbone.config.hidden_size
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

    def forward(self, input_values: torch.Tensor) -> torch.Tensor:
        outputs = self.backbone(input_values=input_values)
        pooled = outputs.pooler_output
        return self.classifier(pooled)


def load_ast_model(checkpoint_path: str, device: torch.device) -> ASTDeepfakeClassifier:
    """
    Load a saved ASTDeepfakeClassifier checkpoint from disk.  [FR-11.10, TDD §5.4]

    The path is validated *before* the Hugging Face backbone is instantiated so
    that a missing file raises a clear, actionable error without triggering an
    unnecessary model download.

    Args:
        checkpoint_path: Absolute or relative path to a ``.pt`` file containing
                         the ``state_dict`` of an ``ASTDeepfakeClassifier`` instance
                         saved with ``torch.save(model.state_dict(), path)``.
        device:          ``torch.device`` on which the model will be placed
                         (e.g. ``torch.device("cpu")`` or ``torch.device("cuda:0")``).

    Returns:
        An ``ASTDeepfakeClassifier`` instance loaded with the checkpoint weights,
        moved to ``device``, and set to evaluation mode (``model.eval()``).

    Raises:
        FileNotFoundError: If ``checkpoint_path`` does not exist.  The error message
                           includes the full path to aid debugging.
        RuntimeError:      If the state_dict keys do not match the model architecture
                           (propagated from ``torch.nn.Module.load_state_dict``).
    """
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(
            f"[load_ast_model] Checkpoint not found at '{checkpoint_path}'. "
            "Train the model first with `python ml/training/train.py --model ast` "
            "or set MODEL_CHECKPOINT_PATH to an existing .pt file."
        )
    model = ASTDeepfakeClassifier()
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def predict_with_ast(
    model: ASTDeepfakeClassifier,
    y: np.ndarray,
    sr: int,
    features: dict,
    device: torch.device,
) -> dict:
    """
    Run a single inference pass with ``model`` and return a structured result.

    Args:
        model:    An ``ASTDeepfakeClassifier`` already loaded and set to eval mode.
        y:        Raw audio waveform as a 1-D float32 NumPy array.
        sr:       Sample rate of ``y`` in Hz (must match the extractor's expected rate).
        features: Pre-extracted feature dict produced by
                  ``backend/services/feature_extraction.py``.  Expected keys:
                  ``features["reverb"]["rt60_estimate_sec"]`` and
                  ``features["breathing"]["cadence_regularity_score"]``.
        device:   ``torch.device`` on which ``model`` lives.

    Returns:
        A ``dict`` with keys:
        - ``prediction``          (str):   ``"Real"`` or ``"Deepfake"``.
        - ``confidence``          (float): Confidence in the prediction, 0–100.
        - ``suspicious_segments`` (list):  Always ``[]``; reserved for future
                                           attention-based localisation.
        - ``room_acoustics_match``   (str): ``"High"`` or ``"Low"``.
        - ``breathing_consistency``  (str): ``"Consistent"`` or ``"Suspicious"``.
    """
    from transformers import ASTFeatureExtractor

    extractor = ASTFeatureExtractor.from_pretrained("MIT/ast-finetuned-audioset-10-10-0.4593")
    inputs = extractor(y, sampling_rate=sr, return_tensors="pt")
    input_values = inputs["input_values"].to(device)

    with torch.no_grad():
        logits = model(input_values)
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    fake_prob = float(probs[1])
    prediction = "Deepfake" if fake_prob >= 0.5 else "Real"
    confidence = round((fake_prob if prediction == "Deepfake" else 1 - fake_prob) * 100, 2)

    rt60 = features["reverb"]["rt60_estimate_sec"]
    breathing_score = features["breathing"]["cadence_regularity_score"]

    return {
        "prediction": prediction,
        "confidence": confidence,
        "suspicious_segments": [],  # populate via saliency/attention-based localization
        "room_acoustics_match": "Low" if (rt60 is None or rt60 >= 3.0) else "High",
        "breathing_consistency": "Suspicious"
        if (breathing_score is None or breathing_score < 0.3)
        else "Consistent",
    }
