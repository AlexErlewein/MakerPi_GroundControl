"""PDF generation for Laufzettel receipts using fpdf2."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fpdf import FPDF, XPos, YPos

if TYPE_CHECKING:
    from .models import Laufzettel, LaufzettelMaterial


_PAYMENT_LABELS = {
    "bar": "Bar",
    "karte": "Karte / SumUp",
    "wero": "Wero",
}

_MONTH_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
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
    """Strip characters fpdf can't encode and return a plain ASCII-safe string."""
    if text is None:
        return "-"
    # replace common German umlauts
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    # strip any remaining non-latin1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(
    lz: "Laufzettel",
    materials: list["LaufzettelMaterial"],
) -> bytes:
    """Generate a PDF receipt for *lz* and return the raw bytes."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Header ──────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", style="B", size=18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, f"Laufzettel #{lz.id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(120, 120, 120)
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    pdf.cell(0, 5, f"Erstellt am {now_str} UTC", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # divider
    pdf.set_draw_color(200, 200, 200)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(4)

    # ── Info table ──────────────────────────────────────────────────────────
    pdf.set_text_color(30, 30, 30)
    label_w = 38

    def info_row(label: str, value: str) -> None:
        pdf.set_font("Helvetica", style="", size=9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(label_w, 6, _safe(label))
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.cell(0, 6, _safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    info_row("Name:", lz.owner_name or "-")
    info_row("Member-ID:", lz.member_id or "-")
    info_row("Datum:", _fmt_date(lz.date))
    info_row("Start:", _fmt_dt(lz.start) if lz.start else "-")
    info_row("Tag UID:", lz.uid or "-")
    pdf.ln(4)

    # ── Material table ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "Material", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # column widths (total usable = 186mm)
    col_w = [8, 74, 34, 20, 18, 32]
    headers = ["#", "Name", "Menge / Masse", "Einheit", "MwSt.", "Preis (EUR)"]

    pdf.set_fill_color(243, 244, 246)
    pdf.set_font("Helvetica", style="B", size=8)
    pdf.set_text_color(60, 60, 60)
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

    pdf.set_font("Helvetica", size=8)
    for m in sorted_mats:
        row_index += 1
        rate = m.tax_rate if m.tax_rate is not None else 19.0
        price = m.calculated_price or 0.0
        if m.calculated_price is not None:
            tax_groups[rate] = tax_groups.get(rate, 0.0) + price
            grand_total += price

        # menge / dimensions text
        if m.laenge_cm is not None and m.breite_cm is not None and m.hoehe_cm is not None:
            vol = m.laenge_cm * m.breite_cm * m.hoehe_cm
            menge_str = f"{m.laenge_cm}x{m.breite_cm}x{m.hoehe_cm} ({vol:.1f}cm3)"
        elif m.menge is not None:
            menge_str = str(m.menge)
        else:
            menge_str = "-"

        price_str = f"{price:.2f}" if m.calculated_price is not None else "-"

        row_bg = 255 if row_index % 2 == 0 else 249
        pdf.set_fill_color(row_bg, row_bg, row_bg)
        pdf.set_text_color(30, 30, 30)

        pdf.cell(col_w[0], 6, str(row_index), fill=True)
        pdf.cell(col_w[1], 6, _safe(m.name), fill=True)
        pdf.cell(col_w[2], 6, _safe(menge_str), fill=True)
        pdf.cell(col_w[3], 6, _safe(m.unit or "-"), fill=True)
        pdf.cell(col_w[4], 6, f"{rate:.0f} %", fill=True)
        pdf.cell(col_w[5], 6, price_str, fill=True, align="R")
        pdf.ln()

    if not sorted_mats:
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Keine Materialeintraege.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)

    # ── Tax summary ──────────────────────────────────────────────────────────
    if tax_groups:
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 7, "Steueruebersicht", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        tw = [22, 35, 35, 35]
        pdf.set_fill_color(243, 244, 246)
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.set_text_color(60, 60, 60)
        for w, h in zip(tw, ["MwSt.-Satz", "Netto (EUR)", "MwSt. (EUR)", "Brutto (EUR)"]):
            pdf.cell(w, 6, h, border="B", fill=True)
        pdf.ln()

        total_netto = 0.0
        total_tax = 0.0
        total_brutto = 0.0

        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(30, 30, 30)
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

        if len(tax_groups) > 1:
            pdf.set_font("Helvetica", style="B", size=8)
            pdf.set_draw_color(155, 160, 170)
            pdf.cell(tw[0], 6, "Gesamt", border="T")
            pdf.cell(tw[1], 6, f"{total_netto:.2f}", border="T", align="R")
            pdf.cell(tw[2], 6, f"{total_tax:.2f}", border="T", align="R")
            pdf.cell(tw[3], 6, f"{total_brutto:.2f}", border="T", align="R")
            pdf.ln()

        pdf.ln(3)
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.set_text_color(5, 122, 85)
        pdf.cell(0, 8, f"Gesamtbetrag (Brutto): {grand_total:.2f} EUR",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        pdf.ln(2)

    # ── Payment section ──────────────────────────────────────────────────────
    if lz.payment_method:
        pdf.set_fill_color(240, 253, 244)
        pdf.set_draw_color(134, 239, 172)
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(22, 101, 52)
        pdf.cell(0, 7, "Zahlung bestaetigt", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        method_label = _PAYMENT_LABELS.get(lz.payment_method, lz.payment_method)
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(30, 30, 30)
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
