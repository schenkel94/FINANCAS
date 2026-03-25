"""
DRE PDV Dashboard — Dark SaaS Premium
Requires: dash, dash-bootstrap-components, plotly, pandas, numpy
Deploy: gunicorn app:server
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dash_table, dcc, html

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "processed" / "dre_pdv_mensal_consolidado_com_acoes.csv"

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


# ─── App Init ─────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="DRE PDV · Analytics",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server  # for Render / Gunicorn

MESES     = sorted(DF["mes"].dt.strftime("%Y-%m-%d").unique())
REGIOES   = sorted(DF["regiao"].unique())
CANAIS    = sorted(DF["canal"].unique())
ALL_PDVS  = sorted(DF["id_pdv"].unique())

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
                    dcc.DatePickerRange(
                        id="filter-period",
                        min_date_allowed=MESES[0],
                        max_date_allowed=MESES[-1],
                        start_date=MESES[0],
                        end_date=MESES[-1],
                        display_format="MM/YYYY",
                        style={"width": "100%"},
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
    Input("filter-period",  "start_date"),
    Input("filter-period",  "end_date"),
    Input("filter-regiao",  "value"),
    Input("filter-canal",   "value"),
    Input("filter-pdv",     "value"),
)
def update_all(start, end, regioes, canais, pdvs):
    dff = apply_filters(DF, regioes, canais, start, end, pdvs)

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
        style_table={"overflowX": "auto"},
        style_cell={
            "backgroundColor": "#131b2a",
            "color":           "#e8edf5",
            "border":          "1px solid rgba(255,255,255,0.07)",
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
            "border":          "1px solid rgba(255,255,255,0.07)",
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