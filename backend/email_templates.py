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
   .logo { max-width: 200px; margin: 0 auto 20px; display: block; }
   .logo svg { width: 100%; height: auto; display: block; }
   .logo-text { font-size: 0.8em; color: #666; text-align: center; margin-top: 4px; }
"""

_H3CKE_LOGO_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAKAAAAAoCAIAAAD2TmbPAAASxElEQVR4nN1cWWxc13k+213m3pnhDClKJEVK"
    "okRLtmVtFrxIlipFluPEaaIkRlUUsJ9aoygKFAiQokDbl6JPBYoCfe1TmqRIALuOaic17NiyFtuKbcm2JEvU"
    "Yu0SqW04+8zdzvmLcw5nSHEZzgxtWvWPgUGP7j333POdf/v+/wxeNrgGIwRISv2P9gRP+ns+43xFQtR/OUIR"
    "YA5ITJoyRkAwYggxDBgjgBbm397q6QdDE3fpCyavbfMCCDFAiE96AkaItDXYlHEQQnSWcUAJmodgJc1ejOSH"
    "I1QRGBByieg2ojQVScpjRKIcAikLnOM0G9E8J4HADCMLA0Z6EzQScc9WkHujmdXT8xFqL+lvAGEmZzdtfLlc"
    "aD7CVtv+j9IlriZqYhgJ2C8yqZbGJAh5Aq+J+Xs7C5FcFmRguBnSn99NcfnOk14M4zAMVz+wcu3DD4ZB2DxI"
    "dQEAZrBPPj159dp1wzDm3ChELaUncJyIda6/wfFWWUE34w4VDEvF1fPiAAGQAiejATvjmSer1iXfDAE7ZFaY"
    "MEI+4D2pwibH99Rbx7A4UHTfKbgOgQY7AyMUAO41whe78lTNQCDkYjhYdN4uuLHavUTtyG3xyrMd5Spg0upC"
    "KWt0PTBYBxHrHS8EuX9iGFy1qVu1CQKhOBEbHN9Xr2pjSHjGzFcKkUgklg0s9T0ft24rAMA0jeEzXwgxp3bJ"
    "NaoK7BDxnY7yzkRluRUaGCLAEeBQfqTe6CsxkivYyfhig29yvR8IfNaz9hfcT8o2R9jGMwAmgQc0YEYbXa8k"
    "5PoniBj2LCEHa2Ti9Y17UsUn49WyUngDQTaipz1L4z2xVggtMqINavw2ALYw2BiYtl2RAhiw3JUtDjUxm4rA"
    "gbpdNByHc+77vh8ETWrw5MuatO3ab1UE3uh4ezsLQ3bAAfvqM+Wy8WGlY0Yc4UAOL8He6PjrY96Jiv3yWPK8"
    "b9lEzDjXAHBF4Kr6R4rkvmk8MaWX5FGnujVezXJaU1/0q7Hk1cBIkKnbNqqNXwdYNAcQIBRiqCp3I59K1Fek"
    "XWden72eR+NxKKW2bct1bAiwnA/GXIgoiupfYowBoFqt4NmNljaqHPCfdBb2pIsUo7KYsBUUIZMARVIpQW1r"
    "FXbIZYtAblBR2xwY4Y2ut9oOfj2WPFB0Z4yGcNNvXXe9DuHPpwukNlycwPGydbjoxKehO3l8/QiKkUl4w4dM"
    "rJ6JwSGMoYUVQkgulz977oKErcF6gMTS833LMpcP9I9/B2CZ5ocff3L12g3TnNkB60VECL3UPbYrWakIEoJc"
    "HSEjA2RhkY/IOc+67Bs3Q1bicrVMDCnG+4xohRX2m2GcgA/yLqS0jWH054tyoyE7WbVtPK+IByuX8cNU6YFY"
    "UFZWVzvaV7LJCGGjYTilfCoai8gFzyb3WvLZhCEYDRcWYBkiMXbp8tULFy83vhJjHEWRE4t9+5lvEUKEEABg"
    "W9bJU8PHPj3BGJsNXWn0AL/UnX06WSkqxdXGySXiTsgOFOMflmKjIVO2Wgax+ha5nRC4BAbM8HG3uiVRWcS4"
    "J0ik4P+oHDvnWda80Q2Uz34uVfKV6+XSbcO+bPysZ7oN47K6Rl7wzX+92dXkPlMmUOZ+Cy2EEEppgwswxpxz"
    "13W/++yuvp4lnu9rdC9cuvL+kY8ppdpQz3CjUoi9nYWnk+WiUhFQ39sYDhacV7LJkcAwCZgYDBVyTLpV/s0R"
    "Ou+bw571ZsH9TkdpV6IcpzAW0V+PJQOYOdRqXiSigH+YKnQxXlI7z8JwNWC/zScs0uzWIQjZBFraal8DwI1j"
    "JYyx1tcd27b09iyu+r5cC8u6efvOgUMfAACldMbbtbnb5Hh70kVtAJFaVobhvzLJ13MJhlGSCZ25zvh4rLYC"
    "wjAWsZ/dTR8tx17qzr6Vj18JzOnhT0ui5/ao421NVPXcQEUDr44lchGZU30ni578/Q5wYwnDcNvWJ1atWuEr"
    "dBlj+XzhnXcPe75vzGKctf65ROztLDCEwppltjD8MtPxWi4RV2HwFCpmuuiFNrDU8tOe9U8j3aFKtOaDrp6b"
    "Q8TznUU9K+Uy4A8l+0jJaZw0z19aza++WsEY+76/ft3a9eseCoJAh9xBELzz7uFcrtAAXZ3yPpWoDNmBpgWE"
    "WtN38u5vc/GESu5b0hJ5O4aKdMOt0zH3CpVzI7uT5QdsSYkQpVX5CP93NilzZvTVyn0EMCIE94OhVYNbntg"
    "chhEAECJ97YFDH4zevG1ZjXgrrpiWbyUqXPJ/4yHJtcB4OZvUHq6N+EgobOYJgCa8BszwezK2knMT0o+KN/"
    "KJS74xT7/+/wlgrbu9Pd07tm+pO2nG2JE/HP3i4mXLMqXznEUIQr7AD9nBcivUiyiTCgRv5OJZTox5VD6+lJ"
    "JJhCRv1cm4ZpNsDOc98818BCv5zQdYJ0XJZGLXzu2maXIuU1nbsj759OTJUwO2Zc1JYAFCGxzPUOFlnVQ/Wr"
    "HtBVnE2UQ6DpBx31OJiiZbtAa/kk2WBaELNYevWXTYbBhs185tqVSH5q1Mwzg1fPajo59ZltlcCANDdqCZQg"
    "3wiaqdjShb2MKlrsXJjzLvit4Xz6cLmmQGFRa8V3Q+Kdttx1a4ic8cUfSM1835yLZFKNm5Y+vSvh7P83WWfP"
    "tu5uNjxwGE73NCKGNyu8+W+0aAu42wm3HtgDWFe8az0MKKLhOVuNQZoeizqsB/2plfbUveSidsmZD+Jptg7X"
    "ImsjirPtA0IlMBlrS7ml/zmBHF1LdtCQHg8cceXTO0yvcDotJXIUTcdb//3DP5QnFkZPTK1RtjuRyjUqZjrA"
    "BGXaoCqDVYJ50jAWPNUXpfimBZV8ZrbP/5dF4TESoOQM92lAOFrrYrr+USIyGLt6u+VLpwYTV8L+0F6mUPdi"
    "9OeDHjf9uTafXBQhXLolqA05Lr7Uyn1619MAjDKTVB27bS6Y7BFQMbN1QvXLp8/MSpQqFomuZ0jAGhDiooggo"
    "QkClNARDmVPFZAFaKNHR8nrH3+x6k5+q+U7Npp2s2O8W56gWNy66Pxjz/3npnQZ5m0AoRuBMxfyPO2m9v+/"
    "RYBXBw/qY35LN1QUZDhO7ptkbFS2Vy+dHR28tX9YfhLIFQOMnhOBcFnSkPzaN9Y88vGLZwPtHPrp46cqMGNuk"
    "pibjayEbM8hXnWPOZKI9VRuuvyJRma5eojfzbkXgBIGm6kHTRPM2S82J2tp0Udk/3GGyEDmziRYI6fJ1q4Jl"
    "matljcEYB0E4fO58b+8SHnGEZTbMGKOUgIAwktkwAHi+7zixZ3bvOHToyPDZ81Mw1rTfPW9Rq7gDWlChCBlE"
    "5nO1livZ/FWfxmOud6wcm09UL9TebXwBQRBMKl5PBZggFKO8pa1f0+Dxan9Loq3xtWs3Xt33O00ZUUqdmJ1O"
    "p/qX9vX2LGaMhmEkC8OcE0K2b3uyWKrcGBmZ3K+jVaeOpfR2BBhGulC4kG64KrCnKkX6oRShBJV4y0wd8LZE"
    "5cOyfbQcazuEls1iDevBWoNjEwp8L8A6PPmsEmvpqTqOTTO+0tJV1JYFAGVz+frfAHDp8rUTJ0/39i55/LFN"
    "S7q7Q2W9VTZlPPn4o6//7i4XfHKnR1ngemAokGSPHSLKEWvDqLQnsjGDiLfyiVezSZeOszKA0F8vHlsbk+yp"
    "ntuP08XhqtUG/Qmqnj0SsGMVi85xGYyGRn1nTwAsVJh3J2L/fqur1Si6IvBj8erf9WbaUGItbFplGgCuXR+"
    "5fTuz++ntywf6NcZhGC5e3DU4uGz4zDmrRoAQjLIRDWshngBJWy5i0c2ImQurwT7gPKeqY1KzHOQ32cRqO6"
    "Otqgd4yA6eTpb35ZIJIlryxBq5a4Hxs7tpS27mBldihsAi45dMNei6TmmRlj+qwtq+wDTRZFYYhocOH8kX"
    "CmxSjrRieX+9oqzbBzMRK3BKFZpypxJYaYVz1o6+dNHJLsPSlhIs99nnVfs9WTKScGpD/VyqtNQYp1RbFYYh"
    "TkScQINPgohYDd2ZmSxo9/OlixDCNI1CoXTm7BdUcR3ySy7S6bRtW7qxUmcCeU5GQmbUEiMB+BHHm2cPRns"
    "yZU0YRq/l4pmImmoyEeBOxveki1FbM9NlrmY+9xFV2UQqRUZHb9X7qIXq7rBtWwihv1G2kZzxxgkAomKu1Va"
    "4UtUevsY31InNjcB4IxfXAOuuym2JygbHa6PbuQ253wFWqRTxPC8Io3pURQiWFrt2gbbSx8tWmY83cnCZC8Du"
    "ZLmRs1oQ0czD20X3omfqXiqt1j9KFxegVvi1AdzimQYghJJJtAUAcDGR62kW8HJgDHuygVnlgjJj2RKvbHS8"
    "ssBt123meVhrPEfHqMTJvlxCD6bn9lDM35koVyY1PH9zAFbBsGQwmoRZCJFMJizT1E5XcyOymweTetglj6gA"
    "/n3BrdcbdE/hC135Tsp1H0Wrok29LgrNq5oCMjf9uBw7Vo7F1P5TxDX5Xqq0hHEd/H9zANb8c09Pt2maksGY"
    "60yGIi/RypXLCR2/khCSzxeqVW+yTmtLeLxif1yydcg63kphhX+1OGth8BVUTYpuYS9wMmgF/9B3Z8gabwOa"
    "jwBC+7KJiioD6xbaHiP6fqoYtJKR3u8Aa3RTHcnvfnvXrp1POU7M82Rb3YxnBTHGhJBKtTo4uGzV4PKgFmQR"
    "Qm6MjEbRhEueuAWhl7PJbC1kJSqi2eB6P+nJpCivt0nPtqD1f/UA+wI/01H6aU/moVjw4qJ8kvBgHqo23sjh"
    "m/vl8TKpxFTNbWey/HDM/0qjrQUFWAhBCHlq6xO2ZQ309+3542cfGBqMhPCDQPpUPH4uVCKntkK1Wl2xfGDn"
    "9i26CKG6tEi5XL54+er00qEOWa8Fxi8zHUx5O6hhvN7x/7Hv7ha3EgAuC8zvPRKiP7peUhHEE3jICn7Sk/nL"
    "7mycQjYiK63wha4Cmd9BTk2g/m8uPhowo3ao0MKS22LqHM2XWPCf/FnQtlkhxOOPbRro7w0CWRxMJhO7n/6j"
    "G9dHz5z7YvTmrUqlyoXQpwwopamO5Jo1Q2sfWkMp5VwSkzotPn7yVDaXt2aqKSm+EA4XnUWM/1lXQR8I1kTb"
    "YiP6m56x4xX7YNE555l5TidlojKWMjDqoHzI8rbEq5tcL0ZEVdH6BMs63Y5k+WDROe1ZbZ9ekVQUQnci+no+"
    "/hfd+VBpbUVWGL1ticr+gttMd7Q8UtYiwb5wAMu6gmEM9Pfp4IgQortzBgb6Bvr7CqVSNpsrFkthGJmmkUwm"
    "FnV1Ok4sDKM6upZljY7ePn7iVIP+We2M92UTGMHeroI6Jiq9ry5lbna9TY53K2RXfGNUHvemHCTHm6LybFK/"
    "JdtCmDyURyrKnismk4/6z7up87U8p23RlYDDRfepePVB1d6rafw9qeJnFbvE5TkoaNhYOGQHf9979z4FmBAS"
    "RtHv3z64Y/vWgYG+wJdHNXVIjBByHSeZiCu3KvUJAKKI+748YlpHN58v7D/4fhCEs51NmnB4BF7NJjMRfaEr"
    "n2RSF+uqjBHqNqI+M6wH27UuCByBDJvrJCJWXQwjAft5JnW0bMeaPmDSaBHUHPZlEz/tGSeofcBLzei5jtIv"
    "MimjIcksEOogotv1W3qi/AkHTW7V/2hPJt8+4zi6vF8olt54a/+jG9c9svZByzTDKNTLxpXMMKzS9VjMHr15"
    "+90D7+dyecNohG59Mg6BA0V56mRvZ2GTUyUYeypzBpX8NC6KqJ9wECVO3sjF/yeXyER0Nvs55a2hOSU+XrGP"
    "lGI71PE4IkthZFeyfKQUu+SbU3ppp4AiEApUz1fzIhuXXAIyLVWR3mSeunnR7IxLhKEWzpplHH26UAhx5KNj"
    "ly5fXb/u4WUDS23bBpD9G1MO7ROMCaUykK5UT35++tPjnwdB2Ay6k+t31wLj3252bXaru5Pl1bavmqGkpnJ9"
    "4P3ebkiGQLfDZSJ6sOzuL7oXPNPAEpLZ9r2l2H/9d5wIHb3PuVZEEtSJza6XYiJSvQkOgRe78v9yc9EUdI3a"
    "+G0HwywT0Q+KMV14kb+tEc380wuNZ0wxykX0/WKs/hsdtyJpG2a4WPEblmnevnP37f2Huro6ly/r7+tdkupI"
    "WpZVPzkohPD8IF8oXL8xevHi5Uw2ZzApLf16i1AMF0Low5LsVB20wvUx/4GY38OiBBWGLPiMB9sccIXjbMSu"
    "SjrMPF21boWMKGi1Ds321l94pk0cX9kGm8DVwJBbpOEcdbR/PTB+lenY7FY95TW0hvQZ4ZXA1LtEfzMSGO8V"
    "HX1Ne4L7V6zRqIz/P5bwtDGQANTSODqLlTGU4AZjruvE3XgsZhmMCQDP84qlcqlUDoKAUtoqtFOEKJB8+etJ"
    "2MKig4pOxjsotwkQBCHgkiD6V3aKnAiETXX4rJkSWQQTblNBLmuFzch4F8q9DzCnmT2ujE3zbzpd/g/3u42r"
    "f7LMpQAAAABJRU5ErkJggg=="
)

_H3CKE_LOGO = (
    '<div class="logo">'
    f'<img src="data:image/png;base64,{_H3CKE_LOGO_B64}"'
    ' alt="H3cke Makerspace" style="max-width:200px;height:auto;display:block;margin:0 auto">'
    '<div class="logo-text">H3cke Makerspace</div>'
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
