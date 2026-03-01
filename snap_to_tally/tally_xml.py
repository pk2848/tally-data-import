"""Module C: XML Construction – builds Tally-compliant XML voucher
envelopes from validated invoice data."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def _el(tag: str, text: str = "", **attribs: str) -> ET.Element:
    """Helper to create an Element with optional text and attributes."""
    elem = ET.Element(tag, attrib=attribs)
    if text:
        elem.text = str(text)
    return elem


def _sub(parent: ET.Element, tag: str, text: str = "", **attribs: str) -> ET.Element:
    elem = ET.SubElement(parent, tag, attrib=attribs)
    if text:
        elem.text = str(text)
    return elem


def _format_amount(value: float) -> str:
    """Return a Tally-style amount string (negative = debit for purchase)."""
    return f"{value:.2f}"


def _tally_date(iso_date: str) -> str:
    """Convert ISO ``YYYY-MM-DD`` to Tally date ``YYYYMMDD``."""
    return iso_date.replace("-", "")


def build_voucher_xml(
    invoice: dict[str, Any],
    *,
    party_ledger: str | None = None,
    item_ledger_map: dict[str, str] | None = None,
    sales_ledger: str = "Sales Account",
    purchase_ledger: str = "Purchase Account",
    cgst_ledger: str = "CGST",
    sgst_ledger: str = "SGST",
    igst_ledger: str = "IGST",
) -> str:
    """Build a TallyPrime-compatible XML import envelope for one voucher.

    Parameters
    ----------
    invoice:
        Parsed invoice dict (as returned by :func:`extractor.extract_invoice_data`).
    party_ledger:
        Resolved Tally ledger name for the party.  Falls back to
        ``invoice["party_name"]``.
    item_ledger_map:
        Optional dict mapping bill item names → resolved Tally stock-item
        names.  Falls back to the item names on the bill.
    sales_ledger / purchase_ledger:
        Default income / expense ledger names.
    cgst_ledger / sgst_ledger / igst_ledger:
        Tax ledger names.

    Returns
    -------
    str
        UTF-8 XML string ready to POST to Tally.
    """
    vtype = invoice.get("voucher_type", "Purchase")
    is_sales = vtype.lower() == "sales"
    tally_vtype = "Sales" if is_sales else "Purchase"

    party = party_ledger or invoice.get("party_name", "Unknown Party")
    date_str = _tally_date(invoice.get("date", "20240101"))

    item_map = item_ledger_map or {}

    # ── root envelope ────────────────────────────────────────────────
    envelope = _el("ENVELOPE")
    header = _sub(envelope, "HEADER")
    _sub(header, "TALLYREQUEST", "Import Data")

    body = _sub(envelope, "BODY")
    import_data = _sub(body, "IMPORTDATA")
    request_desc = _sub(import_data, "REQUESTDESC")
    _sub(request_desc, "REPORTNAME", "Vouchers")
    static_vars = _sub(request_desc, "STATICVARIABLES")
    _sub(static_vars, "SVCURRENTCOMPANY", "##SVCURRENTCOMPANY")

    request_data = _sub(import_data, "REQUESTDATA")
    tall_msg = _sub(request_data, "TALLYMESSAGE", xmlns_UDF="TallyUDF")

    voucher = _sub(tall_msg, "VOUCHER", VCHTYPE=tally_vtype, ACTION="Create")
    _sub(voucher, "DATE", date_str)
    _sub(voucher, "VOUCHERTYPENAME", tally_vtype)
    _sub(voucher, "VOUCHERNUMBER", invoice.get("invoice_no", ""))
    _sub(voucher, "PARTYLEDGERNAME", party)

    # ── item (inventory) entries ─────────────────────────────────────
    items = invoice.get("item_details", [])
    for item in items:
        inv_entry = _sub(voucher, "ALLINVENTORYENTRIES.LIST")
        resolved_name = item_map.get(item["name"], item["name"])
        _sub(inv_entry, "STOCKITEMNAME", resolved_name)

        qty = item.get("qty", 0)
        rate = item.get("rate", 0)
        amount = item.get("amount", qty * rate)

        _sub(inv_entry, "ACTUALQTY", str(qty))
        _sub(inv_entry, "RATE", f"{rate:.2f}")

        # Tally convention: positive for sales, negative for purchase
        sign = 1 if is_sales else -1
        _sub(inv_entry, "AMOUNT", _format_amount(sign * amount))

    # ── ledger (accounting) entries ──────────────────────────────────
    total = invoice.get("total_amount", 0)
    taxes = invoice.get("tax_amounts", {})
    cgst = taxes.get("cgst", 0)
    sgst = taxes.get("sgst", 0)
    igst = taxes.get("igst", 0)
    taxable = total - cgst - sgst - igst

    # Party ledger entry (debit for sales, credit for purchase)
    party_entry = _sub(voucher, "ALLLEDGERENTRIES.LIST")
    _sub(party_entry, "LEDGERNAME", party)
    party_sign = 1 if is_sales else -1
    _sub(party_entry, "AMOUNT", _format_amount(-party_sign * total))

    # Revenue / expense ledger entry
    rev_entry = _sub(voucher, "ALLLEDGERENTRIES.LIST")
    rev_ledger = sales_ledger if is_sales else purchase_ledger
    _sub(rev_entry, "LEDGERNAME", rev_ledger)
    _sub(rev_entry, "AMOUNT", _format_amount(party_sign * taxable))

    # Tax ledger entries
    for tax_amount, ledger in [
        (cgst, cgst_ledger),
        (sgst, sgst_ledger),
        (igst, igst_ledger),
    ]:
        if tax_amount:
            tax_entry = _sub(voucher, "ALLLEDGERENTRIES.LIST")
            _sub(tax_entry, "LEDGERNAME", ledger)
            _sub(tax_entry, "AMOUNT", _format_amount(party_sign * tax_amount))

    return ET.tostring(envelope, encoding="unicode", xml_declaration=True)
