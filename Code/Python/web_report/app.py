"""Streamlit: panoramica, Conto Economico e dettaglio del dataset validato."""
import math
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from charts import contribution_chart, monthly_chart, waterfall
from data_model import (COUNTRIES, DETAIL_COLUMNS, DIMENSIONS, MONTH_COLUMNS, MONTH_NAMES,
                        WEB_DIR, csv_bytes, filter_indices, fmt, load_snapshot,
                        snapshot_signature, summary)

st.set_page_config(page_title="Sorgenia Trading | Business case", page_icon="↗", layout="wide")
st.markdown("""<style>
html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif;}
.stApp {background:#F7F9F8;color:#142B2A;} .block-container {max-width:1440px;padding-top:2.5rem;padding-bottom:3rem;}
h1,h2,h3 {font-family:'Manrope',sans-serif!important;letter-spacing:-.04em!important;}
h1 {font-size:2.5rem!important;font-weight:800!important;} h3 {font-size:1.05rem!important;}
[data-testid="stSidebar"] {background:#FFF;border-right:1px solid #E3EBE6;}
[data-testid="stSidebar"] .block-container {padding-top:1.5rem;}
.brand {font-family:Manrope,sans-serif;font-size:1.4rem;font-weight:800;letter-spacing:-.05em;color:#173C37;}
.brand span {color:#168365;} .eyebrow {font-size:.7rem;font-weight:700;letter-spacing:.16em;color:#658077;margin-bottom:.35rem;}
.subtle {color:#6C817B;font-size:.9rem;} .divider {height:1px;background:#DFE9E3;margin:1.3rem 0;}
.pill {display:inline-block;background:#E7F3EB;color:#27654C;border:1px solid #CFE5D7;border-radius:20px;padding:.25rem .65rem;font-size:.73rem;margin:0 .25rem .3rem 0;}
.filter-chip {display:inline-block;color:#4B625B;border-radius:6px;background:#EEF3EF;padding:.23rem .5rem;font-size:.72rem;margin:0 .25rem .3rem 0;}
[data-testid="stMetric"] {background:white;border:1px solid #DFE9E3;border-radius:12px;padding:18px 20px;margin-bottom:12px;min-height:115px;}
[data-testid="stMetricLabel"] {color:#6C817B;font-size:.8rem;}
[data-testid="stMetricValue"] {font-family:'Manrope',sans-serif;font-size:1.8rem;color:#173C37;}
.hero-kpi {border:1px solid #173C37;background:#173C37;color:white;border-radius:14px;padding:25px 28px;margin-bottom:1.3rem;}
.hero-kpi .label {color:#B4D2C5;font-size:.8rem;}.hero-kpi .value {font-family:'Manrope','Segoe UI',sans-serif;font-size:2.6rem;font-weight:700;letter-spacing:-.04em;}
.footer {font-size:.73rem;color:#7B8D85;border-top:1px solid #DFE9E3;margin-top:2rem;padding-top:1rem;}
div.stButton>button,div.stDownloadButton>button {border-radius:8px;}
@media(max-width:700px){.block-container{padding:1rem!important;}h1{font-size:1.8rem!important;}.hero-kpi .value{font-size:2rem;}[data-testid="stMetricValue"]{font-size:1.4rem;}}
</style>""", unsafe_allow_html=True)

DATA_DIR = WEB_DIR / "data"


@st.cache_resource(show_spinner="Caricamento del dataset validato…", max_entries=1)
def bundle(signature):
    return load_snapshot(DATA_DIR)


@st.cache_data(show_spinner=False, max_entries=8)
def select(signature, selections):
    snapshot = bundle(signature)
    indices = filter_indices(snapshot.rows, selections)
    return indices, summary([snapshot.rows[i] for i in indices]) if indices else None


def label(field, value):
    if value is None or value == "":
        return "Non disponibile"
    if field == "market":
        return COUNTRIES.get(value, value)
    if field == "mese":
        return MONTH_NAMES[value - 1]
    if field == "purpose":
        return {"Buy": "Buy · Acquisto", "Sell": "Sell · Vendita"}.get(value, value)
    return str(value)


try:
    signature = snapshot_signature(DATA_DIR)
    snapshot = bundle(signature)
except (ValueError, OSError, KeyError) as exc:
    st.error(f"Dataset non disponibile o non valido: {exc}")
    st.info("Preparare nuovamente lo snapshot con prepare_data.py.")
    st.stop()

if st.session_state.get("dataset_id") != snapshot.manifest["dataset_id"]:
    for key in list(st.session_state):
        if key.startswith("filter_"):
            del st.session_state[key]
    st.session_state.dataset_id = snapshot.manifest["dataset_id"]

with st.sidebar:
    st.markdown('<div class="brand">sorgenia<span> trading.</span></div><div class="subtle">Business case · Energy markets</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    page = st.radio("Navigazione", ["Panoramica", "Conto Economico", "Dettaglio e controlli"], label_visibility="collapsed", key="navigation")
    st.markdown('<div class="divider"></div><div class="eyebrow">PERIMETRO DI ANALISI</div>', unsafe_allow_html=True)
    def reset():
        for key, values in zip(DIMENSIONS, snapshot.catalog):
            st.session_state[f"filter_{key}"] = list(values)
        st.session_state["detail_page"] = 1
    st.button("Ripristina filtri", on_click=reset, width="stretch")
    selections = []
    titles = ("Anno", "Mese", "Paese", "Counterparty", "Operazione", "Business unit", "Commodity")
    for field, title, values in zip(DIMENSIONS, titles, snapshot.catalog):
        key = f"filter_{field}"
        if key not in st.session_state:
            st.session_state[key] = list(values)
        selected = st.multiselect(title, values, key=key, format_func=lambda value, f=field: label(f, value))
        selections.append(tuple(selected))
    st.caption("I filtri si applicano a tutte le viste.")

selections = tuple(selections)
if st.session_state.get("export_selection") != (snapshot.manifest["dataset_id"], selections):
    st.session_state.pop("detail_export", None)
    st.session_state["export_selection"] = (snapshot.manifest["dataset_id"], selections)
indices, results = select(signature, selections)
st.markdown('<div class="eyebrow">SORG­ENIA TRADING / REPORT INTERATTIVO</div>', unsafe_allow_html=True)
st.title(page)
st.markdown('<div class="subtle">Profili di consegna, benchmark di mercato e risultato economico.</div>', unsafe_allow_html=True)
from html import escape
chips = []
for field, selected, available in zip(DIMENSIONS, selections, snapshot.catalog):
    if len(selected) != len(available):
        chips.append(f'<span class="filter-chip">{escape(dict(zip(DIMENSIONS, titles))[field])}: {escape(", ".join(label(field, v) for v in selected) or "nessuno")}</span>')
period = snapshot.manifest["period"]
st.markdown(f'<span class="pill">Snapshot validato · {period["from"][:4]}</span>' + "".join(chips), unsafe_allow_html=True)
st.caption(f"{fmt(len(indices), 0)} righe di profilo selezionate su {fmt(len(snapshot.rows), 0)} · Valuta EUR · Volumi ENERGY in MWh")
if not indices:
    st.info("Nessun dato per la selezione corrente. Modificare o ripristinare i filtri.")
    st.stop()

stats = results["statistics"]
if stats["n_energy_incomplete"]:
    st.warning(f"Dati ENERGY incompleti: {stats['n_energy_incomplete']} righe senza P&L calcolabile. I totali completi restano non disponibili.")
def metric_value(name, suffix=" €"):
    value = stats[name]
    if value is None:
        return "Non applicabile" if stats["n_energy"] == 0 and name in ("pnl", "volume_energy") else "Dati incompleti"
    return fmt(value, 0 if name == "volume_energy" else 2) + suffix

if page == "Panoramica":
    pnl_text = escape(metric_value("pnl"))
    st.markdown(f'<div class="hero-kpi"><div class="label">P&amp;L ENERGY rispetto alle curve</div><div class="value">{pnl_text}</div><div class="label">Scostamento del prezzo contrattuale dal benchmark di mercato</div></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for col, key, title in zip(cols, ("known_margin", "revenue_energy", "revenue_service"),
                                ("Margine di contribuzione · dataset", "Ricavi energia", "Ricavi servizi")):
        col.metric(title, metric_value(key))
    cols = st.columns(3)
    cols[0].metric("Costi di acquisto energia", metric_value("cost_energy"))
    cols[1].metric("Volume ENERGY", metric_value("volume_energy", " MWh"))
    cols[2].metric("Righe ENERGY con P&L calcolabile", fmt(stats["n_calculable"], 0))
    if stats["n_energy"]:
        st.subheader("Andamento mensile del P&L")
        st.plotly_chart(monthly_chart(results["monthly"]), use_container_width=True, config={"displayModeBar": False})
        left, right = st.columns(2)
        with left:
            st.subheader("Contributo per paese")
            st.plotly_chart(contribution_chart(results["markets"], country=True), use_container_width=True, config={"displayModeBar": False})
        with right:
            st.subheader("Contributo per controparte")
            st.plotly_chart(contribution_chart(results["counterparties"]), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("P&L ENERGY non applicabile: il perimetro selezionato contiene solo servizi o commodity diverse da ENERGY.")

elif page == "Conto Economico":
    st.caption("Bozza gestionale riferita al dataset e ai filtri selezionati.")
    left, right = st.columns([1, 2])
    with left:
        st.metric("Margine di contribuzione · dataset", metric_value("known_margin"))
        total_revenue = stats["revenue_energy"] + stats["revenue_service"] if stats["revenue_energy"] is not None and stats["revenue_service"] is not None else None
        table = [("Ricavi da vendita di energia", stats["revenue_energy"]), ("Ricavi da servizi", stats["revenue_service"]),
                 ("Totale ricavi", total_revenue), ("Costi di acquisto di energia", stats["cost_energy"]),
                 ("Margine di contribuzione", stats["known_margin"])]
        st.dataframe(pd.DataFrame({"Voce": [k for k, _ in table], "EUR": [fmt(v) if v is not None else "Dati incompleti" for _, v in table]}),
                     hide_index=True, width="stretch")
    with right:
        if stats["known_margin"] is not None:
            st.plotly_chart(waterfall(stats), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Il margine completo del perimetro non è disponibile per i dati selezionati.")
    st.markdown("**Criterio:** ENERGY Sell → ricavi energia; SERVICE_POWER Sell → ricavi servizi; ENERGY Buy → costi di acquisto con segno invertito rispetto a IMPORTO.")
    st.caption("Margine = ricavi energia + ricavi servizi − costi energia. Il P&L rispetto alle curve misura lo scostamento dal benchmark e viene presentato separatamente.")

else:
    cols = st.columns(4)
    for col, name, title in zip(cols, ("n_calculable", "n_not_applicable", "n_problem", "n_energy_incomplete"),
                               ("P&L calcolabile", "P&L non applicabile", "Righe con problemi", "ENERGY incompleta")):
        col.metric(title, fmt(stats[name], 0))
    st.subheader("Risultati mensili")
    monthly_frame = pd.DataFrame(results["monthly"])
    st.dataframe(monthly_frame, hide_index=True, width="stretch",
                 column_config={name: st.column_config.NumberColumn(format="%.2f") for name in ("importo_total", "pnl_energy", "market_value_signed_energy", "importo_service_power")})
    st.download_button("Scarica il mensile filtrato", csv_bytes(results["monthly"], MONTH_COLUMNS),
                       "monthly_summary_filtered.csv", "text/csv", key="monthly_download")
    st.subheader("Profili orari")
    detail_rows = [snapshot.rows[i] for i in indices]
    controls = st.columns(4)
    dates = sorted({row["delivery_date"] for row in detail_rows if row["delivery_date"]})
    if st.session_state.get("detail_date") not in [None] + dates:
        st.session_state["detail_date"] = None
    chosen_date = controls[0].selectbox("Data di consegna", [None] + dates, format_func=lambda d: "Tutte le date" if d is None else d.strftime("%d/%m/%Y"), key="detail_date")
    hours = sorted({row["delivery_hour"] for row in detail_rows if row["delivery_hour"] is not None})
    if st.session_state.get("detail_hour") not in [None] + hours:
        st.session_state["detail_hour"] = None
    chosen_hour = controls[1].selectbox("Ora di consegna", [None] + hours, format_func=lambda h: "Tutte le ore" if h is None else str(h), key="detail_hour")
    order_by = controls[2].selectbox("Ordina per", ["Consegna", "pnl", "IMPORTO", "VOLUME", "counterparty", "deal_row_id"], key="detail_order")
    descending = controls[3].checkbox("Ordine decrescente", key="detail_descending")
    detail_rows = [row for row in detail_rows if (chosen_date is None or row["delivery_date"] == chosen_date) and (chosen_hour is None or row["delivery_hour"] == chosen_hour)]
    if order_by == "Consegna":
        sort_keys = ("delivery_date", "delivery_hour", "market", "counterparty", "purpose", "deal_row_id")
    else:
        sort_keys = (("importo_value" if order_by == "IMPORTO" else "volume_value" if order_by == "VOLUME" else order_by), "deal_row_id")
    complete = [r for r in detail_rows if all(r[k] is not None for k in sort_keys)]
    missing = [r for r in detail_rows if any(r[k] is None for k in sort_keys)]
    complete.sort(key=lambda r: tuple(r[k] for k in sort_keys), reverse=descending)
    detail_rows = complete + missing
    st.caption("Data e ora limitano solo questa tabella e il relativo download. Gli indicatori sopra mantengono i filtri globali.")
    full = st.checkbox("Mostra tutte le colonne originali e tecniche", key="full_columns")
    basic = ["DATA", "ORA", "market", "counterparty", "purpose", "business_unit", "commodity", "volume_value", "contract_price", "market_price", "pnl", "deal_row_id"]
    columns = DETAIL_COLUMNS if full else basic
    pages = max(1, math.ceil(len(detail_rows) / 100))
    if st.session_state.get("detail_page", 1) > pages:
        st.session_state.detail_page = 1
    page_number = st.number_input("Pagina", min_value=1, max_value=pages, value=1, step=1, key="detail_page")
    start = (int(page_number) - 1) * 100
    frame = pd.DataFrame([{k: r[k] for k in columns} for r in detail_rows[start:start + 100]], columns=columns)
    if frame.empty:
        st.info("Nessun profilo orario per data e ora selezionate.")
    else:
        st.dataframe(frame, hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="%.2f") for k in ("contract_price", "market_price", "pnl", "volume_value") if k in columns})
    st.caption(f"Pagina {page_number} di {pages} · {fmt(len(detail_rows), 0)} righe. deal_row_id e un identificativo tecnico di riga, non di contratto.")
    if st.button("Prepara CSV di tutte le righe selezionate", key="prepare_download"):
        st.session_state["detail_export"] = (selections, chosen_date, chosen_hour, order_by, descending, csv_bytes(detail_rows, DETAIL_COLUMNS))
    export = st.session_state.get("detail_export")
    if export and export[:5] == (selections, chosen_date, chosen_hour, order_by, descending):
        st.download_button("Scarica il dettaglio filtrato completo", export[5], "deals_enriched_pnl_filtered.csv", "text/csv", key="detail_download")
    with st.expander("Metodo e integrita del dataset"):
        st.write("Join data + ora + mercato, direzione +1 Sell / −1 Buy, P&L = IMPORTO − direction × VOLUME × market_price. I prezzi negativi mantengono il segno; SERVICE_POWER non viene valutato contro la curva ENERGY.")
        st.write("Snapshot verificato tramite SHA-256 e riconciliato con i risultati R e Python. Le ore 25 sono conservate. I costi e ricavi sono classificati per purpose e commodity.")
        st.code(snapshot.manifest["dataset_id"], language=None)

st.markdown(f'<div class="footer">Sorgenia Trading · Business case · Snapshot {snapshot.manifest["dataset_id"][:12]} · EUR / MWh come ipotesi del dataset</div>', unsafe_allow_html=True)
