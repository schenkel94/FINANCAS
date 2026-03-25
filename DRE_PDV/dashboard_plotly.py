from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

BASE_DIR = Path(__file__).resolve().parent 
DATA_PATH = BASE_DIR / "data" / "processed" / "dre_pdv_mensal_consolidado_com_acoes.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Arquivo nao encontrado: {DATA_PATH}")


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["mes"] = pd.to_datetime(df["mes"])

    bool_cols = [
        "flag_margem_abaixo_10",
        "flag_queda_receita_20",
        "flag_ebitda_negativo",
    ]
    for col in bool_cols:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.lower().map({"true": True, "false": False})
            df[col] = df[col].fillna(False).astype(bool)

    numeric_cols = [
        "receita_bruta",
        "receita_liquida",
        "lucro_operacional",
        "ebitda",
        "lucro_liquido",
        "devolucoes",
        "score_alerta",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["regiao"] = df["regiao"].fillna("Nao informado")
    df["canal"] = df["canal"].fillna("Nao informado")
    return df


def brl(value: float) -> str:
    txt = f"{value:,.0f}"
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


def pct(value: float) -> str:
    return f"{value * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def apply_filters(
    df: pd.DataFrame,
    regioes: Iterable[str] | None,
    canais: Iterable[str] | None,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    out = df.copy()
    if regioes:
        out = out[out["regiao"].isin(regioes)]
    if canais:
        out = out[out["canal"].isin(canais)]
    if start_date:
        out = out[out["mes"] >= pd.to_datetime(start_date)]
    if end_date:
        out = out[out["mes"] <= pd.to_datetime(end_date)]
    return out


def aggregate_pdv(df: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "id_pdv",
        "regiao",
        "canal",
        "driver_principal",
        "prioridade_risco",
        "qtd_recomendacoes",
        "recomendacoes",
    ]
    agg = (
        df.groupby(keys, as_index=False)
        .agg(
            receita_liquida_total=("receita_liquida", "sum"),
            receita_bruta_total=("receita_bruta", "sum"),
            lucro_operacional_total=("lucro_operacional", "sum"),
            ebitda_total=("ebitda", "sum"),
            lucro_liquido_total=("lucro_liquido", "sum"),
            devolucoes_total=("devolucoes", "sum"),
            score_alerta_medio=("score_alerta", "mean"),
        )
        .sort_values("id_pdv")
        .reset_index(drop=True)
    )

    agg["margem_operacional_total"] = np.where(
        agg["receita_liquida_total"] > 0,
        agg["lucro_operacional_total"] / agg["receita_liquida_total"],
        np.nan,
    )
    agg["pct_devolucao"] = np.where(
        agg["receita_bruta_total"] > 0,
        agg["devolucoes_total"] / agg["receita_bruta_total"],
        np.nan,
    )
    agg["pdv_critico"] = (
        (agg["margem_operacional_total"] < 0.10)
        | (agg["ebitda_total"] < 0)
        | (agg["score_alerta_medio"] >= 1.5)
    )
    return agg


def fig_ranking(agg: pd.DataFrame) -> go.Figure:
    ranking = agg.sort_values("lucro_liquido_total", ascending=True).head(15).copy()
    ranking = ranking.sort_values("lucro_liquido_total", ascending=True)

    if ranking.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", title="Ranking de PDVs")
        return fig

    ranking["status"] = np.where(ranking["pdv_critico"], "Critico", "Saudavel")
    color_map = {"Critico": "#D1495B", "Saudavel": "#2A9D8F"}

    fig = px.bar(
        ranking,
        x="lucro_liquido_total",
        y="id_pdv",
        color="status",
        orientation="h",
        color_discrete_map=color_map,
        hover_data={
            "regiao": True,
            "canal": True,
            "margem_operacional_total": ":.2%",
            "lucro_liquido_total": ":,.2f",
            "id_pdv": False,
            "status": False,
        },
        labels={"lucro_liquido_total": "Lucro Liquido Total", "id_pdv": "PDV"},
        title="Ranking de Rentabilidade (15 piores no filtro)",
    )
    fig.update_layout(template="plotly_white", legend_title_text="Status")
    fig.update_xaxes(tickprefix="R$ ")
    return fig


def fig_temporal(df: pd.DataFrame, selected_pdv: str | None) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", title="Evolucao Temporal")
        return fig

    if selected_pdv and selected_pdv in set(df["id_pdv"]):
        frame = df[df["id_pdv"] == selected_pdv]
        title = f"Evolucao Temporal - {selected_pdv}"
    else:
        frame = df
        title = "Evolucao Temporal - Consolidado do Filtro"

    timeline = (
        frame.groupby("mes", as_index=False)
        .agg(
            receita_liquida=("receita_liquida", "sum"),
            ebitda=("ebitda", "sum"),
            lucro_liquido=("lucro_liquido", "sum"),
        )
        .sort_values("mes")
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timeline["mes"], y=timeline["receita_liquida"], mode="lines+markers", name="Receita Liquida", line=dict(color="#1D3557", width=3)))
    fig.add_trace(go.Scatter(x=timeline["mes"], y=timeline["ebitda"], mode="lines+markers", name="EBITDA", line=dict(color="#2A9D8F", width=2)))
    fig.add_trace(go.Scatter(x=timeline["mes"], y=timeline["lucro_liquido"], mode="lines+markers", name="Lucro Liquido", line=dict(color="#E76F51", width=2)))

    fig.update_layout(
        template="plotly_white",
        title=title,
        legend_title_text="Metricas",
        margin=dict(l=30, r=20, t=60, b=30),
    )
    fig.update_yaxes(tickprefix="R$ ")
    return fig


def fig_scatter(agg: pd.DataFrame) -> go.Figure:
    if agg.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", title="Receita x Margem")
        return fig

    frame = agg.copy()
    frame["status"] = np.where(frame["pdv_critico"], "Critico", "Saudavel")
    frame["tamanho"] = frame["receita_liquida_total"].clip(lower=1)

    fig = px.scatter(
        frame,
        x="receita_liquida_total",
        y="margem_operacional_total",
        color="status",
        size="tamanho",
        size_max=35,
        color_discrete_map={"Critico": "#D1495B", "Saudavel": "#2A9D8F"},
        hover_name="id_pdv",
        hover_data={
            "regiao": True,
            "canal": True,
            "driver_principal": True,
            "prioridade_risco": True,
            "lucro_liquido_total": ":,.2f",
            "receita_liquida_total": ":,.2f",
            "margem_operacional_total": ":.2%",
            "tamanho": False,
            "status": False,
        },
        title="Dispersao Receita Liquida x Margem Operacional",
        labels={
            "receita_liquida_total": "Receita Liquida Total",
            "margem_operacional_total": "Margem Operacional",
        },
    )

    fig.add_hline(y=0.10, line_color="#FFB703", line_dash="dash", annotation_text="Limite de alerta: 10%", annotation_position="bottom right")
    fig.update_layout(template="plotly_white", legend_title_text="Status")
    fig.update_xaxes(tickprefix="R$ ")
    fig.update_yaxes(tickformat=".0%")
    return fig


def fig_regional(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", title="Comparativo Regional")
        return fig

    regional = (
        df.groupby("regiao", as_index=False)
        .agg(
            receita_liquida=("receita_liquida", "sum"),
            lucro_operacional=("lucro_operacional", "sum"),
        )
        .sort_values("receita_liquida", ascending=False)
    )
    regional["margem_operacional"] = np.where(
        regional["receita_liquida"] > 0,
        regional["lucro_operacional"] / regional["receita_liquida"],
        np.nan,
    )

    fig = px.bar(
        regional,
        x="regiao",
        y="margem_operacional",
        color="margem_operacional",
        color_continuous_scale=["#D1495B", "#F4A261", "#2A9D8F"],
        title="Margem Operacional por Regiao",
        labels={"margem_operacional": "Margem Operacional", "regiao": "Regiao"},
    )
    fig.update_layout(template="plotly_white", coloraxis_showscale=False)
    fig.update_yaxes(tickformat=".0%")
    return fig


def recommendations_block(agg: pd.DataFrame, selected_pdv: str | None) -> html.Div:
    if agg.empty:
        return html.Div("Nenhum dado disponivel para os filtros selecionados.", className="empty-state")

    if selected_pdv and selected_pdv in set(agg["id_pdv"]):
        target = agg[agg["id_pdv"] == selected_pdv].iloc[0]
    else:
        target = agg.sort_values(["pdv_critico", "lucro_liquido_total"], ascending=[False, True]).iloc[0]

    texto = str(target.get("recomendacoes", ""))
    recs = [r.strip() for r in texto.split("|") if r.strip()]
    if not recs:
        recs = ["Sem recomendacoes disponiveis para este PDV."]

    return html.Div(
        [
            html.Div([
                html.H4(f"PDV focal: {target['id_pdv']}", className="rec-title"),
                html.Div(f"Driver: {target.get('driver_principal', 'n/a')}", className="rec-chip chip-driver"),
                html.Div(f"Prioridade: {target.get('prioridade_risco', 'n/a')}", className="rec-chip chip-priority"),
            ], className="rec-header"),
            html.Ul([html.Li(rec) for rec in recs], className="rec-list"),
        ],
        className="recommendation-card",
    )


def metric_card(title: str, element_id: str) -> html.Div:
    return html.Div(
        [
            html.Div(title, className="kpi-title"),
            html.Div("--", id=element_id, className="kpi-value"),
        ],
        className="kpi-card",
    )


df_base = load_data(DATA_PATH)
min_date = df_base["mes"].min().date()
max_date = df_base["mes"].max().date()

app = Dash(__name__)
app.title = "DRE por PDV - Dashboard Plotly"
server = app.server

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Rentabilidade por PDV", className="page-title"),
                html.P("Dashboard analitico de DRE com filtros, criticidade e planos de acao.", className="page-subtitle"),
            ],
            className="hero",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Regiao"),
                        dcc.Dropdown(
                            id="filter-regiao",
                            options=[{"label": r, "value": r} for r in sorted(df_base["regiao"].unique())],
                            value=sorted(df_base["regiao"].unique()),
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    className="filter-item",
                ),
                html.Div(
                    [
                        html.Label("Canal"),
                        dcc.Dropdown(
                            id="filter-canal",
                            options=[{"label": c, "value": c} for c in sorted(df_base["canal"].unique())],
                            value=sorted(df_base["canal"].unique()),
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    className="filter-item",
                ),
                html.Div(
                    [
                        html.Label("Periodo"),
                        dcc.DatePickerRange(
                            id="filter-periodo",
                            min_date_allowed=min_date,
                            max_date_allowed=max_date,
                            start_date=min_date,
                            end_date=max_date,
                            display_format="YYYY-MM",
                        ),
                    ],
                    className="filter-item",
                ),
                html.Div(
                    [
                        html.Label("PDV (foco)"),
                        dcc.Dropdown(id="filter-pdv", placeholder="Consolidado dos filtros", clearable=True),
                    ],
                    className="filter-item",
                ),
            ],
            className="filters",
        ),
        html.Div(
            [
                metric_card("Receita Liquida", "kpi-receita"),
                metric_card("Margem Operacional", "kpi-margem"),
                metric_card("EBITDA", "kpi-ebitda"),
                metric_card("Lucro Liquido", "kpi-lucro"),
                metric_card("PDVs Criticos", "kpi-criticos"),
            ],
            className="kpi-grid",
        ),
        html.Div(
            [
                dcc.Graph(id="fig-ranking", className="chart-card"),
                dcc.Graph(id="fig-temporal", className="chart-card"),
            ],
            className="chart-grid two-col",
        ),
        html.Div(
            [
                dcc.Graph(id="fig-scatter", className="chart-card"),
                dcc.Graph(id="fig-regional", className="chart-card"),
            ],
            className="chart-grid two-col",
        ),
        html.Div(
            [
                html.H3("Planos de Acao Recomendados", className="section-title"),
                html.Div(id="bloco-recomendacoes"),
            ],
            className="actions-section",
        ),
    ],
    className="app-shell",
)


@app.callback(
    Output("filter-pdv", "options"),
    Output("filter-pdv", "value"),
    Input("filter-regiao", "value"),
    Input("filter-canal", "value"),
    Input("filter-periodo", "start_date"),
    Input("filter-periodo", "end_date"),
    Input("filter-pdv", "value"),
)
def update_pdv_options(regioes, canais, start_date, end_date, pdv_atual):
    filtered = apply_filters(df_base, regioes, canais, start_date, end_date)
    options = [{"label": p, "value": p} for p in sorted(filtered["id_pdv"].unique())]
    if pdv_atual not in [o["value"] for o in options]:
        pdv_atual = None
    return options, pdv_atual


@app.callback(
    Output("kpi-receita", "children"),
    Output("kpi-margem", "children"),
    Output("kpi-ebitda", "children"),
    Output("kpi-lucro", "children"),
    Output("kpi-criticos", "children"),
    Output("fig-ranking", "figure"),
    Output("fig-temporal", "figure"),
    Output("fig-scatter", "figure"),
    Output("fig-regional", "figure"),
    Output("bloco-recomendacoes", "children"),
    Input("filter-regiao", "value"),
    Input("filter-canal", "value"),
    Input("filter-periodo", "start_date"),
    Input("filter-periodo", "end_date"),
    Input("filter-pdv", "value"),
)
def update_dashboard(regioes, canais, start_date, end_date, selected_pdv):
    filtered = apply_filters(df_base, regioes, canais, start_date, end_date)

    if filtered.empty:
        vazio = go.Figure().update_layout(template="plotly_white", title="Sem dados para o filtro")
        return (
            "R$ 0",
            "0,0%",
            "R$ 0",
            "R$ 0",
            "0",
            vazio,
            vazio,
            vazio,
            vazio,
            html.Div("Ajuste os filtros para visualizar recomendacoes.", className="empty-state"),
        )

    agg = aggregate_pdv(filtered)

    receita_total = filtered["receita_liquida"].sum()
    ebitda_total = filtered["ebitda"].sum()
    lucro_total = filtered["lucro_liquido"].sum()
    lucro_oper_total = filtered["lucro_operacional"].sum()
    margem_oper = lucro_oper_total / receita_total if receita_total else 0.0
    qtd_criticos = int(agg["pdv_critico"].sum())

    return (
        brl(receita_total),
        pct(margem_oper),
        brl(ebitda_total),
        brl(lucro_total),
        str(qtd_criticos),
        fig_ranking(agg),
        fig_temporal(filtered, selected_pdv),
        fig_scatter(agg),
        fig_regional(filtered),
        recommendations_block(agg, selected_pdv),
    )


if __name__ == "__main__":
    app.run(debug=True)
