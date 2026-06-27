"""
Converts the crew's final Markdown report (plus the chart PNGs it generated)
into a polished PDF using fpdf2. This is a plain deterministic post-processing
step -- no LLM calls happen here.

Font strategy
-------------
fpdf2's built-in "Helvetica" is a Latin-1 core font and cannot render Unicode
characters (bullet •, curly quotes, em-dash, etc.) that LLMs commonly emit.
We therefore use DejaVuSans (TTF, full Unicode) when the font files are present
and fall back to Helvetica + ASCII-safe text otherwise.

DejaVuSans ships with most Linux distros; on Windows/macOS it can be dropped
into a "fonts/" sub-folder next to this file (or next to main.py) -- the
loader checks both locations.
"""

import glob
import os
import re
import unicodedata
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from typing import List, Optional, Tuple

from fpdf import FPDF

# ── Regex patterns ────────────────────────────────────────────────────────────
IMAGE_PATTERN   = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.*)")
BULLET_PATTERN  = re.compile(r"^[-*]\s+(.*)")
NUMBERED_PATTERN = re.compile(r"^\d+\.\s+(.*)")

# Strip C0/C1 control characters and common invisible Unicode.
_CTRL_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f"
    r"\u200b\u200c\u200d\u2028\u2029\ufeff]"
)

# ── Font discovery ────────────────────────────────────────────────────────────
_DEJAVU_SEARCH = [
    # Relative to this file
    Path(__file__).parent / "fonts",
    Path(__file__).parent.parent / "fonts",
    # Common Linux paths
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/dejavu"),
    # macOS Homebrew
    Path("/opt/homebrew/share/fonts"),
    # Windows common locations
    Path("C:/Windows/Fonts"),
]

def _find_font(name: str) -> Optional[str]:
    for directory in _DEJAVU_SEARCH:
        candidate = directory / name
        if candidate.exists():
            return str(candidate)
    return None

_FONT_REGULAR = _find_font("DejaVuSans.ttf")
_FONT_BOLD    = _find_font("DejaVuSans-Bold.ttf")
_FONT_ITALIC  = _find_font("DejaVuSans-Oblique.ttf") or _find_font("DejaVuSans-Italic.ttf")
_USE_UNICODE  = bool(_FONT_REGULAR and _FONT_BOLD)

FONT_NAME = "DejaVu" if _USE_UNICODE else "Helvetica"


# ── Text sanitisation ─────────────────────────────────────────────────────────

def _strip_ctrl(text: str) -> str:
    """Remove control characters that confuse any PDF renderer."""
    return _CTRL_RE.sub("", text)


def _to_latin1(text: str) -> str:
    """
    When no Unicode font is available, replace non-Latin-1 characters with
    their closest ASCII equivalent (via NFKD decomposition) or '?'.
    """
    text = unicodedata.normalize("NFKD", text)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _safe(text: str, unicode_ok: bool = _USE_UNICODE) -> str:
    text = _strip_ctrl(text)
    if not unicode_ok:
        text = _to_latin1(text)
    return text


def _safe_md(text: str) -> str:
    """
    Sanitise text that will be rendered with markdown=True.

    fpdf2's Markdown parser requires balanced ** and _ pairs.  LLM output
    frequently contains unbalanced markers (stray asterisks in numbers like
    "3 * 4", underscores inside URLs, etc.).  We detect imbalance and escape
    the offending markers with a backslash, which fpdf2 treats as a literal.
    """
    text = _safe(text)

    # ── bold (**) ─────────────────────────────────────────────────────────────
    parts = text.split("**")
    if len(parts) % 2 == 0:          # odd number of markers → unbalanced
        text = text.replace("**", r"\*\*")
    else:
        # Re-join to preserve any already-escaped sequences.
        pass

    # ── italic (*) — only single stars not already part of ** ────────────────
    # Count lone * (not part of **).  Simpler: after handling ** above,
    # any remaining * is a candidate italic marker.
    lone_star_count = text.count("*") - text.count(r"\*")
    if lone_star_count % 2 != 0:
        text = re.sub(r"(?<!\\)\*", r"\*", text)

    # ── underscore italic (_) ─────────────────────────────────────────────────
    under_count = text.count("_")
    if under_count % 2 != 0:
        text = text.replace("_", r"\_")

    return text


# ── PDF class ─────────────────────────────────────────────────────────────────

class ReportPDF(FPDF):
    def __init__(self, topic: str):
        super().__init__()
        self.topic = topic
        self.set_auto_page_break(auto=True, margin=20)
        if _USE_UNICODE:
            self.add_font(FONT_NAME, style="",  fname=_FONT_REGULAR, uni=True)
            self.add_font(FONT_NAME, style="B", fname=_FONT_BOLD,    uni=True)
            if _FONT_ITALIC:
                self.add_font(FONT_NAME, style="I", fname=_FONT_ITALIC, uni=True)

    def footer(self):
        self.set_y(-15)
        self.set_font(FONT_NAME, size=8)
        self.set_text_color(120, 120, 120)
        label = _safe(f"{self.topic}  |  Page {self.page_no()}")
        self.cell(0, 10, label, align="C")
        self.set_text_color(0, 0, 0)

    def pw(self) -> float:
        """Full printable width (left margin to right margin)."""
        return self.w - self.l_margin - self.r_margin

    def iw(self, indent_mm: float) -> float:
        """Printable width when cursor is indent_mm right of the left margin."""
        return self.pw() - indent_mm


# ── Image path resolution ─────────────────────────────────────────────────────

def _resolve_image_path(ref: str, base_dir: str, charts_dir: str) -> Optional[str]:
    candidates = [
        ref,
        os.path.join(base_dir, ref),
        os.path.join(charts_dir, os.path.basename(ref)),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    existing = glob.glob(os.path.join(charts_dir, "*.png"))
    names = [os.path.basename(p) for p in existing]
    matches = get_close_matches(os.path.basename(ref), names, n=1, cutoff=0.4)
    if matches:
        return os.path.join(charts_dir, matches[0])
    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def build_pdf(
    topic: str, markdown_text: str, chart_paths: List[str], output_path: str
) -> str:
    base_dir   = os.path.dirname(output_path) or "."
    charts_dir = os.path.join(base_dir, "charts")

    pdf = ReportPDF(topic)

    # ── Cover page ────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font(FONT_NAME, "B", 22)
    pdf.multi_cell(pdf.pw(), 12, _safe(topic), align="C")
    pdf.ln(4)
    pdf.set_font(FONT_NAME, "", 13)
    pdf.cell(pdf.pw(), 10, "AI-Generated Research Report", align="C")
    pdf.ln(20)
    pdf.set_font(FONT_NAME, "I" if _USE_UNICODE else "", 10)
    pdf.cell(pdf.pw(), 10, datetime.now().strftime("Generated on %B %d, %Y"), align="C")

    # ── Report body ───────────────────────────────────────────────────────────
    pdf.add_page()
    embedded_images: set = set()
    INDENT = 5  # mm

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            pdf.ln(3)
            continue

        # Image
        img_match = IMAGE_PATTERN.match(line.strip())
        if img_match:
            alt_text, ref = img_match.groups()
            resolved = _resolve_image_path(ref.strip(), base_dir, charts_dir)
            if resolved:
                try:
                    pdf.image(resolved, w=min(pdf.pw(), 140))
                    embedded_images.add(os.path.abspath(resolved))
                    pdf.ln(2)
                    if alt_text:
                        pdf.set_font(FONT_NAME, "I" if _USE_UNICODE else "", 9)
                        pdf.set_text_color(100, 100, 100)
                        pdf.multi_cell(pdf.pw(), 6, _safe(alt_text), align="C")
                        pdf.set_text_color(0, 0, 0)
                    pdf.ln(2)
                except Exception:
                    pdf.set_font(FONT_NAME, "", 10)
                    pdf.multi_cell(pdf.pw(), 6, f"[Image could not be embedded: {_safe(ref)}]")
            else:
                pdf.set_font(FONT_NAME, "", 10)
                pdf.set_text_color(150, 0, 0)
                pdf.multi_cell(pdf.pw(), 6, f"[Referenced chart not found: {_safe(ref)}]")
                pdf.set_text_color(0, 0, 0)
            continue

        # Heading
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            hashes, text = heading_match.groups()
            level = len(hashes)
            size = {1: 18, 2: 15, 3: 13}.get(level, 12)
            pdf.ln(4)
            pdf.set_font(FONT_NAME, "B", size)
            pdf.multi_cell(pdf.pw(), 8, _safe(text.strip()))
            pdf.set_font(FONT_NAME, "", 11)
            pdf.ln(1)
            continue

        # Bullet
        bullet_match = BULLET_PATTERN.match(line)
        if bullet_match:
            pdf.set_font(FONT_NAME, "", 11)
            pdf.set_x(pdf.l_margin + INDENT)
            pdf.multi_cell(
                pdf.iw(INDENT), 6,
                _safe_md(f"-  {bullet_match.group(1)}"),
                markdown=True,
            )
            continue

        # Numbered list
        if NUMBERED_PATTERN.match(line):
            pdf.set_font(FONT_NAME, "", 11)
            pdf.set_x(pdf.l_margin + INDENT)
            pdf.multi_cell(pdf.iw(INDENT), 6, _safe_md(line), markdown=True)
            continue

        # Plain paragraph — only use markdown=True when bold/italic markers
        # are present so we never risk the parser on purely plain text.
        pdf.set_font(FONT_NAME, "", 11)
        if "**" in line or "__" in line:
            pdf.multi_cell(pdf.pw(), 6, _safe_md(line), markdown=True)
        else:
            pdf.multi_cell(pdf.pw(), 6, _safe(line))

    # ── Safety net: append unreferenced charts ────────────────────────────────
    leftover = [p for p in chart_paths if os.path.abspath(p) not in embedded_images]
    if leftover:
        pdf.add_page()
        pdf.set_font(FONT_NAME, "B", 14)
        pdf.cell(pdf.pw(), 10, "Additional Charts")
        pdf.ln(12)
        for path in leftover:
            try:
                pdf.image(path, w=min(pdf.pw(), 140))
                pdf.ln(6)
            except Exception:
                continue

    pdf.output(output_path)
    return output_path