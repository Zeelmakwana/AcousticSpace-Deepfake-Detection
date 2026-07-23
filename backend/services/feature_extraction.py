"""
AcousticSpace Backend — Feature Extraction Service
===================================================
Week 1 deliverable  (TASK-09): six spectro-temporal extractors
Week 2 deliverable  (TASK-10): estimate_rir_proxy
Week 2 deliverable  (TASK-11): estimate_rt60
Week 2 deliverable  (TASK-12): estimate_breathing_cadence
Week 2 deliverable  (TASK-13): extract_all_features (facade)

This module implements the complete acoustic feature pipeline for deepfake
detection.  All extractor functions are pure — they take (y, sr) and return
a NumPy array or dict, with no side effects and no shared state.   [FR-3.2]

Feature set:
    Spectro-temporal (TASK-09):
        - MFCC (20 coefficients)         — compact spectral envelope  [FR-3.1]
        - Chroma (12 bins)               — harmonic content           [FR-3.1]
        - Spectral Centroid              — brightness proxy           [FR-3.1]
        - Spectral Contrast (7 bands)    — valley/peak contrast       [FR-3.1]
        - Zero Crossing Rate             — noisiness / voicing        [FR-3.1]
        - RMS Energy                     — loudness envelope          [FR-3.1]

    Room acoustics (TASK-10 – TASK-12):
        - RIR Proxy (HPSS-based)         — room reflection proxy      [FR-3.1]
        - RT60 (Schroeder integration)   — reverberation time         [FR-3.1]
        - Breathing Cadence              — inter-speech gap analysis  [FR-3.1]

    Facade (TASK-13):
        - extract_all_features()         — single call for all above  [FR-3.2]

Design note — blind RIR estimation:
    True Room Impulse Response extraction requires a known excitation signal
    (e.g. a sine sweep) played in the room.  For uploaded speech "in the wild"
    we use blind estimation: HPSS percussive-component energy as a proxy for
    room reflections, and Schroeder backward integration for RT60.  These are
    relative indicators, not lab-grade measurements.  [C-5]
"""

import librosa
import numpy as np
from scipy.signal import hilbert


def extract_mfcc(y: np.ndarray, sr: int, n_mfcc: int = 20) -> np.ndarray:
    """
    Compute Mel-Frequency Cepstral Coefficients (MFCCs).  [FR-3.1]

    Args:
        y:      Mono float32 audio array.
        sr:     Sample rate in Hz.
        n_mfcc: Number of MFCC coefficients (default 20).

    Returns:
        2D array of shape (n_mfcc, T) — one coefficient vector per time frame.
    """
    return librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)


def extract_chroma(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Compute a chromagram (chroma STFT) from the audio signal.  [FR-3.1]

    Args:
        y:  Mono float32 audio array.
        sr: Sample rate in Hz.

    Returns:
        2D array of shape (12, T) — one chroma vector per time frame,
        representing energy across the 12 pitch classes (C through B).
    """
    return librosa.feature.chroma_stft(y=y, sr=sr)


def extract_spectral_centroid(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Compute the spectral centroid (brightness) of the audio signal.  [FR-3.1]

    Args:
        y:  Mono float32 audio array.
        sr: Sample rate in Hz.

    Returns:
        2D array of shape (1, T) — centroid frequency (Hz) per time frame.
    """
    return librosa.feature.spectral_centroid(y=y, sr=sr)


def extract_spectral_contrast(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Compute spectral contrast across frequency sub-bands.  [FR-3.1]

    Measures the difference between peaks and valleys in each sub-band,
    capturing spectral shape information beyond the centroid.

    Args:
        y:  Mono float32 audio array.
        sr: Sample rate in Hz.

    Returns:
        2D array of shape (7, T) — contrast values for 6 sub-bands plus
        the top octave, one vector per time frame.
    """
    return librosa.feature.spectral_contrast(y=y, sr=sr)


def extract_zero_crossing_rate(y: np.ndarray) -> np.ndarray:
    """
    Compute the zero-crossing rate of the audio signal.  [FR-3.1]

    High zero-crossing rates indicate noisy or unvoiced segments;
    low rates indicate voiced or tonal content.

    Args:
        y: Mono float32 audio array.

    Returns:
        2D array of shape (1, T) — zero-crossing rate per time frame.
    """
    return librosa.feature.zero_crossing_rate(y)


def extract_rms_energy(y: np.ndarray) -> np.ndarray:
    """
    Compute the root-mean-square (RMS) energy of the audio signal.  [FR-3.1]

    Captures the loudness envelope of the signal over time.

    Args:
        y: Mono float32 audio array.

    Returns:
        2D array of shape (1, T) — RMS energy per time frame.
    """
    return librosa.feature.rms(y=y)


def estimate_rir_proxy(y: np.ndarray, sr: int) -> dict:
    """
    Approximate a room-impulse-response fingerprint from reverberant speech.

    Algorithm (blind RIR proxy via HPSS):  [FR-3.1, TDD §3.5, C-5]
      1. Harmonic-Percussive Source Separation (HPSS) decomposes the signal
         into a harmonically stable component (pitched voice) and a percussive /
         transient component (room reflections, clicks, reverb tails).
      2. The RMS energy of the percussive component is used as a proxy for the
         room's impulse response energy profile over time.
      3. Statistical summaries (mean and std) of this energy curve are the
         features fed to the inference engine.

    A real recording in a reverberant room will have a higher and more variable
    percussive energy curve than a synthetic or anechoic signal, which produces
    a near-zero percussive component.

    Args:
        y:  Mono float32 audio array at TARGET_SAMPLE_RATE.
        sr: Sample rate in Hz (used implicitly by librosa.effects.hpss).

    Returns:
        Dict with exactly three keys:
          - "rir_energy_curve"  list[float]  RMS energy of the percussive
                                             component, first 200 frames.
          - "rir_mean_energy"   float        Mean of the energy curve (≥ 0).
          - "rir_std_energy"    float        Std dev of the energy curve (≥ 0).
                                             Lower std → more anechoic / synthetic.
    """
    _harmonic, percussive = librosa.effects.hpss(y)
    rir_energy_curve = librosa.feature.rms(y=percussive)[0]
    return {
        "rir_energy_curve": rir_energy_curve.tolist()[:200],
        "rir_mean_energy": float(np.mean(rir_energy_curve)),
        "rir_std_energy": float(np.std(rir_energy_curve)),
    }


def estimate_rt60(y: np.ndarray, sr: int) -> dict:
    """
    Blind RT60 (reverberation time) estimate via Schroeder backward integration.
    [FR-3.1, FR-3.3, NFR-4.2, TDD §3.5]

    Algorithm:
      1. Compute the analytic signal via the Hilbert transform to obtain the
         instantaneous energy envelope.
      2. Apply Schroeder backward integration: cumulative sum of the reversed
         envelope, reversed again, converted to dB.
      3. Fit a linear slope between the -5 dB and -35 dB points of the decay
         curve (the EDT-equivalent T20 window).
      4. Extrapolate the slope to -60 dB to derive the RT60 estimate.
      5. Return None without raising if any step fails (silent signal, numerical
         instability, insufficient decay range, etc.).

    The entire computation is wrapped in a single try/except so that no
    edge-case input (empty array, single sample, all-zeros, NaN/inf) can
    propagate an exception to the caller.  [NFR-4.2]

    Args:
        y:  Mono float32 audio array at TARGET_SAMPLE_RATE.
        sr: Sample rate in Hz — used to convert sample-index distances to
            seconds when computing the decay slope.

    Returns:
        Dict with exactly one key:
          - "rt60_estimate_sec"  float | None
              Positive float rounded to 3 decimal places when the decay
              curve yields a valid slope; None for silent, near-zero, or
              otherwise unresolvable signals.
    """
    try:
        analytic_signal = hilbert(y)
        envelope = np.abs(analytic_signal) ** 2
        envelope = np.clip(envelope, 1e-12, None)

        # Schroeder backward integration
        schroeder = np.cumsum(envelope[::-1])[::-1]
        schroeder_db = 10 * np.log10(schroeder / (np.max(schroeder) + 1e-12) + 1e-12)

        # Find -5 dB to -35 dB decay slope (T20 window → extrapolate to -60 dB)
        idx_start = np.argmax(schroeder_db <= -5)
        idx_end = np.argmax(schroeder_db <= -35)
        if idx_end <= idx_start:
            raise ValueError("Insufficient decay range for slope fitting")

        slope = (schroeder_db[idx_end] - schroeder_db[idx_start]) / (
            (idx_end - idx_start) / sr
        )
        rt60 = -60 / slope if slope != 0 else None
    except Exception:
        rt60 = None

    # Use explicit `is not None` guard — a computed rt60 of 0.0 must not be
    # treated as missing.  [AC-3]
    return {"rt60_estimate_sec": round(float(rt60), 3) if rt60 is not None else None}


def estimate_breathing_cadence(y: np.ndarray, sr: int) -> dict:
    """
    Estimate breathing cadence from inter-speech silence gaps.  [FR-3.1, FR-3.4, TDD §3.5]

    Algorithm:
      1. Use ``librosa.effects.split(y, top_db=30)`` to locate voiced speech
         intervals — contiguous segments whose energy is within 30 dB of the
         signal peak.
      2. Compute the duration (in seconds) of each silence gap between
         consecutive speech intervals.  Only positive-length gaps are counted;
         zero-sample boundaries (adjacent intervals) are skipped.
      3. Derive a regularity score as ``1 / (1 + std(gaps))``.  When all gaps
         are equally spaced the std is 0 and the score is exactly 1.0.  As
         spacing becomes more irregular the score approaches 0.
      4. For signals with fewer than two speech intervals, or where all
         consecutive intervals are adjacent (no measurable silence), the
         function returns the no-gap sentinel values rather than raising.

    Synthetic audio typically shows either no gaps (continuous TTS output) or
    perfectly regular gaps (looped silence padding), both of which yield
    cadence scores that differ from natural human breathing patterns.

    The entire computation is wrapped in a single try/except so that no
    degenerate input (empty array, all-NaN, all-zeros, single sample) can
    propagate an exception to the caller.  [NFR-4.2, AC-5]

    Args:
        y:  Mono float32 audio array at TARGET_SAMPLE_RATE.
        sr: Sample rate in Hz — used to convert sample-index gap lengths to
            seconds.

    Returns:
        Dict with exactly three keys:
          - "breathing_events_detected"  int
              Number of positive-length silence gaps found between speech
              segments.  0 when no measurable gaps exist.
          - "avg_gap_sec"  float | None
              Mean gap duration in seconds, rounded to 3 decimal places.
              None when ``breathing_events_detected == 0``.
          - "cadence_regularity_score"  float | None
              Score in ``[0, 1]`` where 1.0 means perfectly regular spacing
              and values approaching 0 indicate irregular gaps.  None when
              ``breathing_events_detected == 0``.  When exactly one gap is
              detected the score is 1.0 (std of a single value is 0).
    """
    _SENTINEL = {
        "breathing_events_detected": 0,
        "avg_gap_sec": None,
        "cadence_regularity_score": None,
    }

    try:
        intervals = librosa.effects.split(y, top_db=30)
        if len(intervals) < 2:
            return _SENTINEL

        gaps = []
        for i in range(1, len(intervals)):
            gap_samples = intervals[i][0] - intervals[i - 1][1]
            if gap_samples > 0:
                gaps.append(gap_samples / sr)

        if not gaps:
            return _SENTINEL

        gaps = np.array(gaps)
        regularity = float(1.0 / (1.0 + np.std(gaps))) if len(gaps) > 1 else 1.0

        return {
            "breathing_events_detected": int(len(gaps)),
            "avg_gap_sec": round(float(np.mean(gaps)), 3),
            "cadence_regularity_score": round(regularity, 3),
        }
    except Exception:
        return _SENTINEL


def extract_all_features(y: np.ndarray, sr: int) -> dict:
    """
    Run the complete acoustic feature extraction pipeline.  [FR-3.2, TDD §3.5, §12.3]

    This is the single external interface for feature extraction.  Route handlers,
    training scripts, and the CLI inference tool should import and call only this
    function — there is no need to call sub-extractors individually.

    Internally calls all nine extractors in the following order:
      Spectro-temporal (TASK-09):
        1. ``extract_mfcc``             — 20-coefficient MFCC matrix
        2. ``extract_chroma``           — 12-bin chromagram
        3. ``extract_spectral_centroid`` — brightness frequency per frame
        4. ``extract_spectral_contrast`` — 7-band valley/peak contrast
        5. ``extract_zero_crossing_rate`` — noisiness / voicing indicator
        6. ``extract_rms_energy``        — loudness envelope
      Room acoustics (TASK-10 – TASK-12):
        7. ``estimate_rir_proxy``        — HPSS-based room reflection proxy
        8. ``estimate_rt60``             — Schroeder backward-integration RT60
        9. ``estimate_breathing_cadence`` — inter-speech silence gap analysis

    Each time-series feature is summarised by its per-coefficient mean (and std for
    MFCCs) across all frames, so the returned dict is fixed-size regardless of audio
    duration.

    Args:
        y:  Mono float32 audio array at TARGET_SAMPLE_RATE (16 kHz).
        sr: Sample rate in Hz — passed through to every sub-extractor.

    Returns:
        Dict with exactly ten top-level keys:

        Spectro-temporal summaries:
          - "mfcc_mean"                list[float]  Length 20. Per-coefficient mean
                                                    of the MFCC matrix over time.
          - "mfcc_std"                 list[float]  Length 20. Per-coefficient std.
          - "chroma_mean"              list[float]  Length 12. Mean chroma vector.
          - "spectral_centroid_mean"   float        Mean spectral centroid (Hz).
          - "spectral_contrast_mean"   list[float]  Length 7. Mean contrast per band.
          - "zero_crossing_rate_mean"  float        Mean zero-crossing rate.
          - "rms_energy_mean"          float        Mean RMS energy.

        Room-acoustic dicts (see individual estimator docstrings for full schemas):
          - "rir"      dict  Keys: rir_energy_curve, rir_mean_energy, rir_std_energy.
          - "reverb"   dict  Keys: rt60_estimate_sec (float | None).
          - "breathing" dict Keys: breathing_events_detected, avg_gap_sec,
                              cadence_regularity_score.

        Visualization data (sampled/downsampled for API transport):
          - "viz"      dict  Keys described below.
    """
    mfcc = extract_mfcc(y, sr)
    chroma = extract_chroma(y, sr)
    centroid = extract_spectral_centroid(y, sr)
    contrast = extract_spectral_contrast(y, sr)
    zcr = extract_zero_crossing_rate(y)
    rms = extract_rms_energy(y)

    rir = estimate_rir_proxy(y, sr)
    reverb = estimate_rt60(y, sr)
    breathing = estimate_breathing_cadence(y, sr)

    # ---- Visualization data -----------------------------------------------
    # All matrices are downsampled to keep the JSON payload manageable.
    # Max time frames kept: 120 (≈ 3 s of features at hop_length=512, sr=16 kHz)
    _MAX_T = 120

    # MFCC matrix: shape (20, T) → cap at _MAX_T time steps
    mfcc_t = min(mfcc.shape[1], _MAX_T)
    mfcc_matrix = mfcc[:, :mfcc_t].tolist()          # list[list[float]], 20 × mfcc_t

    # Mel spectrogram: shape (64, T)
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, fmax=8000)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_t = min(mel_db.shape[1], _MAX_T)
    mel_matrix = mel_db[:, :mel_t].tolist()           # list[list[float]], 64 × mel_t

    # Frequency spectrum: magnitude FFT averaged over time → 128 frequency bins
    n_fft = 1024
    stft_mag = np.abs(librosa.stft(y, n_fft=n_fft))   # (n_fft/2+1, T)
    freq_mean = stft_mag.mean(axis=1)                  # (513,)
    # Downsample to 128 bins for transport
    step = max(1, len(freq_mean) // 128)
    freq_bins = freq_mean[::step][:128].tolist()
    freq_hz = librosa.fft_frequencies(sr=sr, n_fft=n_fft)[::step][:128].tolist()

    # Schroeder decay curve for RT60 graph: 200-point dB-normalised envelope
    schroeder_curve: list[float] = []
    try:
        from scipy.signal import hilbert as _hilbert
        envelope = np.abs(_hilbert(y)) ** 2
        envelope = np.clip(envelope, 1e-12, None)
        sch = np.cumsum(envelope[::-1])[::-1]
        sch_db = 10 * np.log10(sch / (np.max(sch) + 1e-12) + 1e-12)
        # Downsample to 200 points
        idx = np.linspace(0, len(sch_db) - 1, 200, dtype=int)
        schroeder_curve = np.clip(sch_db[idx], -80, 0).tolist()
    except Exception:
        schroeder_curve = []

    viz = {
        "mfcc_matrix":      mfcc_matrix,       # 20 × up-to-120
        "mel_matrix":       mel_matrix,         # 64 × up-to-120
        "freq_bins":        freq_bins,          # 128 magnitude values
        "freq_hz":          freq_hz,            # 128 Hz labels
        "schroeder_curve":  schroeder_curve,    # 200 dB values
        "rir_curve":        rir["rir_energy_curve"][:200],  # already capped
        "n_mfcc_coeffs":    mfcc.shape[0],
        "n_mel_bands":      64,
        "sample_rate":      sr,
    }

    return {
        "mfcc_mean": mfcc.mean(axis=1).tolist(),
        "mfcc_std": mfcc.std(axis=1).tolist(),
        "chroma_mean": chroma.mean(axis=1).tolist(),
        "spectral_centroid_mean": float(centroid.mean()),
        "spectral_contrast_mean": contrast.mean(axis=1).tolist(),
        "zero_crossing_rate_mean": float(zcr.mean()),
        "rms_energy_mean": float(rms.mean()),
        "rir": rir,
        "reverb": reverb,
        "breathing": breathing,
        "viz": viz,
    }
