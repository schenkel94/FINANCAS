from pathlib import Path
import pandas as pd
import numpy as np

from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

# =========================
# LOAD DATA
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "processed" / "dre_pdv_mensal_consolidado_com_acoes.csv"

df = pd.read_csv(DATA_PATH)
df["mes"] = pd.to_datetime(df["mes"])

# =========================
# APP
# =========================
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# =========================
# HELPERS
# =========================
def brl(v):
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pct(v):
    return f"{v*100:.1f}%".replace(".", ",")

# =========================
# LAYOUT
# =========================
app.layout = dbc.Container(fluid=True, className="app-bg", children=[

    # HEADER
    dbc.Row([
        dbc.Col(html.Div([
            html.H2("Financial Analytics SaaS", className="title"),
            html.P("DRE Inteligente por PDV", className="subtitle")
        ]))
    ]),

    # FILTERS
    dbc.Row([
        dbc.Col(dcc.Dropdown(
            options=[{"label": r, "value": r} for r in df["regiao"].unique()],
            multi=True,
            value=df["regiao"].unique(),
            id="regiao"
        ), md=3),

        dbc.Col(dcc.Dropdown(
            options=[{"label": c, "value": c} for c in df["canal"].unique()],
            multi=True,
            value=df["canal"].unique(),
            id="canal"
        ), md=3),
    ], className="filters"),

    # MAIN GRID
    dbc.Row([

        # =========================
        # LEFT (9 cols)
        # =========================
        dbc.Col([

            # KPIs
            dbc.Row([
                dbc.Col(html.Div(id="kpi-receita", className="kpi-card"), md=3),
                dbc.Col(html.Div(id="kpi-ebitda", className="kpi-card"), md=3),
                dbc.Col(html.Div(id="kpi-margem", className="kpi-card"), md=3),
                dbc.Col(html.Div(id="kpi-devol", className="kpi-card"), md=3),
            ]),

            # GRAPHS
            dbc.Row([
                dbc.Col(dcc.Graph(id="area-receita"), md=6),
                dbc.Col(dcc.Graph(id="donut-ebitda"), md=6),
            ])

        ], md=9),

        # =========================
        # RIGHT SIDEBAR (3 cols)
        # =========================
        dbc.Col([

            html.Div(id="dre", className="dre-card"),

            html.H5("PDVs Críticos"),
            html.Div(id="insights")

        ], md=3)

    ])

])

# =========================
# CALLBACK
# =========================
@app.callback(
    Output("kpi-receita", "children"),
    Output("kpi-ebitda", "children"),
    Output("kpi-margem", "children"),
    Output("kpi-devol", "children"),
    Output("area-receita", "figure"),
    Output("donut-ebitda", "figure"),
    Output("dre", "children"),
    Output("insights", "children"),

    Input("regiao", "value"),
    Input("canal", "value"),
)
def update(regiao, canal):

    dff = df[df["regiao"].isin(regiao) & df["canal"].isin(canal)]

    receita = dff["receita_liquida"].sum()
    ebitda = dff["ebitda"].sum()
    devol = dff["devolucoes"].sum()
    margem = ebitda / receita if receita else 0

    # KPI
    kpi1 = f"Receita\n{brl(receita)}"
    kpi2 = f"EBITDA\n{brl(ebitda)}"
    kpi3 = f"Margem\n{pct(margem)}"
    kpi4 = f"Devoluções\n{brl(devol)}"

    # AREA
    ts = dff.groupby("mes")["receita_liquida"].sum().reset_index()

    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        x=ts["mes"], y=ts["receita_liquida"],
        fill='tozeroy'
    ))
    fig_area.update_layout(template="plotly_dark")

    # DONUT
    canal_df = dff.groupby("canal")["ebitda"].sum().reset_index()
    fig_donut = px.pie(canal_df, names="canal", values="ebitda", hole=0.6)
    fig_donut.update_layout(template="plotly_dark")

    # DRE
    dre = html.Div([
        html.H4("DRE"),
        html.P(f"Receita Bruta: {brl(dff['receita_bruta'].sum())}"),
        html.P(f"(-) Devoluções: {brl(devol)}"),
        html.P(f"(=) Líquida: {brl(receita)}"),
        html.P(f"(-) CMV: {brl(dff['cmv'].sum())}"),
        html.P(f"(=) EBITDA: {brl(ebitda)}"),
    ])

    # INSIGHTS
    criticos = dff[dff["prioridade_risco"] == "alta"].head(5)

    insights = [
        html.Div([
            html.B(row["id_pdv"]),
            html.P(row["recomendacoes"])
        ]) for _, row in criticos.iterrows()
    ]

    return kpi1, kpi2, kpi3, kpi4, fig_area, fig_donut, dre, insights


if __name__ == "__main__":
    app.run(debug=True)