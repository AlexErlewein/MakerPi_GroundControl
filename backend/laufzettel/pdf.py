"""PDF generation for Laufzettel receipts using fpdf2."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from fpdf import FPDF, XPos, YPos

if TYPE_CHECKING:
    from .models import Laufzettel, LaufzettelMaterial

# Unicode TrueType font (DejaVuSans) so characters like €, ², ³, ×, –, " "
# render natively instead of being replaced by "?" as they would be with the
# Latin-1-only Helvetica core font.
_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_FAMILY = "DejaVu"
if not (_FONT_DIR / "DejaVuSans.ttf").exists() or not (
    _FONT_DIR / "DejaVuSans-Bold.ttf"
).exists():
    # TTFs missing (e.g. incomplete checkout): fall back to the Latin-1-only
    # built-in Helvetica family. _safe() still guards against unencodable
    # characters in that case so PDF generation never crashes.
    _FONT_FAMILY = "Helvetica"


def _register_fonts(pdf: FPDF) -> None:
    """Register the Unicode font family once per PDF document."""
    if _FONT_FAMILY == "DejaVu":
        pdf.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        pdf.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))


# Corporate Identity Colors (from style.css)
_CI_ACCENT = (208, 68, 23)  # #d04417 - orange/red
_CI_HEADER_BG = (60, 65, 75)  # dark grey for table headers
_CI_ROW_ALT_BG = (242, 242, 245)  # very light grey for alternating data rows
_CI_TEXT_PRIMARY = (30, 30, 30)  # near-black text for PDF body
_CI_TEXT_SECONDARY = (100, 100, 105)  # medium grey for labels
_CI_TEXT_ON_DARK = (255, 255, 255)  # white text on dark header fills
_CI_BORDER = (180, 180, 185)  # light grey border
_CI_SUCCESS = (53, 119, 48)  # #357730 - success green
_CI_WARNING = (210, 153, 34)  # #d29922 - warning yellow

_PAYMENT_LABELS = {
    "bar": "Bar",
    "karte": "Karte / SumUp",
    "wero": "Wero",
}

_MONTH_DE = [
    "",
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%d.%m.%Y %H:%M")


def _fmt_date(d) -> str:
    if d is None:
        return "-"
    if hasattr(d, "strftime"):
        return d.strftime("%d.%m.%Y")
    return str(d)


def _safe(text: str | None) -> str:
    """Return a string safe to render for the active PDF font.

    With the Unicode DejaVu font the text is returned as-is (€, ², ³, ×, … all
    render natively). When the TTFs are unavailable and the document fell back
    to the Latin-1-only Helvetica core font, unencodable characters are replaced
    instead of crashing the PDF generation.
    """
    if text is None:
        return "-"
    if _FONT_FAMILY == "DejaVu":
        return str(text)
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _fmt_qty(value) -> str:
    """Format a quantity with up to 2 decimals, stripping trailing zeros.

    Avoids floating-point noise such as 33.480000000000004 (accumulated device
    session minutes) and redundant trailing zeros (36.0 -> 36, 568.08 stays).
    """
    if value is None:
        return "-"
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _wrapped_lines(pdf: FPDF, text: str, col_width: float) -> int:
    """Estimate how many lines *text* occupies when word-wrapped in *col_width*.

    Used to size material rows so long content wraps onto extra lines instead of
    overflowing into the next column. Biased to over-estimate (safe direction:
    a little extra whitespace beats clipping).
    """
    text = str(text)
    if not text:
        return 1
    pad = 1.0  # mm breathing room inside the cell
    total = 0
    for segment in text.split("\n"):
        if not segment.strip():
            total += 1
            continue
        words = segment.split(" ")
        lines = 1
        cur = ""
        for word in words:
            cand = f"{cur} {word}".strip()
            if pdf.get_string_width(cand) <= col_width - pad:
                cur = cand
            else:
                lines += 1
                cur = word
        total += lines
    return max(total, 1)


def generate_pdf(
    lz: "Laufzettel",
    materials: list["LaufzettelMaterial"],
) -> bytes:
    """Generate a PDF receipt for *lz* and return the raw bytes."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=15)
    _register_fonts(pdf)
    pdf.add_page()

    # ── Header with Logo ─────────────────────────────────────────────────────
    # Add logo if file exists
    logo_path = Path("graphics/H3ckeLogo.svg")
    logo_y = 12
    if logo_path.exists():
        try:
            # fpdf2 supports SVG via image method
            pdf.image(str(logo_path), x=12, y=logo_y, w=25)
            logo_y += 30  # Move title down to avoid overlap with logo
        except Exception:
            pass  # Logo not available or not supported, skip gracefully

    # Title (positioned below logo)
    pdf.set_y(logo_y)
    pdf.set_font(_FONT_FAMILY, style="B", size=18)
    pdf.set_text_color(*_CI_ACCENT)
    pdf.cell(0, 10, f"Laufzettel #{lz.id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font(_FONT_FAMILY, size=9)
    pdf.set_text_color(*_CI_TEXT_SECONDARY)
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    pdf.cell(0, 5, f"Erstellt am {now_str} UTC", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # divider with corporate color
    pdf.set_draw_color(*_CI_ACCENT)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.set_line_width(0.5)
    pdf.ln(4)

    # ── Info table ──────────────────────────────────────────────────────────
    pdf.set_text_color(*_CI_TEXT_PRIMARY)
    label_w = 38

    def info_row(label: str, value: str) -> None:
        pdf.set_font(_FONT_FAMILY, style="", size=9)
        pdf.set_text_color(*_CI_TEXT_SECONDARY)
        pdf.cell(label_w, 6, _safe(label))
        pdf.set_text_color(*_CI_TEXT_PRIMARY)
        pdf.set_font(_FONT_FAMILY, style="B", size=9)
        pdf.cell(0, 6, _safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    info_row("Name:", lz.owner_name or "-")
    if lz.guest_id and getattr(lz, "guest_address", None):
        for line in (lz.guest_address or "").splitlines():
            info_row("Adresse:", line.strip())
    info_row("Member-ID:", lz.member_id or "-")
    info_row("Datum:", _fmt_date(lz.date))
    info_row("Start:", _fmt_dt(lz.start) if lz.start else "-")
    info_row("Tag UID:", lz.uid or "-")
    pdf.ln(4)

    # ── Material table ───────────────────────────────────────────────────────
    pdf.set_font(_FONT_FAMILY, style="B", size=10)
    pdf.set_text_color(*_CI_ACCENT)
    pdf.cell(0, 7, "Material", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # column widths (total usable = 186mm)
    col_w = [8, 74, 34, 20, 18, 32]
    headers = ["#", "Name", "Menge / Masse", "Einheit", "MwSt.", "Preis (EUR)"]

    # Header row with corporate colors
    pdf.set_fill_color(*_CI_HEADER_BG)
    pdf.set_font(_FONT_FAMILY, style="B", size=8)
    pdf.set_text_color(*_CI_TEXT_ON_DARK)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 6, h, border="B", fill=True)
    pdf.ln()

    # group materials by catalog category (variante_id groups together)
    # simple approach: just list all rows, sorted by variante_id then name
    sorted_mats = sorted(
        materials,
        key=lambda m: (m.variante_id or 999999, m.name or ""),
    )

    tax_groups: dict[float, float] = {}
    grand_total = 0.0
    row_index = 0

    pdf.set_font(_FONT_FAMILY, size=8)
    for m in sorted_mats:
        row_index += 1
        rate = m.tax_rate if m.tax_rate is not None else 19.0
        price = m.calculated_price or 0.0
        if m.calculated_price is not None:
            tax_groups[rate] = tax_groups.get(rate, 0.0) + price
            grand_total += price

        # menge / dimensions text
        if (
            m.laenge_cm is not None
            and m.breite_cm is not None
            and m.hoehe_cm is not None
        ):
            vol = m.laenge_cm * m.breite_cm * m.hoehe_cm
            menge_str = (
                f"{_fmt_qty(m.laenge_cm)}x{_fmt_qty(m.breite_cm)}"
                f"x{_fmt_qty(m.hoehe_cm)} ({vol:.0f}cm³)"
            )
        elif m.menge is not None:
            menge_str = _fmt_qty(m.menge)
        else:
            menge_str = "-"

        price_str = f"{price:.2f}" if m.calculated_price is not None else "-"

        # Alternating row colors
        if row_index % 2 == 0:
            pdf.set_fill_color(*_CI_ROW_ALT_BG)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(*_CI_TEXT_PRIMARY)

        # Size the row to fit the tallest wrapped cell so long names / dimensions
        # wrap onto extra lines instead of overflowing into the next column.
        cell_texts = [
            str(row_index),
            _safe(m.name),
            _safe(menge_str),
            _safe(m.unit or "-"),
            f"{rate:.0f} %",
            price_str,
        ]
        line_height = 4.6
        lines_needed = max(
            _wrapped_lines(pdf, t, w) for t, w in zip(cell_texts, col_w)
        )
        row_h = max(6.0, lines_needed * line_height)

        row_top = pdf.get_y()
        for w, txt, align in zip(
            col_w, cell_texts, ["", "", "", "", "", "R"]
        ):
            # Vertical-center short cells in taller rows for a tidy look.
            this_lines = _wrapped_lines(pdf, txt, w)
            y_offset = max(0.0, (row_h - this_lines * line_height) / 2)
            pdf.set_xy(pdf.get_x(), row_top + y_offset)
            pdf.multi_cell(
                w,
                line_height,
                txt,
                border=0,
                align=align or "L",
                fill=True,
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )
        pdf.set_xy(12, row_top + row_h)
        pdf.ln(0)

    if not sorted_mats:
        pdf.set_text_color(*_CI_TEXT_SECONDARY)
        pdf.cell(0, 6, "Keine Materialeinträge.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)

    # ── Tax summary ──────────────────────────────────────────────────────────
    if tax_groups:
        # Title on the left, Gesamtbetrag on the right of the same line.
        pdf.set_font(_FONT_FAMILY, style="B", size=10)
        pdf.set_text_color(*_CI_ACCENT)
        pdf.cell(90, 7, "Steuerübersicht")
        pdf.set_font(_FONT_FAMILY, style="B", size=11)
        pdf.cell(0, 7, f"Gesamtbetrag: {grand_total:.2f} EUR", align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        tw = [22, 35, 35, 35]
        pdf.set_fill_color(*_CI_HEADER_BG)
        pdf.set_font(_FONT_FAMILY, style="B", size=8)
        pdf.set_text_color(*_CI_TEXT_ON_DARK)
        for w, h in zip(
            tw, ["MwSt.-Satz", "Netto (EUR)", "MwSt. (EUR)", "Brutto (EUR)"]
        ):
            pdf.cell(w, 6, h, border="B", fill=True)
        pdf.ln()

        total_netto = 0.0
        total_tax = 0.0
        total_brutto = 0.0

        pdf.set_font(_FONT_FAMILY, size=8)
        pdf.set_text_color(*_CI_TEXT_PRIMARY)
        for rate in sorted(tax_groups.keys(), reverse=True):
            brutto = tax_groups[rate]
            netto = brutto / (1 + rate / 100)
            tax = brutto - netto
            total_netto += netto
            total_tax += tax
            total_brutto += brutto
            pdf.cell(tw[0], 6, f"{rate:.0f} %")
            pdf.cell(tw[1], 6, f"{netto:.2f}", align="R")
            pdf.cell(tw[2], 6, f"{tax:.2f}", align="R")
            pdf.cell(tw[3], 6, f"{brutto:.2f}", align="R")
            pdf.ln()

        # Grey Gesamt bar at the bottom
        pdf.set_font(_FONT_FAMILY, style="B", size=8)
        pdf.set_draw_color(*_CI_BORDER)
        pdf.set_text_color(*_CI_TEXT_PRIMARY)
        if len(tax_groups) > 1:
            pdf.cell(tw[0], 6, "Gesamt", border="T")
            pdf.cell(tw[1], 6, f"{total_netto:.2f}", border="T", align="R")
            pdf.cell(tw[2], 6, f"{total_tax:.2f}", border="T", align="R")
            pdf.cell(tw[3], 6, f"{total_brutto:.2f}", border="T", align="R")
            pdf.ln()
        else:
            pdf.ln(2)

    # ── Payment section ──────────────────────────────────────────────────────
    if lz.payment_method:
        # Payment box with corporate colors
        pdf.set_fill_color(*_CI_SUCCESS)
        pdf.set_draw_color(*_CI_BORDER)
        pdf.set_font(_FONT_FAMILY, style="B", size=10)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 7, "Zahlung bestätigt", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        method_label = _PAYMENT_LABELS.get(lz.payment_method, lz.payment_method)
        pdf.set_font(_FONT_FAMILY, size=9)
        pdf.set_text_color(*_CI_TEXT_PRIMARY)
        info_row("Methode:", method_label)
        info_row("Bezahlt am:", _fmt_dt(lz.paid_at) if lz.paid_at else "-")
        if lz.payment_transaction_id:
            info_row("Transaktions-ID:", lz.payment_transaction_id)
        if lz.payment_notes:
            info_row("Notiz:", lz.payment_notes)

    return bytes(pdf.output())


def pdf_filename(lz: "Laufzettel") -> str:
    """Return a filesystem-safe filename for the PDF."""
    name = re.sub(r"[^\w\-]", "_", lz.owner_name or "unbekannt")
    date_str = _fmt_date(lz.date).replace(".", "-")
    return f"Laufzettel_{date_str}_{name}_{lz.id}.pdf"


def drive_folder_names(lz: "Laufzettel") -> tuple[str, str]:
    """Return (year_str, month_name_de) for the Google Drive folder path."""
    d = lz.date
    if d is None:
        now = datetime.now(timezone.utc)
        return str(now.year), _MONTH_DE[now.month]
    return str(d.year), _MONTH_DE[d.month]
