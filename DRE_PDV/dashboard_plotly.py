"""
DRE PDV Dashboard — Dark SaaS Premium (FULL VERSION)
Deploy: gunicorn app:server
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dash_table, dcc, html

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "dre_pdv_mensal_consolidado_com_acoes.csv"

# ─── App Initialization ───────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    update_title=None,
    suppress_callback_exceptions=True
)

# VARIÁVEL GUNICORN:
server = app.server

# ─── Plotly dark template ──────────────────────────────────────────────────────
DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#7b8ea8", size=11),
    margin=dict(l=10, r=10, t=10, b=10),
    colorway=["#00d4ff", "#00e5a0", "#9b5de5", "#f4a026", "#ff4d6d", "#3dd6f5"],
)

GRID = dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)")

DARK_LEGEND = dict(
    bgcolor="rgba(14,20,32,0.8)",
    bordercolor="rgba(255,255,255,0.07)",
    borderwidth=1,
    font=dict(size=11, color="#7b8ea8"),
)

REGION_COLORS = {
    "Sudeste":     "#00d4ff",
    "Sul":         "#00e5a0",
    "Nordeste":    "#f4a026",
    "Centro-Oeste":"#9b5de5",
    "Norte":       "#ff4d6d",
}

# ─── Data Loading ──────────────────────────────────────────────────────────────
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["mes"] = pd.to_datetime(df["mes"])

    bool_cols = ["flag_margem_abaixo_10", "flag_queda_receita_20", "flag_ebitda_negativo"]
    for col in bool_cols:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.lower().map({"true": True, "false": False})
            df[col] = df[col].fillna(False).astype(bool)

    num_cols = [
        "receita_bruta", "receita_liquida", "lucro_bruto", "lucro_operacional",
        "ebitda", "lucro_liquido", "devolucoes", "score_alerta",
        "despesas_variaveis", "despesas_fixas", "cmv", "impostos",
        "comissoes", "depreciacao_amortizacao", "resultado_financeiro",
        "margem_bruta", "margem_operacional", "margem_ebitda", "margem_liquida",
        "var_receita_vs_mes_anterior",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["regiao"] = df["regiao"].fillna("Não informado")
    df["canal"]  = df["canal"].fillna("Não informado")
    return df


DF = load_data(DATA_PATH)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def brl(v: float) -> str:
    s = f"R$ {abs(v):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{s}" if v < 0 else s


def pct(v: float) -> str:
    return f"{v * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def delta_class(v: float) -> str:
    if v > 0.005:  return "delta-up"
    if v < -0.005: return "delta-down"
    return "delta-flat"


def apply_filters(df: pd.DataFrame, regioes, canais, start, end, pdvs=None) -> pd.DataFrame:
    out = df.copy()
    if regioes:  out = out[out["regiao"].isin(regioes)]
    if canais:   out = out[out["canal"].isin(canais)]
    if pdvs:     out = out[out["id_pdv"].isin(pdvs)]
    if start:    out = out[out["mes"] >= pd.to_datetime(start)]
    if end:      out = out[out["mes"] <= pd.to_datetime(end)]
    return out


# ─── Layout Helpers ────────────────────────────────────────────────────────────
def kpi_card(card_id: str, icon: str, label: str, dot_color: str = "cyan") -> html.Div:
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(icon, className="kpi-icon"),
            html.Div(label, className="kpi-label"),
            html.Div(id=f"kpi-{card_id}", className="kpi-value", children="—"),
        ],
    )


def section_title(text: str, dot: str = "cyan") -> html.Div:
    return html.Div(
        className="chart-card-title",
        children=[html.Span(className=f"dot dot-{dot}"), text],
    )


MESES     = sorted(DF["mes"].dt.strftime("%Y-%m-%d").unique())
REGIOES   = sorted(DF["regiao"].unique())
CANAIS    = sorted(DF["canal"].unique())
ALL_PDVS  = sorted(DF["id_pdv"].unique())


# INCIPOREI O CSS AQUI DENTRO 

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

:root {
  --bg-base:      #080c14;
  --bg-surface:   #0e1420;
  --bg-elevated:  #131b2a;
  --bg-hover:     #1a2438;
  --border:       rgba(255,255,255,0.07);
  --border-glow:  rgba(0,212,255,0.25);
  --text:         #e8edf5;
  --text-muted:   #7b8ea8;
  --text-dim:     #4a5a72;
  --accent-cyan:  #00d4ff;
  --accent-green: #00e5a0;
  --accent-purple:#9b5de5;
  --accent-amber: #f4a026;
  --accent-red:   #ff4d6d;
  --glow-cyan:    0 0 20px rgba(0,212,255,0.25), 0 0 60px rgba(0,212,255,0.08);
  --glow-green:   0 0 20px rgba(0,229,160,0.25), 0 0 60px rgba(0,229,160,0.08);
  --shadow-card:  0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.04) inset;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  background: var(--bg-base);
  color: var(--text);
  font-family: 'DM Sans', 'Segoe UI', sans-serif;
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
}

/* ── Scrollbar ─────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--bg-hover); border-radius: 4px; }

/* ── App Shell ─────────────────────────────── */
.app-shell {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px 24px;
}

/* ── Hero Header ───────────────────────────── */
.hero {
  position: relative;
  overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 22px 28px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0,212,255,0.06) 0%, transparent 50%, rgba(155,93,229,0.06) 100%);
  pointer-events: none;
}
.hero::after {
  content: '';
  position: absolute;
  top: -40px; left: -40px;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%);
  pointer-events: none;
}
.hero-left { position: relative; z-index: 1; }
.page-title {
  font-family: 'Syne', 'Trebuchet MS', sans-serif;
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #ffffff 30%, var(--accent-cyan) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.page-subtitle {
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 4px;
  font-weight: 400;
}
.hero-right {
  position: relative; z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}
.hero-live {
  display: flex;
  align-items: center;
  gap: 5px;
}
.hero-signature {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.sig-name {
  font-family: 'Syne', sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.3px;
  line-height: 1.1;
}
.sig-role {
  font-size: 11px;
  color: var(--accent-cyan);
  font-weight: 500;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  opacity: 0.85;
}
.live-dot {
  width: 8px; height: 8px;
  background: var(--accent-green);
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
  box-shadow: 0 0 8px var(--accent-green);
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
.live-label { color: var(--accent-green); font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }

/* ── Filters Bar ───────────────────────────── */
.filters-bar {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 18px;
  margin-bottom: 16px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  box-shadow: var(--shadow-card);
}
.filter-item label {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 6px;
}

/* ── Native month inputs ───────────────────── */
.date-range-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-elevated);
  border: 1.5px solid rgba(0,212,255,0.2);
  border-radius: 10px;
  padding: 0 10px;
  height: 38px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.date-range-wrapper:focus-within {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(0,212,255,0.10);
}
.dark-month-input {
  flex: 1;
  background: transparent !important;
  border: none !important;
  outline: none !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  min-width: 0;
  color-scheme: dark;
}
.dark-month-input::-webkit-calendar-picker-indicator {
  filter: invert(0.6) sepia(1) saturate(2) hue-rotate(170deg);
  opacity: 0.6;
  cursor: pointer;
}
.dark-month-input::-webkit-calendar-picker-indicator:hover { opacity: 1; }
.date-arrow {
  color: var(--text-dim);
  font-size: 13px;
  flex-shrink: 0;
  user-select: none;
}

/* ── dcc.Dropdown dark override — Dash 2/3 legacy + Dash 4 classes ── */

/* ---- CLOSED STATE (trigger button) ---- */
/* Dash 4 */
.dark-dropdown .dash-dropdown-trigger {
  background: var(--bg-elevated) !important;
  border: 1.5px solid rgba(0,212,255,0.2) !important;
  border-radius: 10px !important;
  min-height: 38px !important;
  padding: 0 10px !important;
  display: flex !important;
  align-items: center !important;
  cursor: pointer !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  gap: 6px !important;
}
/* Dash 2/3 legacy */
.dark-dropdown .Select-control {
  background: var(--bg-elevated) !important;
  border: 1.5px solid rgba(0,212,255,0.2) !important;
  border-radius: 10px !important;
  min-height: 38px !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
.dark-dropdown .Select-control:hover,
.dark-dropdown .dash-dropdown-trigger:hover {
  border-color: var(--accent-cyan) !important;
}
.dark-dropdown[data-dash-is-loading] .dash-dropdown-trigger,
.dark-dropdown .dash-dropdown-trigger:focus-within,
.dark-dropdown.is-open .Select-control {
  border-color: var(--accent-cyan) !important;
  box-shadow: 0 0 0 3px rgba(0,212,255,0.10) !important;
  outline: none !important;
}

/* ---- PLACEHOLDER & VALUE TEXT ---- */
.dark-dropdown .dash-dropdown-value,
.dark-dropdown .Select-value-label,
.dark-dropdown .Select-placeholder {
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
}
.dark-dropdown .dash-dropdown-placeholder,
.dark-dropdown .Select-placeholder { color: var(--text-dim) !important; }

/* ---- MULTI-VALUE TAGS ---- */
.dark-dropdown .dash-dropdown-value-item,
.dark-dropdown .Select-value {
  background: rgba(0,212,255,0.10) !important;
  border: 1px solid rgba(0,212,255,0.25) !important;
  border-radius: 6px !important;
  color: var(--accent-cyan) !important;
  font-size: 12px !important;
  font-family: 'DM Sans', sans-serif !important;
  padding: 2px 6px !important;
}
.dark-dropdown .Select-value-icon {
  border-right: 1px solid rgba(0,212,255,0.25) !important;
  color: var(--accent-cyan) !important;
}
.dark-dropdown .Select-value-icon:hover { background: rgba(255,77,109,0.15) !important; color: var(--accent-red) !important; }

/* Count badge (+N) */
.dark-dropdown .dash-dropdown-value-count {
  background: rgba(0,212,255,0.15) !important;
  border: 1px solid rgba(0,212,255,0.3) !important;
  border-radius: 6px !important;
  color: var(--accent-cyan) !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  padding: 1px 6px !important;
}

/* ---- ICONS ---- */
.dark-dropdown .dash-dropdown-clear,
.dark-dropdown .dash-dropdown-trigger-icon,
.dark-dropdown .Select-clear-zone,
.dark-dropdown .Select-arrow-zone {
  color: var(--text-dim) !important;
  opacity: 0.7 !important;
  flex-shrink: 0 !important;
  transition: color 0.15s, opacity 0.15s !important;
}
.dark-dropdown .dash-dropdown-clear:hover,
.dark-dropdown .Select-clear-zone:hover { color: var(--accent-red) !important; opacity: 1 !important; }
.dark-dropdown .dash-dropdown-trigger-icon,
.dark-dropdown .Select-arrow { opacity: 0.5 !important; }

/* ---- OPEN DROPDOWN PANEL ---- */
/* Dash 4 */
.dark-dropdown .dash-dropdown-content {
  background: var(--bg-elevated) !important;
  border: 1px solid rgba(0,212,255,0.22) !important;
  border-radius: 10px !important;
  box-shadow: 0 14px 44px rgba(0,0,0,0.75) !important;
  z-index: 9999 !important;
  overflow: hidden !important;
  margin-top: 4px !important;
}
/* Dash 2/3 legacy */
.dark-dropdown .Select-menu-outer {
  background: var(--bg-elevated) !important;
  border: 1px solid rgba(0,212,255,0.22) !important;
  border-radius: 10px !important;
  box-shadow: 0 14px 44px rgba(0,0,0,0.75) !important;
  z-index: 9999 !important;
  margin-top: 4px !important;
}
.dark-dropdown .Select-menu {
  background: var(--bg-elevated) !important;
  border-radius: 10px !important;
}

/* ---- SEARCH BOX INSIDE PANEL ---- */
.dark-dropdown .dash-dropdown-search-container,
.dark-dropdown .Select-search-box-container {
  background: var(--bg-base) !important;
  border-bottom: 1px solid rgba(255,255,255,0.06) !important;
  padding: 8px 10px !important;
}
.dark-dropdown .dash-dropdown-search,
.dark-dropdown .VirtualizedSelectFocusedOption,
.dark-dropdown input.Select-input,
.dark-dropdown .Select-input > input {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  width: 100% !important;
  color-scheme: dark;
}
.dark-dropdown .dash-dropdown-search::placeholder { color: var(--text-dim) !important; }
.dark-dropdown .dash-dropdown-search-icon { color: var(--text-dim) !important; }

/* ---- OPTIONS LIST ---- */
.dark-dropdown .dash-dropdown-options,
.dark-dropdown .VirtualizedSelectOption {
  background: transparent !important;
  padding: 4px 0 !important;
}
/* Dash 4 option */
.dark-dropdown .dash-dropdown-option {
  background: transparent !important;
  color: var(--text-muted) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  padding: 9px 14px !important;
  cursor: pointer !important;
  transition: background 0.12s, color 0.12s !important;
}
.dark-dropdown .dash-dropdown-option:hover {
  background: rgba(0,212,255,0.08) !important;
  color: var(--accent-cyan) !important;
}
.dark-dropdown .dash-dropdown-option[aria-selected="true"] {
  background: rgba(0,212,255,0.13) !important;
  color: var(--accent-cyan) !important;
  font-weight: 600 !important;
}
/* Dash 2/3 legacy option */
.dark-dropdown .Select-option {
  background: transparent !important;
  color: var(--text-muted) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  padding: 9px 14px !important;
  cursor: pointer !important;
}
.dark-dropdown .Select-option:hover,
.dark-dropdown .Select-option.is-focused {
  background: rgba(0,212,255,0.08) !important;
  color: var(--accent-cyan) !important;
}
.dark-dropdown .Select-option.is-selected {
  background: rgba(0,212,255,0.13) !important;
  color: var(--accent-cyan) !important;
  font-weight: 600 !important;
}

/* ---- ACTION BUTTONS ---- */
.dark-dropdown .dash-dropdown-actions {
  background: var(--bg-base) !important;
  border-top: 1px solid rgba(255,255,255,0.06) !important;
  padding: 6px 10px !important;
  display: flex !important;
  gap: 8px !important;
}
.dark-dropdown .dash-dropdown-action-button {
  background: rgba(0,212,255,0.08) !important;
  border: 1px solid rgba(0,212,255,0.2) !important;
  border-radius: 6px !important;
  color: var(--accent-cyan) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  padding: 3px 10px !important;
  cursor: pointer !important;
  transition: background 0.15s !important;
}
.dark-dropdown .dash-dropdown-action-button:hover { background: rgba(0,212,255,0.16) !important; }

/* Virtualized list wrapper */
.dark-dropdown .dash-options-list-virtualized,
.dark-dropdown .VirtualizedSelectOption { background: transparent !important; }


.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: var(--shadow-card);
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s, transform 0.15s;
  cursor: default;
}
.kpi-card:hover { border-color: var(--border-glow); transform: translateY(-1px); }
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
  opacity: 0;
  transition: opacity 0.2s;
}
.kpi-card:hover::before { opacity: 1; }
.kpi-icon { font-size: 18px; margin-bottom: 8px; }
.kpi-label {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}
.kpi-value {
  font-family: 'Syne', sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-top: 4px;
  line-height: 1.15;
}
.kpi-delta {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 600;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 999px;
}
.delta-up   { background: rgba(0,229,160,0.12); color: var(--accent-green); }
.delta-down { background: rgba(255,77,109,0.12); color: var(--accent-red); }
.delta-flat { background: rgba(123,142,168,0.12); color: var(--text-muted); }

/* ── Main content layout ───────────────────── */
.main-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

/* ── DRE Panel ─────────────────────────────── */
.dre-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  box-shadow: var(--shadow-card);
  height: fit-content;
}
.dre-title {
  font-family: 'Syne', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent-cyan);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dre-title::before {
  content: ''; width: 3px; height: 16px;
  background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green));
  border-radius: 2px; flex-shrink: 0;
}
.dre-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12.5px;
  transition: background 0.15s;
}
.dre-row:last-child { border-bottom: none; }
.dre-row:hover { background: rgba(255,255,255,0.02); border-radius: 6px; padding-left: 4px; }
.dre-row-label { color: var(--text-muted); font-weight: 400; }
.dre-row-value { font-family: 'DM Mono', monospace; font-size: 12px; color: var(--text); font-weight: 500; }
.dre-row.highlight .dre-row-label { color: var(--text); font-weight: 600; }
.dre-row.highlight .dre-row-value { color: var(--accent-cyan); }
.dre-row.positive .dre-row-value { color: var(--accent-green); }
.dre-row.negative .dre-row-value { color: var(--accent-red); }
.dre-section-sep {
  height: 1px;
  background: linear-gradient(90deg, var(--accent-cyan), transparent);
  margin: 8px 0;
  opacity: 0.3;
}

/* ── Charts Grid ───────────────────────────── */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 14px;
}
.chart-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 14px 8px;
  box-shadow: var(--shadow-card);
  transition: border-color 0.2s;
}
.chart-card:hover { border-color: rgba(0,212,255,0.15); }
.chart-card-title {
  font-family: 'Syne', sans-serif;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.chart-card-title span.dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.dot-cyan   { background: var(--accent-cyan); box-shadow: 0 0 6px var(--accent-cyan); }
.dot-green  { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
.dot-purple { background: var(--accent-purple); box-shadow: 0 0 6px var(--accent-purple); }
.dot-amber  { background: var(--accent-amber); box-shadow: 0 0 6px var(--accent-amber); }

/* ── Bottom Grid (map + scatter full width row) */
.bottom-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

/* ── Insights Table ────────────────────────── */
.insights-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  box-shadow: var(--shadow-card);
  margin-bottom: 14px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.section-title {
  font-family: 'Syne', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge-count {
  background: rgba(255,77,109,0.15);
  color: var(--accent-red);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,77,109,0.3);
}

/* ── Dash DataTable — full dark override ───── */
#insights-table .dash-table-container,
#insights-table .dash-spreadsheet-inner,
#insights-table .dash-spreadsheet-container { border: none !important; background: transparent !important; }

/* Cells & headers */
#insights-table .dash-cell,
#insights-table .dash-header {
  background: var(--bg-elevated) !important;
  color: var(--text) !important;
  border: 1px solid rgba(255,255,255,0.06) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 12.5px !important;
  padding: 8px 12px !important;
}
#insights-table .dash-header {
  background: var(--bg-base) !important;
  color: var(--text-muted) !important;
  font-weight: 600 !important;
  font-size: 11px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}
#insights-table tr:hover .dash-cell { background: var(--bg-hover) !important; }

/* ── Column filter input row ───────────────── */
#insights-table .dash-filter,
#insights-table .dash-filter input,
#insights-table input.dash-filter-field {
  background: var(--bg-base) !important;
  color: var(--text-muted) !important;
  border: 1px solid rgba(0,212,255,0.15) !important;
  border-radius: 6px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 12px !important;
  padding: 4px 8px !important;
  outline: none !important;
  transition: border-color 0.15s !important;
  color-scheme: dark;
}
#insights-table .dash-filter input:focus,
#insights-table input.dash-filter-field:focus {
  border-color: var(--accent-cyan) !important;
  color: var(--text) !important;
  box-shadow: 0 0 0 2px rgba(0,212,255,0.10) !important;
}
#insights-table .dash-filter input::placeholder { color: var(--text-dim) !important; }

/* ── Sort icons ────────────────────────────── */
#insights-table .column-header--sort,
#insights-table .dash-header .column-header-name { color: var(--text-muted) !important; }
#insights-table .dash-sort-arrow { color: var(--accent-cyan) !important; }

/* ── Pagination bar ────────────────────────── */
#insights-table .previous-next-container,
#insights-table .page-number,
#insights-table .dash-pagination { background: transparent !important; }

#insights-table .previous-page,
#insights-table .next-page,
#insights-table .last-page,
#insights-table .first-page {
  background: var(--bg-elevated) !important;
  border: 1px solid rgba(0,212,255,0.2) !important;
  border-radius: 7px !important;
  color: var(--text-muted) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 12px !important;
  padding: 4px 10px !important;
  cursor: pointer !important;
  transition: border-color 0.15s, color 0.15s !important;
}
#insights-table .previous-page:hover,
#insights-table .next-page:hover,
#insights-table .last-page:hover,
#insights-table .first-page:hover {
  border-color: var(--accent-cyan) !important;
  color: var(--accent-cyan) !important;
}

#insights-table .current-page,
#insights-table input.current-page {
  background: var(--bg-base) !important;
  border: 1px solid rgba(0,212,255,0.2) !important;
  border-radius: 7px !important;
  color: var(--accent-cyan) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 12px !important;
  text-align: center !important;
  width: 36px !important;
  padding: 4px 0 !important;
  outline: none !important;
  color-scheme: dark;
}
#insights-table .current-page:focus,
#insights-table input.current-page:focus {
  border-color: var(--accent-cyan) !important;
  box-shadow: 0 0 0 2px rgba(0,212,255,0.10) !important;
}

#insights-table .page-number span,
#insights-table .dash-pagination-container,
#insights-table .pagination-nav { color: var(--text-muted) !important; font-size: 12px !important; }

/* ── Tooltip ───────────────────────────────── */
.dash-tooltip,
.dash-tooltip--multiline,
.dash-tooltip-content,
.dash-tooltip-wrapper,
.dash-table-tooltip {
  background: var(--bg-elevated) !important;
  background-color: var(--bg-elevated) !important;
  border: 1px solid rgba(0,212,255,0.25) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 12px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
  padding: 10px 14px !important;
  max-width: 380px !important;
  color-scheme: dark;
}
/* Arrow border color */
.dash-tooltip::before,
.dash-tooltip::after,
.dash-tooltip--multiline::before,
.dash-tooltip--multiline::after {
  border-bottom-color: rgba(0,212,255,0.25) !important;
  border-top-color: rgba(0,212,255,0.25) !important;
}
/* Inner text and markdown inside tooltip */
.dash-tooltip p,
.dash-tooltip span,
.dash-tooltip--multiline p,
.dash-tooltip-content p,
.dash-tooltip-content span {
  color: var(--text) !important;
  background: transparent !important;
  margin: 0 !important;
}

/* Priority badges inside table */
.badge-alta  { background: rgba(255,77,109,0.15); color: var(--accent-red);   padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; border: 1px solid rgba(255,77,109,0.3); }
.badge-media { background: rgba(244,160,38,0.15); color: var(--accent-amber); padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; border: 1px solid rgba(244,160,38,0.3); }
.badge-baixa { background: rgba(0,229,160,0.12);  color: var(--accent-green); padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; border: 1px solid rgba(0,229,160,0.3); }

/* ── Footer ────────────────────────────────── */
.footer {
  text-align: center;
  color: var(--text-dim);
  font-size: 11px;
  padding: 14px 0 6px;
  border-top: 1px solid var(--border);
  margin-top: 8px;
}
.footer-link {
  color: var(--accent-cyan);
  text-decoration: none;
  font-weight: 600;
  transition: opacity 0.15s;
}
.footer-link:hover { opacity: 0.75; text-decoration: underline; }

/* ── Responsive ────────────────────────────── */
@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .main-layout { grid-template-columns: 1fr; }
  .charts-grid { grid-template-columns: 1fr; }
  .bottom-charts { grid-template-columns: 1fr; }
  .filters-bar { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
  .app-shell { padding: 12px; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .filters-bar { grid-template-columns: 1fr; }
  .page-title { font-size: 22px; }
}

            :root { --bg-base: #080c14; }
            body { background-color: #080c14 !important; color: #e8edf5; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ─── Layout ───────────────────────────────────────────────────────────────────
app.layout = html.Div(
    className="app-shell",
    children=[
        # ── Hero ──────────────────────────────────────────────────────────────
        html.Div(
            className="hero",
            children=[
                html.Div(
                    className="hero-left",
                    children=[
                        html.H1("DRE PDV Analytics", className="page-title"),
                        html.P(
                            "Demonstrativo de Resultados · Visão Consolidada por Ponto de Venda",
                            className="page-subtitle",
                        ),
                    ],
                ),
                html.Div(
                    className="hero-right",
                    children=[
                        html.Div(
                            className="hero-live",
                            children=[
                                html.Div(className="live-dot"),
                                html.Span("LIVE DATA", className="live-label"),
                            ],
                        ),
                        html.Div(
                            className="hero-signature",
                            children=[
                                html.Span("Mário Schenkel", className="sig-name"),
                                html.Span("Business Data Analyst", className="sig-role"),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        # ── Filters ────────────────────────────────────────────────────────────
        html.Div(
            className="filters-bar",
            children=[
                html.Div([
                    html.Label("Período"),
                    html.Div(
                        className="date-range-wrapper",
                        children=[
                            dcc.Input(
                                id="filter-start",
                                type="month",
                                value=MESES[0][:7],
                                min=MESES[0][:7],
                                max=MESES[-1][:7],
                                className="dark-month-input",
                            ),
                            html.Span("→", className="date-arrow"),
                            dcc.Input(
                                id="filter-end",
                                type="month",
                                value=MESES[-1][:7],
                                min=MESES[0][:7],
                                max=MESES[-1][:7],
                                className="dark-month-input",
                            ),
                        ],
                    ),
                ], className="filter-item"),
                html.Div([
                    html.Label("Região"),
                    dcc.Dropdown(
                        id="filter-regiao",
                        options=[{"label": r, "value": r} for r in REGIOES],
                        multi=True,
                        placeholder="Todas as regiões",
                        clearable=True,
                        className="dark-dropdown",
                    ),
                ], className="filter-item"),
                html.Div([
                    html.Label("Canal"),
                    dcc.Dropdown(
                        id="filter-canal",
                        options=[{"label": c, "value": c} for c in CANAIS],
                        multi=True,
                        placeholder="Todos os canais",
                        clearable=True,
                        className="dark-dropdown",
                    ),
                ], className="filter-item"),
                html.Div([
                    html.Label("PDV"),
                    dcc.Dropdown(
                        id="filter-pdv",
                        options=[{"label": p, "value": p} for p in ALL_PDVS],
                        multi=True,
                        placeholder="Todos os PDVs",
                        clearable=True,
                        className="dark-dropdown",
                    ),
                ], className="filter-item"),
            ],
        ),

        # ── KPI Cards ─────────────────────────────────────────────────────────
        html.Div(
            className="kpi-grid",
            children=[
                kpi_card("receita",  "💰", "Receita Líquida"),
                kpi_card("margem",   "📊", "Margem Operacional"),
                kpi_card("ebitda",   "⚡", "EBITDA"),
                kpi_card("lucro",    "🏆", "Lucro Líquido"),
                kpi_card("criticos", "🚨", "PDVs Críticos"),
            ],
        ),

        # ── Main Layout: DRE sidebar + 4 charts ───────────────────────────────
        html.Div(
            className="main-layout",
            children=[
                # DRE Panel
                html.Div(
                    className="dre-panel",
                    children=[
                        html.Div("Demonstrativo de Resultados", className="dre-title"),
                        html.Div(id="dre-content"),
                    ],
                ),
                # 2x2 Charts
                html.Div(
                    className="charts-grid",
                    children=[
                        html.Div(
                            className="chart-card",
                            children=[
                                section_title("Distribuição por Canal", "cyan"),
                                dcc.Graph(id="chart-donut", config={"displayModeBar": False},
                                          style={"height": "260px"}),
                            ],
                        ),
                        html.Div(
                            className="chart-card",
                            children=[
                                section_title("Receita x Margem Operacional", "green"),
                                dcc.Graph(id="chart-scatter", config={"displayModeBar": False},
                                          style={"height": "260px"}),
                            ],
                        ),
                        html.Div(
                            className="chart-card",
                            children=[
                                section_title("Evolução do Lucro Líquido", "purple"),
                                dcc.Graph(id="chart-linhas", config={"displayModeBar": False},
                                          style={"height": "260px"}),
                            ],
                        ),
                        html.Div(
                            className="chart-card",
                            children=[
                                section_title("Top PDVs por Receita Líquida", "amber"),
                                dcc.Graph(id="chart-bar-pdv", config={"displayModeBar": False},
                                          style={"height": "260px"}),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        # ── Bottom Row: Map + Composição DRE ──────────────────────────────────
        html.Div(
            className="bottom-charts",
            children=[
                html.Div(
                    className="chart-card",
                    children=[
                        section_title("Mapa do Brasil · PDVs por Região", "cyan"),
                        dcc.Graph(id="chart-mapa", config={"displayModeBar": False},
                                  style={"height": "380px"}),
                    ],
                ),
                html.Div(
                    className="chart-card",
                    children=[
                        section_title("Composição de Resultado por Região", "green"),
                        dcc.Graph(id="chart-bar-regiao", config={"displayModeBar": False},
                                  style={"height": "380px"}),
                    ],
                ),
            ],
        ),

        # ── Insights Table ────────────────────────────────────────────────────
        html.Div(
            className="insights-section",
            children=[
                html.Div(
                    className="section-header",
                    children=[
                        html.Div(
                            className="section-title",
                            children=[
                                html.Span("⚠", style={"color": "#ff4d6d"}),
                                "PDVs Críticos — Planos de Ação",
                                html.Span(id="badge-criticos", className="badge-count", children="0"),
                            ],
                        ),
                    ],
                ),
                html.Div(id="insights-table"),
            ],
        ),

        # Footer
        html.Div(
            className="footer",
            children=[
                "DRE PDV Analytics · Powered by ",
                html.A(
                    "Mário Schenkel",
                    href="https://schenkel94.github.io/portfolio/",
                    target="_blank",
                    className="footer-link",
                ),
                " · Dados atualizados automaticamente",
            ],
        ),
    ],
)


# ─── Master Callback ──────────────────────────────────────────────────────────
@app.callback(
    Output("kpi-receita",        "children"),
    Output("kpi-margem",         "children"),
    Output("kpi-ebitda",         "children"),
    Output("kpi-lucro",          "children"),
    Output("kpi-criticos",       "children"),
    Output("dre-content",        "children"),
    Output("chart-donut",        "figure"),
    Output("chart-scatter",      "figure"),
    Output("chart-linhas",       "figure"),
    Output("chart-bar-pdv",      "figure"),
    Output("chart-mapa",         "figure"),
    Output("chart-bar-regiao",   "figure"),
    Output("insights-table",     "children"),
    Output("badge-criticos",     "children"),
    Input("filter-start",  "value"),
    Input("filter-end",    "value"),
    Input("filter-regiao", "value"),
    Input("filter-canal",  "value"),
    Input("filter-pdv",    "value"),
)
def update_all(start, end, regioes, canais, pdvs):
    # Convert YYYY-MM to full date string for filter
    start_dt = f"{start}-01" if start else None
    end_dt   = f"{end}-01"   if end   else None
    dff = apply_filters(DF, regioes, canais, start_dt, end_dt, pdvs)

    # ── KPIs ------------------------------------------------------------------
    rl_curr  = dff["receita_liquida"].sum()
    mo_curr  = dff["margem_operacional"].mean()
    eb_curr  = dff["ebitda"].sum()
    ll_curr  = dff["lucro_liquido"].sum()
    criticos_n = dff[dff["prioridade_risco"] == "alta"]["id_pdv"].nunique()

    kpi_results = [
        brl(rl_curr),
        pct(mo_curr),
        brl(eb_curr),
        brl(ll_curr),
        str(criticos_n),
    ]

    # ── DRE ------------------------------------------------------------------
    def dre_row(label, value, cls=""):
        return html.Div(
            className=f"dre-row {cls}",
            children=[
                html.Span(label, className="dre-row-label"),
                html.Span(value, className="dre-row-value"),
            ],
        )

    agg = dff.agg({
        "receita_bruta":             "sum",
        "devolucoes":                "sum",
        "receita_liquida":           "sum",
        "cmv":                       "sum",
        "lucro_bruto":               "sum",
        "despesas_variaveis":        "sum",
        "despesas_fixas":            "sum",
        "lucro_operacional":         "sum",
        "depreciacao_amortizacao":   "sum",
        "ebitda":                    "sum",
        "resultado_financeiro":      "sum",
        "lucro_liquido":             "sum",
    })

    mg_op  = agg["lucro_operacional"] / agg["receita_liquida"] if agg["receita_liquida"] else 0
    mg_ebt = agg["ebitda"] / agg["receita_liquida"] if agg["receita_liquida"] else 0
    mg_liq = agg["lucro_liquido"] / agg["receita_liquida"] if agg["receita_liquida"] else 0

    dre_children = [
        dre_row("Receita Bruta",          brl(agg["receita_bruta"])),
        dre_row("(−) Devoluções",          brl(-agg["devolucoes"]), "negative"),
        html.Div(className="dre-section-sep"),
        dre_row("Receita Líquida",         brl(agg["receita_liquida"]), "highlight"),
        dre_row("(−) CMV",                 brl(-agg["cmv"]), "negative"),
        html.Div(className="dre-section-sep"),
        dre_row("Lucro Bruto",             brl(agg["lucro_bruto"]),
                "positive" if agg["lucro_bruto"] >= 0 else "negative"),
        dre_row("(−) Desp. Variáveis",     brl(-agg["despesas_variaveis"]), "negative"),
        dre_row("(−) Desp. Fixas",         brl(-agg["despesas_fixas"]), "negative"),
        html.Div(className="dre-section-sep"),
        dre_row("Resultado Operacional",   brl(agg["lucro_operacional"]),
                "positive" if agg["lucro_operacional"] >= 0 else "negative"),
        dre_row("Margem Operacional",      pct(mg_op),
                "positive" if mg_op >= 0 else "negative"),
        dre_row("(+) Depr./Amort.",        brl(agg["depreciacao_amortizacao"])),
        html.Div(className="dre-section-sep"),
        dre_row("EBITDA",                  brl(agg["ebitda"]),
                "highlight " + ("positive" if agg["ebitda"] >= 0 else "negative")),
        dre_row("Margem EBITDA",           pct(mg_ebt),
                "positive" if mg_ebt >= 0 else "negative"),
        dre_row("Res. Financeiro",         brl(agg["resultado_financeiro"])),
        html.Div(className="dre-section-sep"),
        dre_row("Lucro Líquido",           brl(agg["lucro_liquido"]),
                "highlight " + ("positive" if agg["lucro_liquido"] >= 0 else "negative")),
        dre_row("Margem Líquida",          pct(mg_liq),
                "positive" if mg_liq >= 0 else "negative"),
    ]

    # ── Donut – Canal --------------------------------------------------------
    canal_agg = dff.groupby("canal")["receita_liquida"].sum().reset_index()
    fig_donut = go.Figure(go.Pie(
        labels=canal_agg["canal"],
        values=canal_agg["receita_liquida"],
        hole=0.62,
        marker=dict(colors=["#00d4ff", "#00e5a0", "#9b5de5", "#f4a026"],
                    line=dict(color="#0e1420", width=3)),
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Receita: R$ %{value:,.0f}<extra></extra>",
    ))
    fig_donut.add_annotation(
        text=f"<b>{len(canal_agg)}</b><br><span style='font-size:9px'>canais</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="#e8edf5"),
    )
    fig_donut.update_layout(**DARK_LAYOUT, showlegend=True,
                             legend=dict(orientation="v", x=1.02, y=0.5,
                                         font=dict(size=11, color="#7b8ea8")))

    # ── Scatter – Receita x Margem -------------------------------------------
    pdv_agg = (
        dff.groupby(["id_pdv", "regiao", "canal"])
        .agg(receita_liquida=("receita_liquida", "sum"),
             margem_op=("margem_operacional", "mean"),
             lucro_liquido=("lucro_liquido", "sum"),
             score=("score_alerta", "mean"))
        .reset_index()
    )
    max_ll = max(pdv_agg["lucro_liquido"].abs().max(), 1)

    fig_scatter = go.Figure()
    for reg in pdv_agg["regiao"].unique():
        sub = pdv_agg[pdv_agg["regiao"] == reg]
        fig_scatter.add_trace(go.Scatter(
            x=sub["receita_liquida"],
            y=sub["margem_op"] * 100,
            mode="markers",
            name=reg,
            marker=dict(
                size=sub["lucro_liquido"].abs() / max_ll * 22 + 6,
                color=REGION_COLORS.get(reg, "#7b8ea8"),
                opacity=0.8,
                line=dict(width=1, color="rgba(255,255,255,0.15)"),
            ),
            text=sub["id_pdv"],
            customdata=sub[["lucro_liquido", "canal"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Receita: R$ %{x:,.0f}<br>"
                "Margem Op.: %{y:.1f}%<br>"
                "Canal: %{customdata[1]}<extra></extra>"
            ),
        ))
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="rgba(255,77,109,0.4)", line_width=1)
    fig_scatter.update_layout(
        **DARK_LAYOUT,
        showlegend=True,
        legend=dict(orientation="h", y=-0.18, x=0, font=dict(size=10)),
        xaxis_title="Receita Líquida (R$)",
        yaxis_title="Margem Op. (%)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickformat=",.0f",
                   zerolinecolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="%",
                   zerolinecolor="rgba(255,255,255,0.08)"),
    )

    # ── Line – Lucro Líquido evolution ----------------------------------------
    time_agg = dff.groupby("mes")["lucro_liquido"].sum().reset_index()
    time_agg = time_agg.sort_values("mes")
    positive_mask = time_agg["lucro_liquido"] >= 0

    fig_line = go.Figure()
    # Gradient fill
    fig_line.add_trace(go.Scatter(
        x=time_agg["mes"], y=time_agg["lucro_liquido"],
        mode="lines",
        name="Lucro Líquido",
        line=dict(color="#9b5de5", width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(155,93,229,0.12)",
        hovertemplate="<b>%{x|%b %Y}</b><br>Lucro: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_line.add_hline(y=0, line_color="rgba(255,77,109,0.4)", line_width=1, line_dash="dot")
    fig_line.update_layout(
        **DARK_LAYOUT,
        showlegend=False,
        xaxis=dict(tickformat="%b/%y", gridcolor="rgba(255,255,255,0.05)",
                   zerolinecolor="rgba(255,255,255,0.05)"),
        yaxis=dict(tickformat=",.0f", gridcolor="rgba(255,255,255,0.05)",
                   zerolinecolor="rgba(255,255,255,0.05)"),
    )

    # ── Bar – Top PDVs -------------------------------------------------------
    top_pdv = (
        dff.groupby("id_pdv")["receita_liquida"].sum()
        .sort_values(ascending=False).head(12).reset_index()
    )
    top_pdv["cor"] = top_pdv["receita_liquida"].apply(
        lambda v: "#00d4ff" if v >= top_pdv["receita_liquida"].quantile(0.66)
        else "#00e5a0" if v >= top_pdv["receita_liquida"].quantile(0.33) else "#f4a026"
    )
    fig_bar = go.Figure(go.Bar(
        y=top_pdv["id_pdv"],
        x=top_pdv["receita_liquida"],
        orientation="h",
        marker=dict(color=top_pdv["cor"], opacity=0.9,
                    line=dict(color="rgba(255,255,255,0.08)", width=0.5)),
        hovertemplate="<b>%{y}</b><br>Receita: R$ %{x:,.0f}<extra></extra>",
    ))
    fig_bar.update_layout(
        **DARK_LAYOUT,
        showlegend=False,
        yaxis=dict(gridcolor="rgba(255,255,255,0.0)", autorange="reversed",
                   tickfont=dict(size=10), zerolinecolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickformat=",.0f",
                   zerolinecolor="rgba(255,255,255,0.05)"),
        bargap=0.35,
    )

    # ── Mapa do Brasil --------------------------------------------------------
    # Approximate centroids for Brazilian regions
    REGION_GEO = {
        "Sudeste":     {"lat": -20.5, "lon": -43.9},
        "Sul":         {"lat": -27.6, "lon": -51.0},
        "Nordeste":    {"lat": -8.0,  "lon": -38.5},
        "Centro-Oeste":{"lat": -15.8, "lon": -52.2},
        "Norte":       {"lat": -4.0,  "lon": -61.0},
    }

    reg_agg = (
        dff.groupby("regiao")
        .agg(
            receita_liquida=("receita_liquida", "sum"),
            margem_op=("margem_operacional", "mean"),
            ebitda=("ebitda", "sum"),
            lucro_liquido=("lucro_liquido", "sum"),
            n_pdv=("id_pdv", "nunique"),
            n_criticos=("prioridade_risco", lambda x: (x == "alta").sum()),
        )
        .reset_index()
    )

    reg_agg["lat"] = reg_agg["regiao"].map(lambda r: REGION_GEO.get(r, {}).get("lat", -15))
    reg_agg["lon"] = reg_agg["regiao"].map(lambda r: REGION_GEO.get(r, {}).get("lon", -55))
    reg_agg["color"] = reg_agg["regiao"].map(lambda r: REGION_COLORS.get(r, "#7b8ea8"))
    reg_agg["size_norm"] = (
        (reg_agg["receita_liquida"] / reg_agg["receita_liquida"].max()) * 40 + 15
    )

    fig_mapa = go.Figure()

    # Brazil outline (simplified scatter_geo)
    fig_mapa.add_trace(go.Scattergeo(
        lat=reg_agg["lat"],
        lon=reg_agg["lon"],
        mode="markers+text",
        marker=dict(
            size=reg_agg["size_norm"],
            color=reg_agg["color"],
            opacity=0.85,
            line=dict(color="rgba(255,255,255,0.2)", width=1.5),
        ),
        text=reg_agg["regiao"].str.replace("-", "-<br>"),
        textposition="bottom center",
        textfont=dict(size=10, color="#e8edf5"),
        customdata=reg_agg[[
            "receita_liquida", "margem_op", "ebitda",
            "lucro_liquido", "regiao"
        ]],
        hovertemplate=(
            "<b>%{customdata[4]}</b><br>"
            "━━━━━━━━━━━━━━━━━━━━<br>"
            "💰 Receita Líquida: <b>R$ %{customdata[0]:,.0f}</b><br>"
            "📊 Margem Op.: <b>%{customdata[1]:.1%}</b><br>"
            "⚡ EBITDA: <b>R$ %{customdata[2]:,.0f}</b><br>"
            "🏆 Lucro Líq.: <b>R$ %{customdata[3]:,.0f}</b>"
            "<extra></extra>"
        ),
        name="",
    ))

    fig_mapa.update_layout(
        **DARK_LAYOUT,
        geo=dict(
            scope="south america",
            showland=True,
            landcolor="rgba(19,27,42,0.9)",
            showocean=True,
            oceancolor="rgba(8,12,20,0.9)",
            showcountries=True,
            countrycolor="rgba(255,255,255,0.08)",
            showframe=False,
            bgcolor="rgba(0,0,0,0)",
            center=dict(lat=-14, lon=-53),
            projection_scale=1.8,
            lataxis_range=[-35, 6],
            lonaxis_range=[-75, -32],
            showsubunits=True,
            subunitcolor="rgba(255,255,255,0.05)",
        ),
        showlegend=False,
        uirevision="brazil-fixed",
    )

    # ── Stacked bar – Composição por Região -----------------------------------
    reg_comp = (
        dff.groupby("regiao")
        .agg(
            receita_liquida=("receita_liquida", "sum"),
            cmv=("cmv", "sum"),
            despesas_variaveis=("despesas_variaveis", "sum"),
            despesas_fixas=("despesas_fixas", "sum"),
            lucro_liquido=("lucro_liquido", "sum"),
        )
        .reset_index()
        .sort_values("receita_liquida", ascending=True)
    )

    fig_reg = go.Figure()
    bar_defs = [
        ("CMV",              "cmv",                "#ff4d6d"),
        ("Desp. Variáveis",  "despesas_variaveis", "#f4a026"),
        ("Desp. Fixas",      "despesas_fixas",     "#9b5de5"),
        ("Lucro Líquido",    "lucro_liquido",       "#00e5a0"),
    ]
    for name, col, color in bar_defs:
        fig_reg.add_trace(go.Bar(
            y=reg_comp["regiao"],
            x=reg_comp[col],
            name=name,
            orientation="h",
            marker=dict(color=color, opacity=0.85,
                        line=dict(color="rgba(255,255,255,0.05)", width=0.5)),
            hovertemplate=f"<b>%{{y}}</b><br>{name}: R$ %{{x:,.0f}}<extra></extra>",
        ))

    fig_reg.update_layout(
        **DARK_LAYOUT,
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0, font=dict(size=10)),
        yaxis=dict(gridcolor="rgba(255,255,255,0.0)", tickfont=dict(size=11),
                   zerolinecolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickformat=",.0f",
                   zerolinecolor="rgba(255,255,255,0.05)"),
        bargap=0.3,
    )

    # ── Insights Table --------------------------------------------------------
    criticos_df = (
        dff[dff["prioridade_risco"].isin(["alta", "media"])]
        .groupby(["id_pdv", "regiao", "canal", "prioridade_risco",
                  "driver_principal", "recomendacoes"], as_index=False)
        .agg(
            receita_liquida=("receita_liquida", "sum"),
            lucro_liquido=("lucro_liquido", "sum"),
            score_alerta=("score_alerta", "mean"),
        )
        .sort_values(["prioridade_risco", "score_alerta"], ascending=[True, False])
        .head(25)
    )

    criticos_df["Receita Líq."] = criticos_df["receita_liquida"].apply(brl)
    criticos_df["Lucro Líq."]   = criticos_df["lucro_liquido"].apply(brl)
    criticos_df["Score"]         = criticos_df["score_alerta"].apply(lambda v: f"{v:.1f}")

    # Truncate recomendacoes for display
    criticos_df["Recomendações"] = criticos_df["recomendacoes"].apply(
        lambda r: (r[:120] + "…") if isinstance(r, str) and len(r) > 120 else r
    )

    table_df = criticos_df.rename(columns={
        "id_pdv":          "PDV",
        "regiao":          "Região",
        "canal":           "Canal",
        "prioridade_risco":"Prioridade",
        "driver_principal":"Driver",
    })[["PDV", "Região", "Canal", "Prioridade", "Driver",
        "Receita Líq.", "Lucro Líq.", "Score", "Recomendações"]]

    table = dash_table.DataTable(
        id="insights-table",
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_table={"overflowX": "auto", "background": "#080c14"},
        style_cell={
            "backgroundColor": "#131b2a",
            "color":           "#e8edf5",
            "border":          "1px solid rgba(255,255,255,0.06)",
            "fontFamily":      "DM Sans, sans-serif",
            "fontSize":        "12.5px",
            "padding":         "8px 12px",
            "textAlign":       "left",
            "whiteSpace":      "normal",
            "height":          "auto",
            "maxWidth":        "320px",
        },
        style_header={
            "backgroundColor": "#080c14",
            "color":           "#7b8ea8",
            "fontWeight":      "600",
            "fontSize":        "11px",
            "textTransform":   "uppercase",
            "letterSpacing":   "0.5px",
            "border":          "1px solid rgba(255,255,255,0.06)",
        },
        style_filter={
            "backgroundColor": "#080c14",
            "color":           "#7b8ea8",
            "border":          "1px solid rgba(0,212,255,0.15)",
            "fontFamily":      "DM Sans, sans-serif",
            "fontSize":        "12px",
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{Prioridade} = alta", "column_id": "Prioridade"},
                "color":      "#ff4d6d",
                "fontWeight": "700",
                "background": "rgba(255,77,109,0.08)",
            },
            {
                "if": {"filter_query": "{Prioridade} = media", "column_id": "Prioridade"},
                "color":      "#f4a026",
                "fontWeight": "700",
            },
            {
                "if": {"filter_query": "{Lucro Líq.} contains '-'"},
                "color": "#ff4d6d",
            },
            {"if": {"row_index": "odd"}, "backgroundColor": "#0e1420"},
        ],
        page_size=10,
        page_action="native",
        sort_action="native",
        filter_action="native",
        tooltip_data=[
            {col: {"value": str(row[col]), "type": "markdown"}
             for col in ["Recomendações", "Driver"]}
            for row in table_df.to_dict("records")
        ],
        tooltip_duration=None,
    )

    badge_n = str(criticos_df[criticos_df["prioridade_risco"] == "alta"].shape[0])

    return (*kpi_results, dre_children,
            fig_donut, fig_scatter, fig_line, fig_bar,
            fig_mapa, fig_reg, table, badge_n)


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8050)