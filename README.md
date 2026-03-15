# Electric Invoice Analyzer

A Streamlit web app that reads a Spanish electricity bill (PDF or image), extracts data using OpenAI's vision model, simulates costs across multiple tariffs, and generates a savings proposal — capped at 30%.

## Features

- **OCR extraction** — upload a PDF or photo of your electricity bill and let GPT-4o parse it
- **Data review & editing** — verify and manually correct extracted values before simulation
- **Tariff simulation** — compare your current cost against 5 simulated tariffs (P1/P2/P3 periods)
- **Savings proposal** — automatically selects the best tariff, capped at a 30% savings limit
- **HTML export** — download a clean, styled proposal document for your client

## Project Structure

```
├── app/
│   └── app.py            # Streamlit UI (4-screen flow)
├── core/
│   ├── schema.py         # Pydantic data models (InvoiceData, PowerPeriod, EnergyPeriod)
│   ├── extract.py        # OpenAI GPT-4o vision extraction
│   ├── validate.py       # Data validation and confidence scoring
│   ├── simulate.py       # Tariff simulation engine
│   ├── tariffs.py        # Predefined tariff table
│   └── formatters.py     # HTML proposal generator
├── requirements.txt
└── .env.example
```

## Getting Started

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd <repo-name>
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-...your-key-here...
```

### 3. Run the app

```bash
streamlit run app/app.py
```

The app will open at `http://localhost:8501`.

## How It Works

| Step | Screen | Description |
|------|--------|-------------|
| 1 | Upload | Upload a PDF or image of your electricity bill |
| 2 | Review | Inspect and edit the extracted data (periods, totals, metadata) |
| 3 | Compare | See all tariffs side by side with simulated costs and savings |
| 4 | Proposal | Get a detailed before/after breakdown and download the HTML report |

## Tariffs

Five simulated tariffs are included, covering common consumer profiles:

| Tariff | Profile |
|--------|---------|
| TARIFA_A_FIJA_EQUILIBRADA | Balanced consumption |
| TARIFA_B_DH_NOCTURNA | High off-peak consumption |
| TARIFA_C_SOLAR_AMIGABLE | Solar / valley-friendly |
| TARIFA_D_VERDE_SIMPLE | Flat energy price |
| TARIFA_E_FIJA | Fixed flat rate |

## Requirements

- Python 3.10+
- OpenAI API key (GPT-4o)

See `requirements.txt` for the full dependency list.

## License

MIT
