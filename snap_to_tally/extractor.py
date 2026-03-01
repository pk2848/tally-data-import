"""Module A: AI Extraction – uses Google Gemini 1.5 Flash to extract
structured invoice data from bill images/scans."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import google.generativeai as genai
from PIL import Image

# ── Gemini system prompt ────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are an expert Indian invoice / bill parser.
Given an image of a physical bill or scanned invoice, extract **all** data and
return it as a **single JSON object** with exactly the following structure.
Do NOT add commentary – output only the JSON.

{
  "voucher_type": "Sales" | "Purchase",
  "date": "YYYY-MM-DD",
  "invoice_no": "<string>",
  "party_name": "<string>",
  "gstin": "<string or null>",
  "item_details": [
    {
      "name": "<string>",
      "qty": <number>,
      "rate": <number>,
      "amount": <number>,
      "gst_rate": <number>,
      "hsn": "<string or null>"
    }
  ],
  "tax_amounts": {
    "cgst": <number>,
    "sgst": <number>,
    "igst": <number>
  },
  "total_amount": <number>
}

Rules:
- Use ISO 8601 date format (YYYY-MM-DD).
- If a field is absent on the bill, use null for strings or 0 for numbers.
- `gst_rate` should be in percent (e.g. 18 for 18%).
- `amount` is the line total *before* tax.
"""


def configure_gemini(api_key: str | None = None) -> None:
    """Configure the Gemini SDK with an API key."""
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError(
            "A Gemini API key is required. Pass it explicitly or set "
            "the GEMINI_API_KEY environment variable."
        )
    genai.configure(api_key=key)


def extract_invoice_data(
    image_path: str | Path,
    *,
    api_key: str | None = None,
    model_name: str = "gemini-1.5-flash",
) -> dict[str, Any]:
    """Send a bill image to Gemini and return structured invoice data.

    Parameters
    ----------
    image_path:
        Path to a JPG / PNG / PDF image of the bill.
    api_key:
        Optional Gemini API key (falls back to ``GEMINI_API_KEY`` env var).
    model_name:
        Gemini model to use (default ``gemini-1.5-flash``).

    Returns
    -------
    dict
        Parsed invoice data matching the JSON schema above.
    """
    configure_gemini(api_key)

    image = Image.open(image_path)
    model = genai.GenerativeModel(model_name)

    response = model.generate_content(
        [_SYSTEM_PROMPT, image],
    )

    raw_text: str = response.text.strip()

    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini returned non-JSON output:\n{raw_text}"
        ) from exc

    return data
