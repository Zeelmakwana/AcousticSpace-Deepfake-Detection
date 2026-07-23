"""
AcousticSpace — PDF Report Generator
=====================================
Produces a professional, single-page PDF analysis report using ReportLab.

Layout
------
  Header band   — logo text + report title + analysis ID
  Info table    — filename, prediction verdict (colour-coded), timestamp,
                  system version, model mode
  Confidence    — labelled progress-bar drawn with rectangles
  Acoustics     — room match, breathing consistency, inference time
  Waveform      — text-based suspicious-segment timeline (start → end seconds)
  Footer        — page number + generated-at timestamp

No ML logic is invoked; the function receives a plain dict matching the
AnalysisHistory row shape and returns raw PDF bytes.

Public API
----------
    generate_analysis_pdf(data: dict) -> bytes
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colour palette — mirrors the AcousticSpace dark-theme accent colours
# expressed as ReportLab RGB tuples (0–1 range).
# ---------------------------------------------------------------------------
_NAVY       = colors.HexColor("#0b1020")
_PANEL      = colors.HexColor("#131a2e")
_RAISED     = colors.HexColor("#1a2340")
_LINE       = colors.HexColor("#2a3457")
_TEXT       = colors.HexColor("#e7ebf7")
_MUTED      = colors.HexColor("#93a0c4")
_CYAN       = colors.HexColor("#4fd6e0")
_BLUE       = colors.HexColor("#7c9dfc")
_RED        = colors.HexColor("#ff6b6b")
_GREEN      = colors.HexColor("#4fd68a")
_WHITE      = colors.white
_BLACK      = colors.black

_PAGE_W, _PAGE_H = A4          # 210 × 297 mm
_MARGIN = 18 * mm

# ---------------------------------------------------------------------------
# System version — kept in sync with app.py
# ---------------------------------------------------------------------------
_SYSTEM_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "rpt_title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=_CYAN,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "rpt_subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=_MUTED,
            spaceAfter=0,
        ),
        "section": ParagraphStyle(
            "rpt_section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=_CYAN,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "rpt_body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=_TEXT,
            leading=14,
        ),
        "mono": ParagraphStyle(
            "rpt_mono",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=8,
            textColor=_MUTED,
            leading=12,
        ),
        "verdict_real": ParagraphStyle(
            "rpt_verdict_real",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=_GREEN,
        ),
        "verdict_fake": ParagraphStyle(
            "rpt_verdict_fake",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=_RED,
        ),
        "footer": ParagraphStyle(
            "rpt_footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            textColor=_MUTED,
        ),
    }


def _divider(width: float) -> HRFlowable:
    return HRFlowable(
        width=width,
        thickness=0.5,
        color=_LINE,
        spaceAfter=6,
        spaceBefore=2,
    )


# ---------------------------------------------------------------------------
# Confidence bar — drawn as a ReportLab Drawing embedded in a 1-cell Table
# so it flows naturally in the Platypus story.
# ---------------------------------------------------------------------------

def _confidence_bar_table(
    confidence: float,
    prediction: str,
    avail_width: float,
) -> Table:
    """Return a 1-row table that visually represents the confidence value."""
    from reportlab.graphics.shapes import Drawing, Rect, String

    bar_w = avail_width - 60          # leave room for the % label
    fill_w = bar_w * (confidence / 100.0)
    bar_h = 14

    colour = _GREEN if prediction == "Real" else _RED

    d = Drawing(avail_width, bar_h + 4)

    # Track (background)
    d.add(Rect(0, 2, bar_w, bar_h, fillColor=_RAISED, strokeColor=_LINE, strokeWidth=0.5))

    # Fill
    if fill_w > 0:
        d.add(Rect(0, 2, fill_w, bar_h, fillColor=colour, strokeColor=None, strokeWidth=0))

    # Percentage label
    d.add(
        String(
            bar_w + 6,
            4,
            f"{confidence:.1f}%",
            fontName="Courier-Bold",
            fontSize=9,
            fillColor=colour,
        )
    )

    t = Table([[d]], colWidths=[avail_width])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


# ---------------------------------------------------------------------------
# Info table builder
# ---------------------------------------------------------------------------

def _info_table(rows: list[tuple[str, Any]], avail_width: float) -> Table:
    label_w = 52 * mm
    value_w = avail_width - label_w
    tdata = [[Paragraph(f"<b>{k}</b>", ParagraphStyle(
                "lbl", fontName="Helvetica-Bold", fontSize=8,
                textColor=_MUTED)),
              Paragraph(str(v), ParagraphStyle(
                "val", fontName="Helvetica", fontSize=9,
                textColor=_TEXT))]
             for k, v in rows]
    t = Table(tdata, colWidths=[label_w, value_w])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), _PANEL),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [_PANEL, _RAISED]),
        ("GRID",         (0, 0), (-1, -1), 0.4, _LINE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# ---------------------------------------------------------------------------
# Suspicious-segments timeline
# ---------------------------------------------------------------------------

def _segments_block(segments: list[dict], avail_width: float) -> Table | Paragraph:
    st = _styles()
    if not segments:
        return Paragraph("No suspicious segments detected.", st["body"])

    # Header row + data rows
    header = ["#", "Start (s)", "End (s)", "Duration (s)"]
    rows = [header] + [
        [
            str(i + 1),
            f"{seg.get('start_sec', 0):.3f}",
            f"{seg.get('end_sec', 0):.3f}",
            f"{seg.get('end_sec', 0) - seg.get('start_sec', 0):.3f}",
        ]
        for i, seg in enumerate(segments)
    ]

    col_w = avail_width / 4
    t = Table(rows, colWidths=[col_w * 0.5, col_w * 1.2, col_w * 1.2, col_w * 1.1])
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0), _RAISED),
        ("TEXTCOLOR",    (0, 0), (-1, 0), _CYAN),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        # Data rows
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_PANEL, _RAISED]),
        ("TEXTCOLOR",    (0, 1), (-1, -1), _TEXT),
        ("FONTNAME",     (0, 1), (-1, -1), "Courier"),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        # All cells
        ("GRID",         (0, 0), (-1, -1), 0.4, _LINE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",        (0, 0), (0, -1), "CENTER"),
    ]))
    return t


# ---------------------------------------------------------------------------
# Header canvas callback — dark band at the top
# ---------------------------------------------------------------------------

def _make_header_footer(analysis_id: str, generated_at: str):
    """Return an onFirstPage / onLaterPages callback that draws the dark header band."""

    def _draw(canvas, doc):
        canvas.saveState()

        # ---- Top header band ------------------------------------------------
        band_h = 22 * mm
        canvas.setFillColor(_NAVY)
        canvas.rect(0, _PAGE_H - band_h, _PAGE_W, band_h, fill=1, stroke=0)

        # Logo / brand
        canvas.setFillColor(_CYAN)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(_MARGIN, _PAGE_H - 13 * mm, "🎧  AcousticSpace")

        # Report label
        canvas.setFillColor(_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(_MARGIN, _PAGE_H - 19 * mm, "DEEPFAKE AUDIO ANALYSIS REPORT")

        # Analysis ID (right-aligned)
        canvas.setFont("Courier", 7)
        id_text = f"ID: {analysis_id}"
        canvas.drawRightString(_PAGE_W - _MARGIN, _PAGE_H - 13 * mm, id_text)

        # ---- Bottom footer band ---------------------------------------------
        footer_h = 10 * mm
        canvas.setFillColor(_NAVY)
        canvas.rect(0, 0, _PAGE_W, footer_h, fill=1, stroke=0)

        canvas.setFillColor(_MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            _MARGIN,
            3.5 * mm,
            f"AcousticSpace v{_SYSTEM_VERSION}  ·  Infotact Solutions Internship  ·  Confidential",
        )
        canvas.drawRightString(
            _PAGE_W - _MARGIN,
            3.5 * mm,
            f"Generated: {generated_at}  ·  Page {doc.page}",
        )

        canvas.restoreState()

    return _draw


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_analysis_pdf(data: dict) -> bytes:
    """
    Build a professional PDF report for a single analysis record.

    Parameters
    ----------
    data : dict
        Must contain all fields from _row_to_dict() plus ``inference_mode``.
        Keys: id, filename, prediction, confidence, suspicious_segments,
              room_acoustics_match, breathing_consistency, inference_time_sec,
              inference_mode, timestamp.

    Returns
    -------
    bytes
        Raw PDF bytes suitable for streaming directly to the HTTP client.
    """
    buf = io.BytesIO()
    generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Effective content width
    avail_w = _PAGE_W - 2 * _MARGIN

    # Top/bottom margin accounts for header (22 mm) and footer (10 mm) bands.
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=26 * mm,
        bottomMargin=14 * mm,
        title=f"AcousticSpace Report — {data.get('filename', 'Unknown')}",
        author="AcousticSpace v" + _SYSTEM_VERSION,
        subject="Deepfake Audio Analysis",
    )

    st = _styles()
    story: list = []

    # ---- Report title -------------------------------------------------------
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Analysis Report", st["title"]))
    story.append(Paragraph(
        f"Deepfake Detection via Room Impulse Response (RIR) &amp; Acoustic Fingerprinting",
        st["subtitle"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_divider(avail_w))

    # ---- Verdict (large, colour-coded) -------------------------------------
    prediction: str = data.get("prediction", "Unknown")
    verdict_style = st["verdict_real"] if prediction == "Real" else st["verdict_fake"]
    verdict_icon = "✔  AUTHENTIC" if prediction == "Real" else "⚠  DEEPFAKE DETECTED"
    story.append(Paragraph(f"Verdict: {verdict_icon}", verdict_style))
    story.append(Spacer(1, 3 * mm))

    # ---- Confidence bar -----------------------------------------------------
    story.append(Paragraph("Confidence Score", st["section"]))
    story.append(
        _confidence_bar_table(
            float(data.get("confidence", 0.0)),
            prediction,
            avail_w,
        )
    )
    story.append(Spacer(1, 4 * mm))

    # ---- File & analysis metadata -------------------------------------------
    story.append(Paragraph("File Information", st["section"]))
    ts_raw = data.get("timestamp", "")
    try:
        ts_display = datetime.fromisoformat(ts_raw).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        ts_display = ts_raw

    story.append(_info_table([
        ("Filename",       data.get("filename", "—")),
        ("Prediction",     prediction),
        ("Timestamp",      ts_display),
        ("Analysis ID",    data.get("id", "—")),
        ("System Version", f"AcousticSpace v{_SYSTEM_VERSION}"),
        ("Model Mode",     data.get("inference_mode", "heuristic")),
    ], avail_w))
    story.append(Spacer(1, 4 * mm))

    # ---- Acoustic indicators ------------------------------------------------
    story.append(Paragraph("Acoustic Indicators", st["section"]))
    story.append(_info_table([
        ("Room Acoustics Match",   data.get("room_acoustics_match", "—")),
        ("Breathing Consistency",  data.get("breathing_consistency", "—")),
        ("Inference Time",         f"{float(data.get('inference_time_sec', 0)):.3f} s"),
    ], avail_w))
    story.append(Spacer(1, 4 * mm))

    # ---- Suspicious segments / waveform annotation --------------------------
    story.append(Paragraph("Waveform — Suspicious Segments", st["section"]))
    segments = data.get("suspicious_segments", [])
    if isinstance(segments, str):
        import json as _json
        try:
            segments = _json.loads(segments)
        except Exception:
            segments = []

    story.append(_segments_block(segments, avail_w))
    story.append(Spacer(1, 4 * mm))

    # ---- Interpretation note ------------------------------------------------
    story.append(_divider(avail_w))
    story.append(Paragraph("Interpretation Notes", st["section"]))
    if prediction == "Real":
        note = (
            "The audio exhibits room impulse response characteristics consistent with a genuine "
            "recording environment. Reverberation time (RT60), breathing cadence, and spatial "
            "acoustic fingerprint all align with expected natural patterns. No evidence of "
            "synthetic voice generation was detected."
        )
    else:
        seg_count = len(segments)
        note = (
            f"The audio shows acoustic anomalies inconsistent with a genuine recording "
            f"environment. {seg_count} suspicious segment{'s' if seg_count != 1 else ''} "
            f"{'were' if seg_count != 1 else 'was'} identified where the room impulse response "
            f"diverges from the expected spatial fingerprint. This is indicative of synthetic "
            f"voice generation or post-processing artifacts."
        )
    story.append(Paragraph(note, st["body"]))
    story.append(Spacer(1, 3 * mm))

    # ---- Disclaimer ---------------------------------------------------------
    story.append(_divider(avail_w))
    story.append(Paragraph(
        "<i>This report is generated automatically by AcousticSpace for informational purposes. "
        "Results should be reviewed by a qualified professional before being used in any "
        "legal, forensic, or compliance context. Infotact Solutions accepts no liability for "
        "decisions made solely on the basis of this automated analysis.</i>",
        st["footer"],
    ))

    # ---- Build PDF ----------------------------------------------------------
    cb = _make_header_footer(
        analysis_id=str(data.get("id", "—")),
        generated_at=generated_at,
    )
    doc.build(story, onFirstPage=cb, onLaterPages=cb)

    return buf.getvalue()
