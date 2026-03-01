"""Tally HTTP/XML client – fetch masters and push vouchers via the
TallyPrime XML-over-HTTP interface (default port 9000)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

_DEFAULT_URL = "http://localhost:9000"

# ── Request XML templates ────────────────────────────────────────────

_FETCH_LEDGERS_XML = """\
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>Ledger Collection</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="Ledger Collection" ISMODIFY="No">
            <TYPE>Ledger</TYPE>
            <FETCH>NAME</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

_FETCH_STOCK_ITEMS_XML = """\
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>Stock Item Collection</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="Stock Item Collection" ISMODIFY="No">
            <TYPE>StockItem</TYPE>
            <FETCH>NAME</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""


def _post_xml(xml_payload: str, tally_url: str = _DEFAULT_URL) -> ET.Element:
    """POST an XML payload to Tally and return the parsed response root."""
    resp = requests.post(
        tally_url,
        data=xml_payload.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8"},
        timeout=30,
    )
    resp.raise_for_status()
    return ET.fromstring(resp.text)


def _extract_names(root: ET.Element) -> list[str]:
    """Extract NAME text from a Tally collection response."""
    names: list[str] = []
    for name_el in root.iter("NAME"):
        text = (name_el.text or "").strip()
        if text:
            names.append(text)
    return names


# ── Public API ───────────────────────────────────────────────────────


def fetch_ledgers(tally_url: str = _DEFAULT_URL) -> list[str]:
    """Return the list of Ledger names from TallyPrime."""
    root = _post_xml(_FETCH_LEDGERS_XML, tally_url)
    return _extract_names(root)


def fetch_stock_items(tally_url: str = _DEFAULT_URL) -> list[str]:
    """Return the list of Stock Item names from TallyPrime."""
    root = _post_xml(_FETCH_STOCK_ITEMS_XML, tally_url)
    return _extract_names(root)


def push_voucher_xml(xml_payload: str, tally_url: str = _DEFAULT_URL) -> dict[str, Any]:
    """Push a voucher XML to Tally and return a status dict.

    Returns
    -------
    dict
        ``{"success": True/False, "message": "..."}``
    """
    try:
        root = _post_xml(xml_payload, tally_url)
        # Tally returns <LINEERROR> or <CREATED> elements
        created = root.findtext(".//CREATED", default="0").strip()
        errors = root.findtext(".//LINEERROR", default="").strip()

        if int(created) > 0:
            return {"success": True, "message": f"{created} voucher(s) created."}

        return {
            "success": False,
            "message": errors or "Unknown error from Tally.",
        }
    except requests.RequestException as exc:
        return {"success": False, "message": str(exc)}
