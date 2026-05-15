from __future__ import annotations
from datetime import datetime
from app.models.session import ProFormaSession


def export_pdf(session: ProFormaSession, result: dict, output_path: str) -> None:
    from PySide6.QtGui import QPdfWriter, QTextDocument, QPageLayout, QPageSize, QMarginsF

    writer = QPdfWriter(output_path)
    writer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.Letter),
        QPageLayout.Orientation.Portrait,
        QMarginsF(15, 15, 15, 15),
    ))
    doc = QTextDocument()
    doc.setHtml(_build_html(session, result))
    doc.print_(writer)


def _build_html(session: ProFormaSession, result: dict) -> str:
    s = session
    tenant_rows = "".join(
        f"<tr><td>{t.name}</td><td>{t.suite}</td><td>{t.sqft:,.0f}</td>"
        f"<td>${t.rate_psf:.2f}</td><td>{t.lease_exp}</td>"
        f"<td>{t.projection_type}</td></tr>"
        for t in s.tenants
    )
    noi_y1 = result["nois"][0] if result.get("nois") else 0.0
    val_y1 = result["values"][0] if result.get("values") else 0.0
    rev_y1 = result["rental_revenue"][0] if result.get("rental_revenue") else 0.0
    cap = s.cap_rate
    delta = s.cap_delta
    low_val = noi_y1 / (cap - delta) if (cap - delta) > 0 else 0.0
    high_val = noi_y1 / (cap + delta) if (cap + delta) > 0 else 0.0

    return f"""
<html>
<body style="font-family: Segoe UI, Arial, sans-serif; color: #222222; font-size: 10pt;">
  <h1 style="color: #C8102E; margin-bottom: 4px;">NAI Horizon — Pro Forma Summary</h1>
  <h2 style="margin-top: 0;">{s.building_name}</h2>
  <p style="color: #666666; margin-top: 0;">
    Generated: {datetime.now().strftime("%B %d, %Y")}
  </p>
  <hr style="border: none; border-top: 1px solid #DDDDDD;"/>

  <h3>Building Parameters</h3>
  <table cellpadding="4">
    <tr><td><b>Projection Period:</b></td>
        <td>{s.start_month}/{s.start_year} — {s.years} years</td></tr>
    <tr><td><b>Total SF:</b></td><td>{s.total_sqft:,.0f}</td></tr>
    <tr><td><b>Occupied SF:</b></td><td>{s.occupied_sqft:,.0f}</td></tr>
    <tr><td><b>OpEx / SF:</b></td><td>${s.opex_psf:.2f}</td></tr>
    <tr><td><b>Market Avg Rate:</b></td><td>${s.market_avg_rate:.2f}/SF</td></tr>
    <tr><td><b>Market Rent Growth:</b></td><td>{s.market_growth_pct:.1%}</td></tr>
    <tr><td><b>Cap Rate:</b></td><td>{s.cap_rate:.2%}</td></tr>
  </table>

  <h3>Tenants</h3>
  <table border="1" cellpadding="5" width="100%"
         style="border-collapse: collapse; border-color: #DDDDDD;">
    <tr style="background-color: #4A4A4A; color: #FFFFFF;">
      <th>Name</th><th>Suite</th><th>SF</th>
      <th>Rate/SF</th><th>Lease Expiry</th><th>Type</th>
    </tr>
    {tenant_rows}
  </table>

  <h3>Year 1 Preview</h3>
  <table cellpadding="4">
    <tr><td><b>Rental Revenue:</b></td><td>${rev_y1:,.0f}</td></tr>
    <tr><td><b>NOI:</b></td><td>${noi_y1:,.0f}</td></tr>
    <tr><td><b>Building Value:</b></td><td>${val_y1:,.0f}</td></tr>
  </table>

  <h3>Cap Rate Sensitivity</h3>
  <table border="1" cellpadding="5"
         style="border-collapse: collapse; border-color: #DDDDDD;">
    <tr style="background-color: #4A4A4A; color: #FFFFFF;">
      <th>Scenario</th><th>Cap Rate</th><th>Value</th>
    </tr>
    <tr><td>Low (− {s.cap_delta:.2%})</td>
        <td>{cap - delta:.2%}</td><td>${low_val:,.0f}</td></tr>
    <tr><td>Base</td>
        <td>{cap:.2%}</td><td>${val_y1:,.0f}</td></tr>
    <tr><td>High (+ {s.cap_delta:.2%})</td>
        <td>{cap + delta:.2%}</td><td>${high_val:,.0f}</td></tr>
  </table>
</body>
</html>"""
