import pandas as pd
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from pathlib import Path

# --- SETUP ---
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "processed" / "dre_pdv_mensal_consolidado_com_acoes.csv"

df = pd.read_csv(DATA_PATH)
df['mes'] = pd.to_datetime(df['mes'])

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# --- LAYOUT ---
app.layout = dbc.Container(fluid=True, className="py-4", children=[
    
    # Header com Filtros
    dbc.Row([
        dbc.Col(html.H2("FINANCIAL PORTAL", className="fw-bold text-info"), width=4),
        dbc.Col(dcc.Dropdown(
            id='regiao-filter', 
            options=[{'label': r, 'value': r} for r in sorted(df['regiao'].unique())],
            multi=True, placeholder="Região", className="dash-dropdown"
        ), width=4),
        dbc.Col(dcc.Dropdown(
            id='canal-filter', 
            options=[{'label': c, 'value': c} for c in sorted(df['canal'].unique())],
            multi=True, placeholder="Canal", className="dash-dropdown"
        ), width=4),
    ], className="mb-4 g-3"),

    dbc.Row([
        # Main Dashboard
        dbc.Col(width=9, children=[
            # KPIs com a classe 'saas-card'
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.Small("RECEITA LÍQUIDA", className="text-muted"),
                    html.H3(id="kpi-rec", className="fw-bold")
                ]), className="saas-card")),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.Small("EBITDA", className="text-muted"),
                    html.H3(id="kpi-ebitda", className="fw-bold text-success")
                ]), className="saas-card")),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.Small("MARGEM LIQ.", className="text-muted"),
                    html.H3(id="kpi-margem", className="fw-bold text-info")
                ]), className="saas-card")),
            ], className="mb-4 g-3"),

            # Gráfico Principal
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6("Performance Mensal", className="text-muted mb-3"),
                    dcc.Graph(id='trend-chart', config={'displayModeBar': False})
                ]), className="saas-card"), width=12),
            ]),
        ]),

        # DRE Lateral com a classe 'dre-container'
        dbc.Col(width=3, children=[
            dbc.Card(dbc.CardBody([
                html.H5("DRE DINÂMICO", className="text-center mb-4"),
                html.Div(id='dre-lateral-content', className="dre-container")
            ]), className="saas-card h-100")
        ])
    ])
])

# --- CALLBACK ---
@app.callback(
    [Output('kpi-rec', 'children'), Output('kpi-ebitda', 'children'), 
     Output('kpi-margem', 'children'), Output('trend-chart', 'figure'), 
     Output('dre-lateral-content', 'children')],
    [Input('regiao-filter', 'value'), Input('canal-filter', 'value')]
)
def update_dashboard(regiao, canal):
    dff = df.copy()
    if regiao: dff = dff[dff['regiao'].isin(regiao)]
    if canal: dff = dff[dff['canal'].isin(canal)]

    # Cálculos
    rec = dff['receita_liquida'].sum()
    ebitda = dff['ebitda'].sum()
    margem = (dff['lucro_liquido'].sum() / rec * 100) if rec > 0 else 0

    # Gráfico SaaS (Área Azul)
    df_t = dff.groupby('mes')['receita_liquida'].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_t['mes'], y=df_t['receita_liquida'], fill='tozeroy', line_color='#58a6ff'))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                      margin=dict(l=0, r=0, t=0, b=0), height=300)

    # DRE Lateral
    dre_items = [
        ("Receita Bruta", dff['receita_bruta'].sum(), False),
        ("(-) Devoluções", dff['devolucoes'].sum() * -1, False),
        ("(=) Receita Líquida", rec, True),
        ("(-) CMV", dff['cmv'].sum() * -1, False),
        ("(=) Lucro Bruto", dff['lucro_bruto'].sum(), True),
        ("(=) EBITDA", ebitda, True),
    ]
    
    dre_html = [
        html.Div([
            html.Span(label),
            html.Span(f"R$ {val:,.0f}")
        ], className=f"dre-row {'dre-total' if bold else ''}") 
        for label, val, bold in dre_items
    ]

    return (f"R$ {rec/1e6:.1f}M", f"R$ {ebitda/1e6:.1f}M", f"{margem:.1f}%", fig, dre_html)

if __name__ == '__main__':
    app.run_server(debug=True)