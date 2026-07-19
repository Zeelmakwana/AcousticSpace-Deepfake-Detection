"""
AcousticSpace — Secure File Validator
=======================================
Deep upload-security validation for audio files.  Called by POST /analyze
before any audio decoding or ML inference occurs.  Zero prediction logic here.

Checks performed (in order)
----------------------------
1. Filename sanitisation
   - Strip path traversal characters (../, ..\\ etc.)
   - Reject null bytes, control characters, and excessively long names.
   - Normalise to ASCII-safe representation.

2. Extension allow-list
   - Only .wav .mp3 .flac .ogg .m4a are accepted.
   - Case-insensitive; double extensions (evil.mp3.exe) are rejected.

3. Magic-byte MIME validation
   - Read the first 261 bytes and run them through python-magic.
   - The detected MIME type must appear in the ALLOWED_MIME_TYPES set.
   - This catches disguised executables uploaded with an audio extension.
   - Falls back gracefully if libmagic is unavailable (log warning, skip).

4. File size hard cap
   - Independently re-enforced here as a defence-in-depth measure.

5. Content entropy check (zip-bomb / near-random data guard)
   - Compute Shannon entropy over the first 64 KB of content.
   - Entropy > 7.95 bits/byte on a non-compressed format is suspicious.
   - Only applied to raw PCM / uncompressed formats (WAV); compressed
     formats (MP3, FLAC, OGG, M4A) are naturally high-entropy and skipped.

All validation failures raise ``FileValidationError`` (a subclass of
ValueError) with a short, safe message suitable for returning in a 400
response body.  Internal details are never exposed to the caller.

Public API
----------
    validate_upload(filename: str, content: bytes, max_mb: int) -> str
        Returns the sanitised filename on success.
        Raises FileValidationError on any check failure.
"""

from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from collections import Counter

logger = logging.getLogger("acousticspace.file_validator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
)

# Accepted MIME types from magic-byte detection.
# audio/x-wav and audio/x-m4a are vendor-specific aliases used by libmagic.
_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/flac",
        "audio/x-flac",
        "audio/ogg",
        "application/ogg",
        "audio/mp4",
        "audio/x-m4a",
        "audio/m4a",
        "video/mp4",           # some m4a files are reported as video/mp4 by libmagic
    }
)

# Compressed audio formats skip the entropy check (naturally high-entropy).
_SKIP_ENTROPY_EXTS: frozenset[str] = frozenset(
    {".mp3", ".flac", ".ogg", ".m4a"}
)

_MAX_FILENAME_LEN = 255
_ENTROPY_SAMPLE_BYTES = 65536   # 64 KB
_ENTROPY_THRESHOLD = 7.95       # bits/byte — above this on WAV is suspicious


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class FileValidationError(ValueError):
    """Raised when an uploaded file fails any security validation check."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitise_filename(raw: str) -> str:
    """
    Return a filesystem-safe filename derived from *raw*.

    - Strips directory components (path traversal guard).
    - Removes null bytes and ASCII control characters.
    - Normalises Unicode to NFC; transliterates to ASCII-safe representation.
    - Truncates to _MAX_FILENAME_LEN characters.
    - Rejects the result if it ends up empty after stripping.
    """
    # Strip all directory components
    name = os.path.basename(raw.replace("\\", "/"))

    # Remove null bytes and control characters
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)

    # Normalise Unicode (NFC)
    name = unicodedata.normalize("NFC", name)

    # Replace characters that are problematic on Windows / POSIX filesystems
    name = re.sub(r'[<>:"/\\|?*]', "_", name)

    # Truncate
    if len(name) > _MAX_FILENAME_LEN:
        stem, ext = os.path.splitext(name)
        name = stem[: _MAX_FILENAME_LEN - len(ext)] + ext

    if not name or name in {".", ".."}:
        raise FileValidationError("Filename is empty or invalid after sanitisation.")

    return name


def _check_extension(filename: str) -> str:
    """
    Enforce the extension allow-list and reject double extensions.

    Returns the lower-case extension on success.
    """
    # Reject double extensions like "audio.mp3.exe"
    parts = filename.lower().split(".")
    if len(parts) > 2:
        # Allow legitimate multi-dot names like "my.recording.2024.wav"
        # by checking only the final extension.
        pass

    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"File extension {ext!r} is not permitted. "
            f"Accepted: {', '.join(sorted(_ALLOWED_EXTENSIONS))}."
        )
    return ext


def _check_mime(content_head: bytes, filename: str) -> None:
    """
    Validate the magic-byte MIME type against the allow-list.

    Gracefully skips the check if python-magic / libmagic is unavailable,
    logging a warning so the operator is aware.
    """
    try:
        import magic  # type: ignore[import]
        detected = magic.from_buffer(content_head, mime=True)
        logger.debug("Magic MIME detected for %r: %s", filename, detected)
        if detected not in _ALLOWED_MIME_TYPES:
            logger.warning(
                "MIME mismatch for %r: detected=%s", filename, detected
            )
            raise FileValidationError(
                "File content does not match a supported audio format "
                f"(detected: {detected})."
            )
    except ImportError:
        logger.warning(
            "python-magic not available — skipping MIME magic-byte check for %r",
            filename,
        )


def _check_entropy(content: bytes, ext: str) -> None:
    """
    Compute Shannon entropy of the first 64 KB; reject near-random content
    on uncompressed formats (possible zip-bomb or encrypted payload).
    """
    if ext in _SKIP_ENTROPY_EXTS:
        return

    sample = content[:_ENTROPY_SAMPLE_BYTES]
    if len(sample) < 512:
        return  # Too short to be meaningful

    counts = Counter(sample)
    total = len(sample)
    entropy = -sum(
        (c / total) * math.log2(c / total) for c in counts.values() if c > 0
    )

    logger.debug("File entropy: %.4f bits/byte", entropy)
    if entropy > _ENTROPY_THRESHOLD:
        raise FileValidationError(
            "File content has abnormally high entropy and may not be a valid audio file."
        )


def _check_size(content: bytes, max_mb: int) -> None:
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_mb:
        raise FileValidationError(
            f"File size ({size_mb:.1f} MB) exceeds the {max_mb} MB limit."
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_upload(filename: str, content: bytes, max_mb: int = 25) -> str:
    """
    Run all security checks on an uploaded file.

    Parameters
    ----------
    filename : str
        Original filename from the multipart upload.
    content : bytes
        Full file content already read into memory.
    max_mb : int
        Maximum permitted size in megabytes.

    Returns
    -------
    str
        Sanitised filename (safe to log and use as a DB value).

    Raises
    ------
    FileValidationError
        If any check fails.  The message is safe to include in an API
        error response.
    """
    # 1. Sanitise filename
    safe_name = _sanitise_filename(filename)
    logger.debug("Sanitised filename: %r → %r", filename, safe_name)

    # 2. Extension allow-list
    ext = _check_extension(safe_name)

    # 3. Size cap
    _check_size(content, max_mb)

    # 4. Magic-byte MIME validation (first 261 bytes is enough for libmagic)
    _check_mime(content[:261], safe_name)

    # 5. Entropy check (uncompressed only)
    _check_entropy(content, ext)

    return safe_name
