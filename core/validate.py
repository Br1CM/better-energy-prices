from core.schema import InvoiceData

TOLERANCE = 0.50  # EUR


def validate(invoice: InvoiceData) -> tuple[InvoiceData, dict]:
    """Validate and normalize extracted invoice data.

    Returns:
        Tuple of (cleaned invoice, validation report dict).
    """
    warnings = []
    score = 100

    # --- Normalization ---
    data = invoice.model_dump()

    for pp in data["power_periods"]:
        pp["amount_eur"] = round(pp["amount_eur"], 2)
        if pp["days"] <= 0:
            warnings.append(f"Potencia {pp['period']}: dias <= 0 ({pp['days']})")
            score -= 20

    for ep in data["energy_periods"]:
        ep["amount_eur"] = round(ep["amount_eur"], 2)
        if ep["kwh"] < 0:
            warnings.append(f"Energia {ep['period']}: kWh negativo ({ep['kwh']})")
            score -= 20
        if ep["price_eur_per_kwh"] > 1.0:
            warnings.append(f"Energia {ep['period']}: precio > 1.0 EUR/kWh ({ep['price_eur_per_kwh']})")
            score -= 20

    data["total_amount_eur"] = round(data["total_amount_eur"], 2)
    data["energy_amount_eur"] = round(data["energy_amount_eur"], 2)
    data["power_amount_eur"] = round(data["power_amount_eur"], 2)
    data["other_costs_eur"] = round(data["other_costs_eur"], 2)

    # --- Cuadre de periodos vs totales ---
    power_sum = round(sum(pp["amount_eur"] for pp in data["power_periods"]), 2)
    energy_sum = round(sum(ep["amount_eur"] for ep in data["energy_periods"]), 2)

    if abs(data["power_amount_eur"] - power_sum) > TOLERANCE:
        warnings.append(
            f"Potencia total ({data['power_amount_eur']}) != suma periodos ({power_sum})"
        )
        score -= 20

    if abs(data["energy_amount_eur"] - energy_sum) > TOLERANCE:
        warnings.append(
            f"Energia total ({data['energy_amount_eur']}) != suma periodos ({energy_sum})"
        )
        score -= 20

    # --- Cuadre total general ---
    expected_total = round(
        data["energy_amount_eur"] + data["power_amount_eur"] + data["other_costs_eur"], 2
    )
    if abs(data["total_amount_eur"] - expected_total) > TOLERANCE:
        warnings.append(
            f"Total ({data['total_amount_eur']}) != energia + potencia + otros ({expected_total})"
        )
        score -= 20

    # --- Status ---
    score = max(score, 0)
    if score >= 80:
        data["validation_status"] = "ok"
    else:
        data["validation_status"] = "needs_review"

    cleaned = InvoiceData(**data)
    report = {
        "score": score,
        "warnings": warnings,
        "status": data["validation_status"],
    }

    return cleaned, report
