import pandas as pd
from core.schema import InvoiceData

# Period-to-column mapping (mirrors simulate.py)
_POWER_COL = {"P1": "p1", "P2": "p1", "P3": "p3"}
_ENERGY_COL = {"P1": "p1", "P2": "p2", "P3": "p3"}


def generate_proposal_html(
    invoice: InvoiceData,
    best_offer: dict,
    results_df: pd.DataFrame,
    tariff_prices: dict | None = None,
) -> str:
    """Generate an HTML proposal document with actual vs proposed comparison."""

    savings_pct = best_offer.get("savings_pct_capped", best_offer["savings_pct"])
    savings_eur = best_offer.get("savings_eur_capped", best_offer["savings_eur"])

    # Power comparison rows
    power_rows = ""
    for pp in invoice.power_periods:
        if tariff_prices:
            suffix = _POWER_COL.get(pp.period, "p1")
            new_price = tariff_prices[f"power_{suffix}_eur_kw_day"]
            new_amount = round(pp.power_kw * pp.days * new_price, 2)
            diff = round(pp.amount_eur - new_amount, 2)
            diff_class = ' class="positive"' if diff > 0 else (' class="negative"' if diff < 0 else "")
            power_rows += f"""
        <tr>
            <td>{pp.period}</td>
            <td>{pp.power_kw:.2f} kW</td>
            <td>{pp.days}</td>
            <td>{pp.price_eur_per_kw_day:.6f}</td>
            <td>{pp.amount_eur:.2f}</td>
            <td>{new_price:.6f}</td>
            <td>{new_amount:.2f}</td>
            <td{diff_class}>{diff:+.2f}</td>
        </tr>"""
        else:
            power_rows += f"""
        <tr>
            <td>{pp.period}</td>
            <td>{pp.power_kw:.2f} kW</td>
            <td>{pp.days}</td>
            <td>{pp.price_eur_per_kw_day:.6f}</td>
            <td>{pp.amount_eur:.2f} EUR</td>
        </tr>"""

    # Energy comparison rows
    energy_rows = ""
    for ep in invoice.energy_periods:
        if tariff_prices:
            suffix = _ENERGY_COL.get(ep.period, "p1")
            new_price = tariff_prices[f"energy_{suffix}_eur_kwh"]
            new_amount = round(ep.kwh * new_price, 2)
            diff = round(ep.amount_eur - new_amount, 2)
            diff_class = ' class="positive"' if diff > 0 else (' class="negative"' if diff < 0 else "")
            energy_rows += f"""
        <tr>
            <td>{ep.period}</td>
            <td>{ep.kwh:.2f}</td>
            <td>{ep.price_eur_per_kwh:.6f}</td>
            <td>{ep.amount_eur:.2f}</td>
            <td>{new_price:.6f}</td>
            <td>{new_amount:.2f}</td>
            <td{diff_class}>{diff:+.2f}</td>
        </tr>"""
        else:
            energy_rows += f"""
        <tr>
            <td>{ep.period}</td>
            <td>{ep.kwh:.2f} kWh</td>
            <td>{ep.price_eur_per_kwh:.6f} EUR/kWh</td>
            <td>{ep.amount_eur:.2f} EUR</td>
        </tr>"""

    # Power / energy header and totals depend on whether we have comparison data
    if tariff_prices:
        power_header = "<tr><th>Periodo</th><th>Potencia</th><th>Dias</th><th>Precio actual<br>(EUR/kW/dia)</th><th>Importe actual<br>(EUR)</th><th>Precio propuesto<br>(EUR/kW/dia)</th><th>Importe propuesto<br>(EUR)</th><th>Ahorro (EUR)</th></tr>"
        power_total_new = round(best_offer["power_sim_eur"], 2)
        power_total_diff = round(invoice.power_amount_eur - power_total_new, 2)
        power_footer = f'<tr style="font-weight:bold"><td>Total</td><td colspan="3"></td><td>{invoice.power_amount_eur:.2f}</td><td></td><td>{power_total_new:.2f}</td><td class="positive">{power_total_diff:+.2f}</td></tr>'

        energy_header = "<tr><th>Periodo</th><th>Consumo (kWh)</th><th>Precio actual<br>(EUR/kWh)</th><th>Importe actual<br>(EUR)</th><th>Precio propuesto<br>(EUR/kWh)</th><th>Importe propuesto<br>(EUR)</th><th>Ahorro (EUR)</th></tr>"
        energy_total_new = round(best_offer["energy_sim_eur"], 2)
        energy_total_diff = round(invoice.energy_amount_eur - energy_total_new, 2)
        energy_footer = f'<tr style="font-weight:bold"><td>Total</td><td colspan="2"></td><td>{invoice.energy_amount_eur:.2f}</td><td></td><td>{energy_total_new:.2f}</td><td class="positive">{energy_total_diff:+.2f}</td></tr>'
    else:
        power_header = "<tr><th>Periodo</th><th>Potencia</th><th>Dias</th><th>Precio</th><th>Importe</th></tr>"
        power_footer = f'<tr style="font-weight:bold"><td>Total Potencia</td><td colspan="3"></td><td>{invoice.power_amount_eur:.2f} EUR</td></tr>'
        energy_header = "<tr><th>Periodo</th><th>Consumo</th><th>Precio</th><th>Importe</th></tr>"
        energy_footer = f'<tr style="font-weight:bold"><td>Total Energia</td><td colspan="2"></td><td>{invoice.energy_amount_eur:.2f} EUR</td></tr>'

    html = f"""\
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Propuesta de Ahorro Energetico</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }}
        h1 {{ color: #2c5f2d; border-bottom: 2px solid #2c5f2d; padding-bottom: 10px; }}
        h2 {{ color: #2c5f2d; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: right; }}
        th {{ background-color: #2c5f2d; color: white; }}
        td:first-child {{ text-align: left; }}
        .summary-box {{ background-color: #f0f7f0; border: 2px solid #2c5f2d; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
        .savings {{ font-size: 2em; color: #2c5f2d; font-weight: bold; }}
        .positive {{ color: #2c5f2d; font-weight: bold; }}
        .negative {{ color: #c0392b; font-weight: bold; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <h1>Propuesta de Ahorro Energetico</h1>

    <div class="summary-box">
        <p>Tarifa recomendada: <strong>{best_offer['tariff']}</strong></p>
        <p class="savings">Ahorro estimado: {savings_eur:.2f} EUR ({savings_pct:.1%})</p>
        <p>Coste actual: {invoice.total_amount_eur:.2f} EUR &rarr; Coste propuesto: {best_offer['total_sim_eur']:.2f} EUR</p>
    </div>

    <h2>Comparativa de Potencia — Actual vs Propuesta</h2>
    <table>
        {power_header}
        {power_rows}
        {power_footer}
    </table>

    <h2>Comparativa de Energia — Actual vs Propuesta</h2>
    <table>
        {energy_header}
        {energy_rows}
        {energy_footer}
    </table>

    <h2>Otros Costes</h2>
    <p>Impuestos, alquiler de equipos y otros: <strong>{invoice.other_costs_eur:.2f} EUR</strong> (se mantienen constantes en la simulacion).</p>

    <div class="footer">
        <p>Este documento es una estimacion basada en los datos extraidos de la factura. Los importes reales pueden variar.</p>
    </div>
</body>
</html>"""

    return html
