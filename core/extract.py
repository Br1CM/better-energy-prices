import base64
import json
import io

import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv

from core.schema import InvoiceData

load_dotenv()

EXTRACTION_PROMPT = """\
Eres un experto en lectura de facturas electricas espanolas.
Analiza la imagen de la factura y extrae los datos en formato JSON con esta estructura exacta:

{
  "total_amount_eur": float,
  "energy_amount_eur": float,
  "power_amount_eur": float,
  "other_costs_eur": float,
  "power_periods": [
    {"period": "P1"|"P2"|"P3", "power_kw": float, "days": int, "price_eur_per_kw_day": float, "amount_eur": float}
  ],
  "energy_periods": [
    {"period": "P1"|"P2"|"P3", "kwh": float, "price_eur_per_kwh": float, "amount_eur": float}
  ],
  "cups": string | null,
  "billing_start_date": "YYYY-MM-DD" | null,
  "billing_end_date": "YYYY-MM-DD" | null,
  "supply_address": string | null,
  "notes": string | null
}

Reglas:
- Devuelve SOLO JSON valido, sin texto adicional.
- Usa P1, P2, P3 segun aparezcan en la factura.
- Si un campo no aparece, usa null.
- Numeros como float con punto decimal (ej: 123.45).
- IMPORTANTE: Los precios unitarios (price_eur_per_kwh y price_eur_per_kw_day) deben conservar TODOS los decimales que aparezcan en la factura. Por ejemplo, si el precio es 0,082614 EUR/kWh, devuelve 0.082614. No redondees los precios unitarios.
- other_costs_eur = total_amount_eur - energy_amount_eur - power_amount_eur
- Si hay conflicto entre totales y suma de periodos, prioriza los totales y anotalo en "notes".
- Busca tablas o lineas con desglose de periodos para potencia y energia.
"""

CORRECTION_PROMPT = """\
El JSON extraido anteriormente no es valido. Revisa la imagen de nuevo y devuelve un JSON corregido
con la misma estructura. Asegurate de que todos los campos numericos sean float y las listas esten completas.
Devuelve SOLO JSON valido.
"""


def _pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """Convert PDF pages to PNG images."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _encode_image(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def _build_messages(image_b64_list: list[str], prompt: str) -> list[dict]:
    """Build OpenAI messages with images."""
    content = [{"type": "text", "text": prompt}]
    for img_b64 in image_b64_list:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"},
        })
    return [{"role": "user", "content": content}]


def extract_invoice(file_bytes: bytes, file_type: str) -> InvoiceData:
    """Extract invoice data from PDF or image using GPT-4o.

    Args:
        file_bytes: Raw file bytes.
        file_type: MIME type (e.g. "application/pdf", "image/png", "image/jpeg").

    Returns:
        Parsed InvoiceData model.
    """
    client = OpenAI()

    # Convert to images
    if file_type == "application/pdf":
        images = _pdf_to_images(file_bytes)
    else:
        images = [file_bytes]

    image_b64_list = [_encode_image(img) for img in images]

    # First attempt
    messages = _build_messages(image_b64_list, EXTRACTION_PROMPT)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=4096,
        temperature=0.0,
    )

    raw_json = response.choices[0].message.content

    try:
        data = json.loads(raw_json)
        return InvoiceData(**data)
    except Exception:
        pass

    # Retry with correction prompt
    messages.append({"role": "assistant", "content": raw_json})
    messages.append({"role": "user", "content": CORRECTION_PROMPT})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=4096,
        temperature=0.0,
    )

    raw_json = response.choices[0].message.content
    data = json.loads(raw_json)
    return InvoiceData(**data)
