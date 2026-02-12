# Plan de ejecución paso a paso (Streamlit + OpenAI OCR) — Facturas eléctricas y propuesta de ahorro

> Objetivo: construir una app web en **Streamlit** que lea una factura (PDF/imagen), extraiga campos con **OpenAI (OCR + parsing)**, simule el coste con **tarifas predefinidas**, y genere una **propuesta de ahorro** con un tope de **30%**.

---

## 0) Preparación rápida (1–2 horas)

### 0.1 Crear repo y entorno
2. Crea entorno virtual.
3. Instala dependencias mínimas:
   - `streamlit`, `pandas`, `pydantic`
   - `openai`
   - `pymupdf` (render de PDF a imágenes) o similar
   - `python-dotenv` (variables de entorno)
   - opcional: `reportlab` / `weasyprint` para exportar PDF

### 0.2 Configurar secretos
- Define `OPENAI_API_KEY` en `.env` o en secretos del despliegue.

### 0.3 Estructura de proyecto recomendada
app/
app.py
core/
tariffs.py
schema.py
extract.py
validate.py
simulate.py
formatters.py
assets/
samples/
tests/
README.md
.env.example


---

## 1) Definir el modelo de datos (la “verdad” del sistema)

### 1.1 Crear el Schema (JSON) de salida
Define un esquema **estricto** para que el modelo devuelva siempre lo mismo.
Campos mínimos:

- Totales:
  - `total_amount_eur`
  - `energy_amount_eur`
  - `power_amount_eur`

- Potencia (P1, P3):
  - `power_kw`, `days`, `price_eur_per_kw_day`, `amount_eur`

- Energía (P1, P2, P3):
  - `kwh`, `price_eur_per_kwh`, `amount_eur`

- Metadatos opcionales:
  - `cups`, `billing_start_date`, `billing_end_date`, `supply_address`

### 1.2 Definir tolerancias y reglas
- `otros_pagos = total - energia - potencia`
- Tolerancia “cuadre” (ejemplo):
  - `abs(energia - sum(energia_periodos)) <= 0.50`
  - `abs(potencia - sum(potencia_periodos)) <= 0.50`
- Si no cuadra:
  - marcar `validation_status = "needs_review"` y permitir edición manual.

**Entregable:** `core/schema.py` (Pydantic) y/o `schema.json`.

---

## 2) Crear la tabla de tarifas (inventadas pero realistas)

### 2.1 Definir tarifas demo
Crea un dataset local (lista dicts o CSV) con columnas:
- `name`
- `power_p1_eur_kw_day`
- `power_p3_eur_kw_day`
- `energy_p1_eur_kwh`
- `energy_p2_eur_kwh`
- `energy_p3_eur_kwh`

en base a la siguiente tabla:
### 📊 Tabla de tarifas simuladas

| Tarifa | Potencia P1 (€/kW día) | Potencia P3 (€/kW día) | Energía P1 (€/kWh) | Energía P2 (€/kWh) | Energía P3 (€/kWh) | Perfil recomendado |
|--------|------------------------|------------------------|--------------------|--------------------|--------------------|-------------------|
| TARIFA_A_FIJA_EQUILIBRADA | 0,110 | 0,090 | 0,145 | 0,120 | 0,095 | Consumo equilibrado |
| TARIFA_B_DH_NOCTURNA | 0,108 | 0,085 | 0,170 | 0,110 | 0,065 | Alto consumo en valle |
| TARIFA_C_SOLAR_AMIGABLE | 0,105 | 0,080 | 0,155 | 0,095 | 0,070 | Buen ajuste en llano/valle |
| TARIFA_D_VERDE_SIMPLE | 0,115 | 0,095 | 0,135 | 0,135 | 0,135 | Precio energía plano |

**Entregable:** `core/tariffs.py` con función:
- `get_tariffs() -> pd.DataFrame`

---

## 3) Implementar extracción con OpenAI (OCR + parsing a JSON)

### 3.1 Implementar pipeline de entrada
Caso A: **PDF**
- Convertir PDF a imágenes por página (para mejorar OCR en facturas escaneadas).
- Alternativa: si el PDF ya trae texto, aún así enviar imágenes para robustez.

Caso B: **Imagen**
- Enviar imagen directamente.

**Entregable:** `core/extract.py` con:
- `extract_invoice(file_bytes, file_type) -> InvoiceModel`

### 3.2 Prompt de extracción (clave del éxito)
Instrucciones recomendadas:
- “Devuelve SOLO JSON válido siguiendo el schema”
- “Usa P1/P2/P3 según aparezca; si no aparece un campo, usa null”
- “Devuelve números como float (punto decimal)”
- “Si hay conflicto entre totales y suma de periodos, prioriza los totales y anota en `notes`”
- “Si hay varias secciones (potencia, energía), busca tablas o líneas con periodos”

### 3.3 Manejo de errores de extracción
- Si la respuesta no valida:
  - reintentar 1 vez con un prompt de “corrección”
  - si falla, devolver error y pedir edición manual.

**Entregables:**
- extractor funcionando con 3–5 facturas diferentes en `samples/`.

---

## 4) Normalización y validación de datos extraídos

### 4.1 Normalizar formatos
- Convertir `None` a 0 donde aplique (solo en cálculos).
- Redondear importes a 2 decimales.
- Control de valores imposibles:
  - días <= 0
  - kWh negativos
  - €/kWh fuera de rango (ej. > 1.0) => warning

### 4.2 Validaciones internas
- Cuadre de energía y potencia con sus sumas por periodos.
- Cuadre total:
  - `total ≈ energia + potencia + otros`
- Generar un “score de confianza” (simple):
  - 100 si todo cuadra
  - -20 por cada discrepancia relevante

**Entregable:** `core/validate.py`:
- `validate(invoice) -> (invoice_clean, validation_report)`

---

## 5) Motor de simulación de tarifas

### 5.1 Cálculo por tarifa
Para cada tarifa:
- `potencia_sim = Σ (kW_periodo * días_periodo * precio_tarifa_kw_dia_periodo)`
- `energia_sim = Σ (kWh_periodo * precio_tarifa_kwh_periodo)`
- `total_sim = potencia_sim + energia_sim + otros_pagos`

### 5.2 Ahorro y regla del 30%
- `ahorro = total_actual - total_sim`
- `ahorro_pct = ahorro / total_actual`
- Filtrar candidatas:
  - `0 < ahorro_pct <= 0.30`

### 5.3 Selección de propuesta
- Si hay candidatas válidas: elegir mayor ahorro (sin pasar 30%).
- Si ninguna candidata:
  - si todas ahorran > 30%: elegir la más cercana a 30% por debajo (o capar a 30%)
  - si ninguna ahorra: mostrar “no se detecta ahorro” y recomendar tarifa actual o revisar datos.

**Entregable:** `core/simulate.py`:
- `simulate(invoice, tariffs_df) -> results_df, best_offer`

---

## 6) Construir la UI con Streamlit (MVP)

### 6.1 Pantalla 1 — Subida y vista previa
- `st.file_uploader`
- Preview:
  - si PDF: render de 1–2 páginas como imagen
  - si imagen: mostrar imagen

### 6.2 Pantalla 2 — Datos extraídos + edición
- Mostrar:
  - Totales (energía, potencia, total, otros)
  - Tablas por periodos (potencia y energía)
- Permitir edición:
  - `st.data_editor` para periodos
  - inputs para totales

### 6.3 Pantalla 3 — Comparativa de tarifas
- Tabla comparativa:
  - total simulado por tarifa
  - ahorro € y %
- Marcar la “recomendada” (la que cumple y maximiza ahorro).

### 6.4 Pantalla 4 — Propuesta final
- Resumen “Antes vs Después”
- Desglose:
  - energía (P1/P2/P3)
  - potencia (P1/P3)
  - otros pagos (constante)
- Texto comercial:
  - “Ahorro estimado: X€ (Y%)”

**Entregable:** `app/app.py` operativo (MVP).

---

## 7) Exportación (propuesta para el cliente)

### 7.1 Export HTML (rápido y suficiente)
- Generar HTML con tu logo, datos y tabla resumen.
- `st.download_button` para descargar.

### 7.2 Export PDF (opcional)
- Convertir HTML a PDF (WeasyPrint) o construir PDF (ReportLab).

**Entregable:** `core/formatters.py` + botón descarga.

---

## 8) Pruebas con facturas reales y hardening

### 8.1 Dataset de pruebas
- Reúne 20–30 facturas (diferentes comercializadoras y formatos):
  - PDF con texto
  - PDF escaneado
  - fotos móviles con sombras

### 8.2 Métricas simples
- % facturas con extracción completa
- % con cuadre sin edición
- tiempo medio de proceso

### 8.3 Mejoras típicas tras pruebas
- Prompt más específico por comercializadora
- Reintentos condicionados (solo si faltan campos)
- UI de “corrección guiada” cuando falte P2 o P3

**Entregable:** reporte de pruebas + mejoras aplicadas.

---

## 9) Despliegue

### 9.1 Opciones
- Streamlit Community Cloud (rápido)
- Docker + VPS (más control)

### 9.2 Seguridad mínima
- No guardar facturas por defecto
- Si guardas: cifrado + consentimiento + política de borrado
- Logs sin datos sensibles (solo IDs y errores)

**Entregable:** app accesible por URL + README de despliegue.

---
