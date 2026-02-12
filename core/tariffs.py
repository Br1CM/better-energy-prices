import pandas as pd

TARIFFS = [
    {
        "name": "TARIFA_A_FIJA_EQUILIBRADA",
        "power_p1_eur_kw_day": 0.0731270,
        "power_p3_eur_kw_day": 0.0731270,
        "energy_p1_eur_kwh": 0.105,
        "energy_p2_eur_kwh": 0.105,
        "energy_p3_eur_kwh": 0.095,
        "profile": "Consumo equilibrado",
    },
    {
        "name": "TARIFA_B_DH_NOCTURNA",
        "power_p1_eur_kw_day": 0.068,
        "power_p3_eur_kw_day": 0.085,
        "energy_p1_eur_kwh": 0.120,
        "energy_p2_eur_kwh": 0.110,
        "energy_p3_eur_kwh": 0.065,
        "profile": "Alto consumo en valle",
    },
    {
        "name": "TARIFA_C_SOLAR_AMIGABLE",
        "power_p1_eur_kw_day": 0.105,
        "power_p3_eur_kw_day": 0.080,
        "energy_p1_eur_kwh": 0.155,
        "energy_p2_eur_kwh": 0.095,
        "energy_p3_eur_kwh": 0.070,
        "profile": "Buen ajuste en llano/valle",
    },
    {
        "name": "TARIFA_D_VERDE_SIMPLE",
        "power_p1_eur_kw_day": 0.115,
        "power_p3_eur_kw_day": 0.095,
        "energy_p1_eur_kwh": 0.112,
        "energy_p2_eur_kwh": 0.112,
        "energy_p3_eur_kwh": 0.112,
        "profile": "Precio energia plano",
    },
    {
        "name": "TARIFA_E_FIJA",
        "power_p1_eur_kw_day": 0.0731270,
        "power_p3_eur_kw_day": 0.0731270,
        "energy_p1_eur_kwh": 0.1102,
        "energy_p2_eur_kwh": 0.1102,
        "energy_p3_eur_kwh": 0.1102,
        "profile": "Precio plano",
    },
]


def get_tariffs() -> pd.DataFrame:
    return pd.DataFrame(TARIFFS)
