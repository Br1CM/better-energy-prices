import pandas as pd
from core.schema import InvoiceData

# Mapping from period names to tariff column suffixes
_POWER_PERIOD_MAP = {"P1": "p1", "P2": "p1", "P3": "p3"}  # P2 uses P1 pricing for power
_ENERGY_PERIOD_MAP = {"P1": "p1", "P2": "p2", "P3": "p3"}


def simulate(
    invoice: InvoiceData, tariffs_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict | None]:
    """Simulate invoice cost under each tariff and find the best offer.

    Returns:
        Tuple of (results DataFrame, best offer dict or None).
    """
    results = []

    for _, tariff in tariffs_df.iterrows():
        # Simulate power cost
        power_sim = 0.0
        for pp in invoice.power_periods:
            suffix = _POWER_PERIOD_MAP.get(pp.period, "p1")
            price = tariff[f"power_{suffix}_eur_kw_day"]
            power_sim += pp.power_kw * pp.days * price

        # Simulate energy cost
        energy_sim = 0.0
        for ep in invoice.energy_periods:
            suffix = _ENERGY_PERIOD_MAP.get(ep.period, "p1")
            price = tariff[f"energy_{suffix}_eur_kwh"]
            energy_sim += ep.kwh * price

        total_sim = round(power_sim + energy_sim + invoice.other_costs_eur, 2)
        savings = round(invoice.total_amount_eur - total_sim, 2)
        savings_pct = round(savings / invoice.total_amount_eur, 4) if invoice.total_amount_eur else 0.0

        results.append({
            "tariff": tariff["name"],
            "profile": tariff["profile"],
            "power_sim_eur": round(power_sim, 2),
            "energy_sim_eur": round(energy_sim, 2),
            "total_sim_eur": total_sim,
            "savings_eur": savings,
            "savings_pct": savings_pct,
        })

    results_df = pd.DataFrame(results)

    # Find best offer
    best_offer = _select_best_offer(results_df, invoice.total_amount_eur)

    return results_df, best_offer


def _select_best_offer(results_df: pd.DataFrame, total_actual: float) -> dict | None:
    """Select the best tariff offer respecting the 30% cap."""
    # Candidates that save between 0% and 30%
    candidates = results_df[
        (results_df["savings_pct"] > 0) & (results_df["savings_pct"] <= 0.30)
    ]

    if not candidates.empty:
        best = candidates.loc[candidates["savings_pct"].idxmax()]
        return best.to_dict()

    # If all offers save > 30%, pick closest to 30% from below
    over_30 = results_df[results_df["savings_pct"] > 0.30]
    if not over_30.empty:
        closest = over_30.loc[(over_30["savings_pct"] - 0.30).abs().idxmin()]
        offer = closest.to_dict()
        # Cap savings display at 30%
        offer["savings_pct_capped"] = 0.30
        offer["savings_eur_capped"] = round(total_actual * 0.30, 2)
        return offer

    # No tariff saves money
    return None
