import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from io import BytesIO

from core.extract import extract_invoice
from core.validate import validate
from core.simulate import simulate
from core.tariffs import get_tariffs
from core.formatters import generate_proposal_html

st.set_page_config(page_title="Analizador de Facturas Electricas", layout="wide")


def init_state():
    defaults = {
        "step": 1,
        "uploaded_file": None,
        "file_bytes": None,
        "file_type": None,
        "invoice": None,
        "validation_report": None,
        "results_df": None,
        "best_offer": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_pdf_preview(file_bytes: bytes) -> list[bytes]:
    """Render first 2 pages of PDF as images."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images = []
    for i, page in enumerate(doc):
        if i >= 2:
            break
        pix = page.get_pixmap(dpi=150)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


# ─── Screen 1: Upload & Preview ──────────────────────────────────────────────

def screen_upload():
    st.header("1. Sube tu factura electrica")

    uploaded = st.file_uploader(
        "Selecciona un PDF o imagen de tu factura",
        type=["pdf", "png", "jpg", "jpeg"],
    )

    if uploaded is not None:
        file_bytes = uploaded.read()
        file_type = uploaded.type

        st.session_state.file_bytes = file_bytes
        st.session_state.file_type = file_type

        # Preview (constrained width so images don't force scrolling)
        st.subheader("Vista previa")
        _, preview_col, _ = st.columns([1, 2, 1])
        with preview_col:
            if file_type == "application/pdf":
                images = render_pdf_preview(file_bytes)
                for img in images:
                    st.image(img, use_container_width=True)
            else:
                st.image(file_bytes, use_container_width=True)

        if st.button("Extraer datos de la factura", type="primary"):
            with st.spinner("Extrayendo los datos de tu factura..."):
                try:
                    invoice = extract_invoice(file_bytes, file_type)
                    invoice, report = validate(invoice)
                    st.session_state.invoice = invoice
                    st.session_state.validation_report = report
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en la extraccion: {e}")


# ─── Screen 2: Extracted Data + Edit ─────────────────────────────────────────

def screen_data():
    st.header("2. Datos extraidos de la factura")
    invoice = st.session_state.invoice
    report = st.session_state.validation_report

    # Validation status
    if report["status"] == "ok":
        st.success(f"Validacion correcta (puntuacion: {report['score']}/100)")
    else:
        st.warning(f"Requiere revision (puntuacion: {report['score']}/100)")
        for w in report["warnings"]:
            st.warning(w)

    # Totals
    st.subheader("Totales")
    col1, col2, col3, col4 = st.columns(4)
    total = col1.number_input("Total (EUR)", value=invoice.total_amount_eur, format="%.2f", key="total")
    energy = col2.number_input("Energia (EUR)", value=invoice.energy_amount_eur, format="%.2f", key="energy")
    power = col3.number_input("Potencia (EUR)", value=invoice.power_amount_eur, format="%.2f", key="power")
    other = col4.number_input("Otros (EUR)", value=invoice.other_costs_eur, format="%.2f", key="other")

    # Metadata
    st.subheader("Metadatos")
    mcol1, mcol2, mcol3 = st.columns(3)
    cups = mcol1.text_input("CUPS", value=invoice.cups or "", key="cups")
    start = mcol2.text_input("Fecha inicio", value=invoice.billing_start_date or "", key="start")
    end = mcol3.text_input("Fecha fin", value=invoice.billing_end_date or "", key="end")

    # Power periods
    st.subheader("Periodos de potencia")
    power_data = [
        {"Periodo": pp.period, "kW": pp.power_kw, "Dias": pp.days,
         "EUR/kW/dia": pp.price_eur_per_kw_day, "Importe EUR": pp.amount_eur}
        for pp in invoice.power_periods
    ]
    power_df = pd.DataFrame(power_data) if power_data else pd.DataFrame(
        columns=["Periodo", "kW", "Dias", "EUR/kW/dia", "Importe EUR"]
    )
    edited_power = st.data_editor(
        power_df,
        num_rows="dynamic",
        key="power_editor",
        column_config={
            "EUR/kW/dia": st.column_config.NumberColumn(format="%.6f"),
        },
    )

    # Energy periods
    st.subheader("Periodos de energia")
    energy_data = [
        {"Periodo": ep.period, "kWh": ep.kwh, "EUR/kWh": ep.price_eur_per_kwh,
         "Importe EUR": ep.amount_eur}
        for ep in invoice.energy_periods
    ]
    energy_df = pd.DataFrame(energy_data) if energy_data else pd.DataFrame(
        columns=["Periodo", "kWh", "EUR/kWh", "Importe EUR"]
    )
    edited_energy = st.data_editor(
        energy_df,
        num_rows="dynamic",
        key="energy_editor",
        column_config={
            "EUR/kWh": st.column_config.NumberColumn(format="%.6f"),
        },
    )

    if st.button("Simular tarifas", type="primary"):
        # Rebuild invoice from edited values
        from core.schema import InvoiceData, PowerPeriod, EnergyPeriod

        power_periods = []
        for _, row in edited_power.iterrows():
            power_periods.append(PowerPeriod(
                period=str(row["Periodo"]),
                power_kw=float(row["kW"]),
                days=int(row["Dias"]),
                price_eur_per_kw_day=float(row["EUR/kW/dia"]),
                amount_eur=float(row["Importe EUR"]),
            ))

        energy_periods = []
        for _, row in edited_energy.iterrows():
            energy_periods.append(EnergyPeriod(
                period=str(row["Periodo"]),
                kwh=float(row["kWh"]),
                price_eur_per_kwh=float(row["EUR/kWh"]),
                amount_eur=float(row["Importe EUR"]),
            ))

        updated_invoice = InvoiceData(
            total_amount_eur=total,
            energy_amount_eur=energy,
            power_amount_eur=power,
            other_costs_eur=other,
            power_periods=power_periods,
            energy_periods=energy_periods,
            cups=cups or None,
            billing_start_date=start or None,
            billing_end_date=end or None,
            supply_address=invoice.supply_address,
            notes=invoice.notes,
            validation_status=invoice.validation_status,
        )

        tariffs_df = get_tariffs()
        results_df, best_offer = simulate(updated_invoice, tariffs_df)

        st.session_state.invoice = updated_invoice
        st.session_state.results_df = results_df
        st.session_state.best_offer = best_offer
        st.session_state.step = 3
        st.rerun()

    if st.button("Volver"):
        st.session_state.step = 1
        st.rerun()


# ─── Screen 3: Tariff Comparison ─────────────────────────────────────────────

def screen_comparison():
    st.header("3. Comparativa de tarifas")
    results_df = st.session_state.results_df
    best_offer = st.session_state.best_offer
    tariffs_df = get_tariffs()

    if best_offer is None:
        st.info("No se ha detectado ahorro con ninguna tarifa. Revisa los datos de la factura.")
    else:
        st.success(
            f"Tarifa recomendada: **{best_offer['tariff']}** — "
            f"Ahorro: {best_offer['savings_eur']:.2f} EUR ({best_offer['savings_pct']:.1%})"
        )

    # Top 3 tariffs by savings
    top3 = results_df.nlargest(3, "savings_eur").copy()

    # Merge tariff prices for display
    top3 = top3.merge(tariffs_df, left_on="tariff", right_on="name", how="left")

    # Build display table
    display_df = pd.DataFrame({
        "Tarifa": top3["tariff"],
        "Perfil": top3["profile_x"] if "profile_x" in top3.columns else top3["profile"],
        "Potencia Sim.": top3["power_sim_eur"].apply(lambda x: f"{x:.2f} EUR"),
        "Energia Sim.": top3["energy_sim_eur"].apply(lambda x: f"{x:.2f} EUR"),
        "Total Sim.": top3["total_sim_eur"].apply(lambda x: f"{x:.2f} EUR"),
        "Ahorro": top3.apply(lambda r: f"{r['savings_eur']:.2f} EUR ({r['savings_pct']:.1%})", axis=1),
    })

    def highlight_best(row):
        if best_offer and row["Tarifa"] == best_offer["tariff"]:
            return ["background-color: #d4edda"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_best, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # Show energy & power prices per tariff
    st.subheader("Precios por tarifa")
    for _, row in top3.iterrows():
        with st.expander(f"{row['tariff']} — {row['profile_x'] if 'profile_x' in top3.columns else row['profile']}"):
            pcol1, pcol2 = st.columns(2)
            with pcol1:
                st.markdown("**Potencia (EUR/kW/dia)**")
                st.write(f"- P1: {row['power_p1_eur_kw_day']:.6f}")
                st.write(f"- P3: {row['power_p3_eur_kw_day']:.6f}")
            with pcol2:
                st.markdown("**Energia (EUR/kWh)**")
                st.write(f"- P1: {row['energy_p1_eur_kwh']:.6f}")
                st.write(f"- P2: {row['energy_p2_eur_kwh']:.6f}")
                st.write(f"- P3: {row['energy_p3_eur_kwh']:.6f}")

    col1, col2 = st.columns(2)
    if col1.button("Ver propuesta final", type="primary", disabled=best_offer is None):
        st.session_state.step = 4
        st.rerun()
    if col2.button("Volver a datos"):
        st.session_state.step = 2
        st.rerun()


# ─── Screen 4: Final Proposal ────────────────────────────────────────────────

def _get_best_tariff_prices(tariff_name: str) -> dict:
    """Look up the price columns for a given tariff."""
    tariffs_df = get_tariffs()
    row = tariffs_df[tariffs_df["name"] == tariff_name].iloc[0]
    return row.to_dict()


def screen_proposal():
    st.header("4. Propuesta de ahorro")
    invoice = st.session_state.invoice
    best_offer = st.session_state.best_offer
    results_df = st.session_state.results_df

    savings_pct = best_offer.get("savings_pct_capped", best_offer["savings_pct"])
    savings_eur = best_offer.get("savings_eur_capped", best_offer["savings_eur"])

    tariff_prices = _get_best_tariff_prices(best_offer["tariff"])

    # Period-to-column mapping (same as simulate.py)
    power_col = {"P1": "p1", "P2": "p1", "P3": "p3"}
    energy_col = {"P1": "p1", "P2": "p2", "P3": "p3"}

    # Summary
    st.markdown("### Resumen")
    col1, col2, col3 = st.columns(3)
    col1.metric("Coste actual", f"{invoice.total_amount_eur:.2f} EUR")
    col2.metric("Coste propuesto", f"{best_offer['total_sim_eur']:.2f} EUR")
    col3.metric("Ahorro", f"{savings_eur:.2f} EUR ({savings_pct:.1%})")

    st.markdown(f"**Tarifa recomendada:** {best_offer['tariff']}")

    # Power comparison table
    st.markdown("### Comparativa de potencia")
    power_rows = []
    for pp in invoice.power_periods:
        suffix = power_col.get(pp.period, "p1")
        new_price = tariff_prices[f"power_{suffix}_eur_kw_day"]
        new_amount = round(pp.power_kw * pp.days * new_price, 2)
        power_rows.append({
            "Periodo": pp.period,
            "kW": pp.power_kw,
            "Dias": pp.days,
            "Precio actual (EUR/kW/dia)": pp.price_eur_per_kw_day,
            "Importe actual (EUR)": pp.amount_eur,
            "Precio propuesto (EUR/kW/dia)": new_price,
            "Importe propuesto (EUR)": new_amount,
            "Diferencia (EUR)": round(pp.amount_eur - new_amount, 2),
        })
    if power_rows:
        st.dataframe(pd.DataFrame(power_rows), use_container_width=True, hide_index=True)

    # Energy comparison table
    st.markdown("### Comparativa de energia")
    energy_rows = []
    for ep in invoice.energy_periods:
        suffix = energy_col.get(ep.period, "p1")
        new_price = tariff_prices[f"energy_{suffix}_eur_kwh"]
        new_amount = round(ep.kwh * new_price, 2)
        energy_rows.append({
            "Periodo": ep.period,
            "kWh": ep.kwh,
            "Precio actual (EUR/kWh)": ep.price_eur_per_kwh,
            "Importe actual (EUR)": ep.amount_eur,
            "Precio propuesto (EUR/kWh)": new_price,
            "Importe propuesto (EUR)": new_amount,
            "Diferencia (EUR)": round(ep.amount_eur - new_amount, 2),
        })
    if energy_rows:
        st.dataframe(pd.DataFrame(energy_rows), use_container_width=True, hide_index=True)

    st.markdown(f"### Otros costes: {invoice.other_costs_eur:.2f} EUR")
    st.caption("Los otros costes (impuestos, alquiler de equipos, etc.) se mantienen constantes.")

    # Export
    html = generate_proposal_html(invoice, best_offer, results_df, tariff_prices)
    st.download_button(
        "Descargar propuesta (HTML)",
        data=html,
        file_name="propuesta_ahorro.html",
        mime="text/html",
        type="primary",
    )

    if st.button("Volver a comparativa"):
        st.session_state.step = 3
        st.rerun()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    init_state()

    st.title("Analizador de Facturas Electricas")
    st.caption("Sube tu factura, revisa los datos y obtiene una propuesta de ahorro.")

    # Navigation
    screens = {1: screen_upload, 2: screen_data, 3: screen_comparison, 4: screen_proposal}
    screen_fn = screens.get(st.session_state.step, screen_upload)
    screen_fn()


if __name__ == "__main__":
    main()
