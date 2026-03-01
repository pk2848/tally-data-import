# Snap-to-Tally

AI-powered tool that converts physical bill photos/scans into TallyPrime Sales and Purchase vouchers.

## Features

| Module | Description |
|--------|-------------|
| **AI Extraction** | Send bill images to Google Gemini 1.5 Flash and receive structured invoice JSON. |
| **Master Matching** | Resolve bill item names to Tally master names via exact → fuzzy → history → manual matching. |
| **XML Construction** | Build Tally-compliant XML voucher envelopes ready for import. |
| **Tally Client** | Fetch ledgers/stock items and push vouchers over Tally's XML-HTTP interface (port 9000). |
| **Streamlit Dashboard** | Upload bills, review extracted data, resolve item names, and push to Tally in one UI. |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Set your Gemini API key
export GEMINI_API_KEY="your-key-here"

# Run the dashboard
streamlit run snap_to_tally/app.py

# Run tests
pytest
```

## Architecture

```
snap_to_tally/
├── __init__.py        # Package metadata
├── extractor.py       # Module A – Gemini AI extraction
├── database.py        # SQLite historical mapping store
├── matcher.py         # Module B – Fuzzy + history matching
├── tally_client.py    # Tally HTTP/XML client
├── tally_xml.py       # Module C – XML voucher builder
└── app.py             # Streamlit verification dashboard
```

## Tech Stack

- **Python 3.10+**
- **Google Gemini 1.5 Flash** – OCR & data extraction
- **thefuzz** – Levenshtein distance fuzzy matching
- **SQLite** – Local mapping persistence
- **Streamlit** – Web dashboard
- **requests** – Tally HTTP communication
