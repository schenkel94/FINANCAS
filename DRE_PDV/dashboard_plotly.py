# =============================
# BOARDROOM-LEVEL CHURN DASHBOARD
# =============================

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# =============================
# THEME
# =============================
BACKGROUND = "#0D1117"
CARD = "#161B22"
TEXT = "#E6EDF3"
ACCENT = "#58A6FF"
SUCCESS = "#2EA043"
WARNING = "#D29922"
DANGER = "#F85149"

PRIMARY_PAIN_LABEL = "Principal Dor do Cliente"

# =============================
# LOAD DATA
# =============================

def load_data():
    silver = pd.read_csv("churn_silver_2025.csv")
    gold = pd.read_csv("churn_gold_2025.csv")

    df = silver.merge(gold, on="id_cliente")

    df["probabilidade_churn"] = df["probabilidade_churn"].astype(float)
    df["valor_mensalidade"] = df["valor_mensalidade"].astype(float)
    df["score_sentimento_voc"] = df["score_sentimento_voc"].astype(float)

    return df

# =============================
# KPI / DRE
# =============================

def format_currency(v):
    return f"R$ {v:,.0f}".replace(",", ".")


def build_dre(df):
    receita = df["valor_mensalidade"].sum()
    risco = (df["valor_mensalidade"] * df["probabilidade_churn"]).sum()
    liquido = receita - risco

    return html.Div(className="kpi-row", children=[
        kpi("Receita Total", format_currency(receita)),
        kpi("Receita em Risco", format_currency(risco), DANGER),
        kpi("Receita Líquida", format_currency(liquido), SUCCESS),
    ])


def kpi(title, value, color=ACCENT):
    return html.Div(style={
        "background": CARD,
        "padding": "20px",
        "borderRadius": "16px"
    }, children=[
        html.Div(title, style={"color": "gray"}),
        html.H2(value, style={"color": color})
    ])

# =============================
# GRAPHS
# =============================

def revenue_vs_risk(df):
    g = df.groupby(PRIMARY_PAIN_LABEL).agg({
        "valor_mensalidade": "sum",
        "probabilidade_churn": "mean"
    }).reset_index()

    fig = go.Figure()

    fig.add_bar(x=g[PRIMARY_PAIN_LABEL], y=g["valor_mensalidade"], name="Receita")
    fig.add_scatter(x=g[PRIMARY_PAIN_LABEL], y=g["probabilidade_churn"], yaxis="y2", name="Risco")

    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color=TEXT),
        yaxis2=dict(overlaying="y", side="right", tickformat=".0%")
    )

    return fig


def churn_donut(df):
    c = df["previsao_final"].value_counts()

    return go.Figure(data=[go.Pie(
        labels=["OK", "Churn"],
        values=[c.get(0,0), c.get(1,0)],
        hole=0.6
    )])


def pareto(df):
    df = df.sort_values("probabilidade_churn", ascending=False)
    df["cum"] = df["valor_mensalidade"].cumsum()
    total = df["valor_mensalidade"].sum()

    fig = go.Figure()
    fig.add_scatter(y=df["cum"] / total)

    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color=TEXT)
    )

    return fig


def scatter(df):
    return px.scatter(
        df,
        x="score_sentimento_voc",
        y="probabilidade_churn",
        size="valor_mensalidade",
        color=PRIMARY_PAIN_LABEL
    )

# =============================
# INSIGHTS AUTOMÁTICOS
# =============================

def generate_insight(df):
    top = df.groupby(PRIMARY_PAIN_LABEL)["probabilidade_churn"].mean().idxmax()
    risk = df["probabilidade_churn"].mean()

    return f"Maior risco concentrado em: {top}. Risco médio da base: {risk:.1%}"

# =============================
# APP
# =============================

df = load_data()

app = Dash(__name__)

app.layout = html.Div(style={"background": BACKGROUND, "padding": "20px"}, children=[

    html.H1("Boardroom Churn Dashboard", style={"color": TEXT}),

    build_dre(df),

    html.Div(generate_insight(df), style={"color": "gray", "margin": "20px 0"}),

    html.Div([
        dcc.Graph(figure=revenue_vs_risk(df)),
        dcc.Graph(figure=churn_donut(df)),
        dcc.Graph(figure=pareto(df)),
        dcc.Graph(figure=scatter(df)),
    ])
])

# =============================
# RUN
# =============================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8050)))