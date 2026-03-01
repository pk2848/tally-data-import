"""Tests for snap_to_tally.tally_xml – XML voucher construction."""

import xml.etree.ElementTree as ET

import pytest

from snap_to_tally.tally_xml import build_voucher_xml


_SAMPLE_INVOICE = {
    "voucher_type": "Purchase",
    "date": "2024-06-15",
    "invoice_no": "INV-001",
    "party_name": "ABC Suppliers",
    "gstin": "29ABCDE1234F1Z5",
    "item_details": [
        {
            "name": "Widget A",
            "qty": 10,
            "rate": 100.0,
            "amount": 1000.0,
            "gst_rate": 18,
            "hsn": "8471",
        },
        {
            "name": "Widget B",
            "qty": 5,
            "rate": 200.0,
            "amount": 1000.0,
            "gst_rate": 18,
            "hsn": "8472",
        },
    ],
    "tax_amounts": {"cgst": 180.0, "sgst": 180.0, "igst": 0},
    "total_amount": 2360.0,
}


class TestBuildVoucherXML:

    def test_returns_valid_xml(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        assert root.tag == "ENVELOPE"

    def test_purchase_voucher_type(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        vtype = root.findtext(".//VOUCHERTYPENAME")
        assert vtype == "Purchase"

    def test_sales_voucher_type(self):
        sales = {**_SAMPLE_INVOICE, "voucher_type": "Sales"}
        xml_str = build_voucher_xml(sales)
        root = ET.fromstring(xml_str)
        assert root.findtext(".//VOUCHERTYPENAME") == "Sales"

    def test_date_format(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        assert root.findtext(".//DATE") == "20240615"

    def test_party_ledger(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE, party_ledger="ABC Ltd.")
        root = ET.fromstring(xml_str)
        assert root.findtext(".//PARTYLEDGERNAME") == "ABC Ltd."

    def test_inventory_entries_count(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        inv_entries = root.findall(".//ALLINVENTORYENTRIES.LIST")
        assert len(inv_entries) == 2

    def test_item_name_mapping(self):
        xml_str = build_voucher_xml(
            _SAMPLE_INVOICE,
            item_ledger_map={"Widget A": "Tally Widget A"},
        )
        root = ET.fromstring(xml_str)
        names = [el.text for el in root.iter("STOCKITEMNAME")]
        assert "Tally Widget A" in names
        assert "Widget B" in names  # unmapped falls through

    def test_ledger_entries_present(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        ledger_entries = root.findall(".//ALLLEDGERENTRIES.LIST")
        # party + revenue + cgst + sgst = 4 (igst is 0 so excluded)
        assert len(ledger_entries) == 4

    def test_no_igst_entry_when_zero(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        ledger_names = [el.text for el in root.iter("LEDGERNAME")]
        assert "IGST" not in ledger_names

    def test_igst_entry_when_present(self):
        inv = {**_SAMPLE_INVOICE, "tax_amounts": {"cgst": 0, "sgst": 0, "igst": 360.0}}
        xml_str = build_voucher_xml(inv)
        root = ET.fromstring(xml_str)
        ledger_names = [el.text for el in root.iter("LEDGERNAME")]
        assert "IGST" in ledger_names

    def test_invoice_number(self):
        xml_str = build_voucher_xml(_SAMPLE_INVOICE)
        root = ET.fromstring(xml_str)
        assert root.findtext(".//VOUCHERNUMBER") == "INV-001"
