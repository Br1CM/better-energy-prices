from pydantic import BaseModel, Field
from typing import Optional


class PowerPeriod(BaseModel):
    period: str = Field(description="Periodo de potencia (ej: P1, P3)")
    power_kw: float = Field(description="Potencia contratada en kW")
    days: int = Field(description="Numero de dias facturados")
    price_eur_per_kw_day: float = Field(description="Precio en EUR/kW/dia")
    amount_eur: float = Field(description="Importe total del periodo en EUR")


class EnergyPeriod(BaseModel):
    period: str = Field(description="Periodo de energia (ej: P1, P2, P3)")
    kwh: float = Field(description="Consumo en kWh")
    price_eur_per_kwh: float = Field(description="Precio en EUR/kWh")
    amount_eur: float = Field(description="Importe total del periodo en EUR")


class InvoiceData(BaseModel):
    # Totales
    total_amount_eur: float = Field(description="Importe total de la factura en EUR")
    energy_amount_eur: float = Field(description="Importe total de energia en EUR")
    power_amount_eur: float = Field(description="Importe total de potencia en EUR")
    other_costs_eur: float = Field(default=0.0, description="Otros costes (impuestos, alquiler, etc.)")

    # Periodos
    power_periods: list[PowerPeriod] = Field(default_factory=list, description="Desglose de potencia por periodos")
    energy_periods: list[EnergyPeriod] = Field(default_factory=list, description="Desglose de energia por periodos")

    # Metadatos
    cups: Optional[str] = Field(default=None, description="Codigo CUPS del punto de suministro")
    billing_start_date: Optional[str] = Field(default=None, description="Fecha inicio de facturacion (YYYY-MM-DD)")
    billing_end_date: Optional[str] = Field(default=None, description="Fecha fin de facturacion (YYYY-MM-DD)")
    supply_address: Optional[str] = Field(default=None, description="Direccion de suministro")

    # Control
    notes: Optional[str] = Field(default=None, description="Notas del modelo sobre la extraccion")
    validation_status: str = Field(default="pending", description="Estado de validacion: ok, needs_review, error")
