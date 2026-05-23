"""HTML email templates for GroundControl notifications"""

from typing import Optional

_BASE_STYLE = """
  body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #222; }
  h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 8px; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background: #f5f5f5; font-weight: bold; }
  .total-row td { font-weight: bold; font-size: 1.05em; background: #f9f9f9; }
  .btn { display: inline-block; background: #007bff; color: #fff; padding: 10px 22px;
         text-decoration: none; border-radius: 4px; margin: 12px 0; }
  .footer { color: #888; font-size: 0.85em; margin-top: 28px; border-top: 1px solid #eee; padding-top: 12px; }
"""

_PAYMENT_LABELS = {
    "bar": "Barzahlung",
    "karte": "Kartenzahlung",
    "wero": "Wero",
}


def laufzettel_receipt_html(
    lz, materials: list, view_url: Optional[str] = None, request=None
) -> str:
    """HTML receipt email for a paid or newly created Laufzettel."""
    date_str = lz.date.strftime("%d.%m.%Y") if lz.date else "—"
    method_label = _PAYMENT_LABELS.get(
        lz.payment_method or "", lz.payment_method or "—"
    )
    owner = lz.owner_name or "Gast"

    # Use provided view URL or construct from request (using Pi's IP)
    if not view_url:
        if request:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
        else:
            # Fallback to Pi's internal IP when no request context
            base_url = "http://192.168.3.228:8443"
        view_url = f"{base_url}/laufzettel/view/{lz.id}"

    rows_html = ""
    total = 0.0
    for mat in materials:
        price = mat.calculated_price or 0.0
        total += price
        if mat.menge is not None and mat.unit:
            qty = f"{mat.menge} {mat.unit}"
        elif mat.menge is not None:
            qty = str(mat.menge)
        else:
            qty = "—"
        rows_html += (
            f"<tr>"
            f"<td>{mat.name or '—'}</td>"
            f"<td>{qty}</td>"
            f"<td style='text-align:right'>{price:.2f}&nbsp;€</td>"
            f"</tr>"
        )

    if not rows_html:
        rows_html = (
            "<tr><td colspan='3' style='color:#888'>Keine Materialien erfasst</td></tr>"
        )

    # Adjust content based on payment status
    if lz.payment_method:
        subject_header = "Quittung"
        intro_text = "Hier ist deine Quittung für deinen Besuch in der H3cke."
        cta_text = f"Laufzettel #{lz.id} ansehen"
    else:
        subject_header = "Laufzettel erstellt"
        intro_text = f"Hallo {owner}, danke für deinen Besuch in der H3cke! Dein Laufzettel wurde erfolgreich erstellt."
        cta_text = f"Laufzettel #{lz.id} verwalten"

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Laufzettel #{lz.id} – H3cke</title>
<style>{_BASE_STYLE}</style></head>
<body>
<h1>{subject_header} – Laufzettel #{lz.id}</h1>
<p>
  {intro_text}<br>
  <strong>Datum:</strong> {date_str}<br>
  {method_label != "—" and f"<strong>Zahlungsart:</strong> {method_label}" or ""}
</p>
<table>
  <thead>
    <tr><th>Material</th><th>Menge</th><th style="text-align:right">Preis</th></tr>
  </thead>
  <tbody>
    {rows_html}
    <tr class="total-row">
      <td colspan="2">Gesamt</td>
      <td style="text-align:right'>{total:.2f}&nbsp;€</td>
    </tr>
  </tbody>
</table>

<p style="margin: 20px 0;">
  <a class="btn" href="{view_url}" style="display: block; text-align: center;">
    {cta_text}
  </a>
</p>

<p style="font-size: 0.85em; color: #666;">
  Direktlink: <a href="{view_url}" style="color: #666;">{view_url}</a>
</p>

<p class="footer">H3cke Makerspace &middot; Vielen Dank für deinen Besuch!</p>
</body>
</html>"""


def easyverein_signup_html(name: str, signup_url: str) -> str:
    """HTML email inviting a guest to sign up as an easyVerein member."""
    if signup_url:
        cta_html = (
            f'<p><a class="btn" href="{signup_url}">Jetzt Mitglied werden</a></p>'
            f'<p style="font-size:0.9em">Direktlink: <a href="{signup_url}">{signup_url}</a></p>'
        )
    else:
        cta_html = (
            "<p>Sprich uns vor Ort an oder schreib uns eine E-Mail,"
            " um die Mitgliedschaft zu beantragen.</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Willkommen im H3cke!</title>
<style>{_BASE_STYLE}</style></head>
<body>
<h1>Willkommen im H3cke Makerspace!</h1>
<p>Hallo {name},</p>
<p>danke für deinen Besuch in der H3cke! Wir freuen uns, dass du unsere Maschinen und
Materialien genutzt hast.</p>
<p>Als <strong>Mitglied</strong> profitierst du von:</p>
<ul>
  <li>Dein digitaler Laufzettel mit deiner persönlichen RFID-Karte</li>
  <li>Nutzung aller Maschinen und Werkzeuge</li>
  <li>Einer aktiven Community von Makern</li>
</ul>
<p>Die Mitgliedschaft wird über <strong>easyVerein</strong> verwaltet:</p>
{cta_html}
<p class="footer">
  H3cke Makerspace &middot; Diese E-Mail wurde automatisch nach deinem Besuch verschickt.
</p>
</body>
</html>"""
