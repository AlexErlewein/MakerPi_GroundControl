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
   .logo { max-width: 280px; margin: 0 auto 20px; display: block; }
"""

_H3CKE_LOGO_B64 = (
    "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"
    "AElFTkSuQmCC"
)

_H3CKE_LOGO = (
    '<div class="logo">'
    f'<img src="data:image/png;base64,{_H3CKE_LOGO_B64}"'
    ' alt="H3cke Makerspace Rosenheim" style="max-width:280px;height:auto;display:block;margin:0 auto">'
    "</div>"
)

_PAYMENT_LABELS = {
    "bar": "Barzahlung",
    "karte": "Kartenzahlung",
    "wero": "Wero",
    "gutschein": "Gutschein",
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

    if not view_url:
        if request:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
        else:
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
{_H3CKE_LOGO}
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
      <td style="text-align:right">{total:.2f}&nbsp;€</td>
    </tr>
  </tbody>
</table>

 <p style="margin: 20px 0;">
   <a class="btn" href="{view_url}" style="display: block; text-align: center;">
     {cta_text}
   </a>
 </p>

 <p class="footer">H3cke Makerspace &middot; Vielen Dank für deinen Besuch!</p>
</body>
</html>"""


def easyverein_key_expiry_html(days_left: int, org_id: str = "") -> str:
    renew_url = (
        f"https://easyverein.com/app/{org_id}/setting/api-key"
        if org_id
        else "https://easyverein.com"
    )
    if days_left <= 0:
        status_text = "ist heute abgelaufen"
        color = "#dc3545"
    elif days_left == 1:
        status_text = "läuft morgen ab"
        color = "#dc3545"
    elif days_left <= 3:
        status_text = f"läuft in {days_left} Tagen ab"
        color = "#dc3545"
    else:
        status_text = f"läuft in {days_left} Tagen ab"
        color = "#fd7e14"

    return f"""<!DOCTYPE html>
<html><head><style>{_BASE_STYLE}</style></head>
<body>
{_H3CKE_LOGO}
<h1>easyVerein API-Schlüssel {status_text}</h1>
<p>Der easyVerein API-Schlüssel für GroundControl <strong style="color:{color}">{status_text}</strong>.</p>
<p>Bitte erneuere den API-Schlüssel, um die Mitgliedersynchronisation aufrechtzuerhalten.</p>
<a class="btn" href="{renew_url}" target="_blank">Jetzt API-Schlüssel erneuern →</a>
<p style="margin-top:16px;">Nach der Erneuerung trage den neuen Schlüssel in GroundControl unter
<strong>Mitglieder → API-Schlüssel aktualisieren</strong> ein.</p>
<div class="footer">MakerPi GroundControl — automatische Benachrichtigung</div>
</body></html>"""


def easyverein_signup_html(name: str, signup_url: str) -> str:
    """HTML email inviting a guest to sign up as an easyVerein member."""
    if signup_url:
        cta_html = (
            f'<p><a class="btn" href="{signup_url}">Jetzt Mitglied werden</a></p>'
        )
    else:
        cta_html = (
            "<p>Sprich uns vor Ort an oder schreib uns eine E-Mail,"
            " um die Mitgliedschaft zu beantragen.</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Willkommen in der H3cke!</title>
<style>{_BASE_STYLE}</style></head>
<body>
{_H3CKE_LOGO}
<h1>Willkommen in der H3cke! Jetzt Mitglied werden</h1>
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
