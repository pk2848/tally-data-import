"""Streamlit-based verification dashboard for Snap-to-Tally."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from snap_to_tally.database import MappingDatabase
from snap_to_tally.extractor import extract_invoice_data
from snap_to_tally.matcher import match_name, MatchResult
from snap_to_tally.tally_client import (
    fetch_ledgers,
    fetch_stock_items,
    push_voucher_xml,
)
from snap_to_tally.tally_xml import build_voucher_xml


def _init_session_state() -> None:
    """Initialise Streamlit session-state defaults."""
    defaults = {
        "invoice_data": None,
        "match_results": [],
        "tally_url": "http://localhost:9000",
        "ledgers": [],
        "stock_items": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _sidebar() -> None:
    """Render configuration sidebar."""
    st.sidebar.title("⚙️ Settings")
    st.session_state["tally_url"] = st.sidebar.text_input(
        "Tally URL", value=st.session_state["tally_url"]
    )
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
    if gemini_key:
        st.session_state["gemini_key"] = gemini_key

    if st.sidebar.button("🔄 Sync Tally Masters"):
        try:
            url = st.session_state["tally_url"]
            st.session_state["ledgers"] = fetch_ledgers(url)
            st.session_state["stock_items"] = fetch_stock_items(url)
            st.sidebar.success(
                f"Loaded {len(st.session_state['ledgers'])} ledgers, "
                f"{len(st.session_state['stock_items'])} stock items."
            )
        except Exception as exc:
            st.sidebar.error(f"Tally sync failed: {exc}")


def _upload_section() -> None:
    """Bill upload and AI extraction section."""
    st.header("📤 Upload Bill Image")
    uploaded = st.file_uploader(
        "Choose an image (JPG / PNG)", type=["jpg", "jpeg", "png"]
    )
    if uploaded is not None and st.button("🔍 Extract Data"):
        with tempfile.NamedTemporaryFile(
            suffix=Path(uploaded.name).suffix, delete=False
        ) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name

        with st.spinner("Sending to Gemini AI …"):
            try:
                data = extract_invoice_data(
                    tmp_path,
                    api_key=st.session_state.get("gemini_key"),
                )
                st.session_state["invoice_data"] = data
                st.success("Extraction complete ✅")
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")


def _review_section(db: MappingDatabase) -> None:
    """Review extracted data and resolve item names."""
    data = st.session_state.get("invoice_data")
    if data is None:
        return

    st.header("📝 Review Extracted Data")
    st.json(data)

    st.subheader("Item Matching")
    items = data.get("item_details", [])
    tally_names = st.session_state.get("stock_items", [])
    results: list[MatchResult] = []

    for idx, item in enumerate(items):
        result = match_name(item["name"], tally_names, db=db)
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            st.text(f"Bill: {item['name']}")
        with col2:
            if result.method == "unresolved":
                options = ["-- select --"] + tally_names
                choice = st.selectbox(
                    f"Map item #{idx + 1}",
                    options,
                    key=f"item_map_{idx}",
                )
                if choice != "-- select --":
                    result = MatchResult(item["name"], choice, "manual", 100)
                    db.save(item["name"], choice)
            else:
                st.text(f"→ {result.tally_name} ({result.method})")
        with col3:
            st.text(f"Score: {result.score}")
        results.append(result)

    st.session_state["match_results"] = results


def _push_section() -> None:
    """Build XML and push to Tally."""
    data = st.session_state.get("invoice_data")
    results = st.session_state.get("match_results", [])
    if data is None or not results:
        return

    st.header("🚀 Push to Tally")
    item_map = {
        r.bill_name: r.tally_name
        for r in results
        if r.tally_name is not None
    }

    xml_str = build_voucher_xml(data, item_ledger_map=item_map)

    with st.expander("Preview XML"):
        st.code(xml_str, language="xml")

    if st.button("Push Voucher"):
        status = push_voucher_xml(xml_str, st.session_state["tally_url"])
        if status["success"]:
            st.success(status["message"])
        else:
            st.error(status["message"])


def main() -> None:
    """Entry-point for the Streamlit app."""
    st.set_page_config(page_title="Snap-to-Tally", page_icon="🧾", layout="wide")
    st.title("🧾 Snap-to-Tally")
    st.caption("Convert bill photos into TallyPrime vouchers with AI")

    _init_session_state()
    _sidebar()

    db = MappingDatabase()
    try:
        _upload_section()
        _review_section(db)
        _push_section()
    finally:
        db.close()


if __name__ == "__main__":
    main()
