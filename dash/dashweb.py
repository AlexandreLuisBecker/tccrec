import dash
from dash import dcc, html, Input, Output, State
import dash.dash_table as dash_table
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import tempfile
import base64
import os

file_path = 'dash/registro.xlsx'
df = pd.read_excel(file_path)

df['Data_Hora'] = pd.to_datetime(df['Data_Hora'], errors='coerce')

def dentro_da_tolerancia(horario, registro, tolerancia=pd.Timedelta(minutes=5)):
    horario_dt = pd.to_datetime(horario.strftime('%H:%M:%S'))
    registro_dt = pd.to_datetime(registro.strftime('%H:%M:%S'))
    horario_min = horario_dt - tolerancia
    horario_max = horario_dt + tolerancia
    return horario_min <= registro_dt <= horario_max

horario_entrada = pd.to_datetime("07:00:00").time()
horario_intervalo_inicio = pd.to_datetime("12:00:00").time()
horario_intervalo_fim = pd.to_datetime("13:00:00").time()
horario_saida = pd.to_datetime("17:00:00").time()

def calcular_status_individual(row):
    if pd.isna(row['Data_Hora']):
        return 'Incompleto'

    if dentro_da_tolerancia(horario_entrada, row['Data_Hora']):
        return 'Entrada Correta'
    elif dentro_da_tolerancia(horario_intervalo_inicio, row['Data_Hora']):
        return 'Intervalo Iniciado'
    elif dentro_da_tolerancia(horario_intervalo_fim, row['Data_Hora']):
        return 'Intervalo Finalizado'
    elif dentro_da_tolerancia(horario_saida, row['Data_Hora']):
        return 'Saida Correta'
    else:
        return 'Irregular'

df['Status'] = df.apply(calcular_status_individual, axis=1)

app = dash.Dash(__name__, suppress_callback_exceptions=True)

# ====== Estilos base (fixam altura e evitam “crescimento infinito”) ======
PAGE_BG = '#f9f9f9'
PRIMARY = '#1a237e'

GRAPH_CONTAINER_STYLE = {
    'display': 'flex',
    'gap': '16px',
    'justify-content': 'space-between',
    'align-items': 'stretch',
    'flex-wrap': 'wrap',        # quebra em telas menores
    'maxWidth': '1200px',
    'margin': '0 auto',
    'padding': '0 16px'
}

GRAPH_CARD_STYLE = {
    'flex': '1 1 520px',        # duas colunas quando der, senão quebra
    'minWidth': '320px',
    'backgroundColor': '#ffffff',
    'borderRadius': '10px',
    'boxShadow': '0px 2px 10px rgba(0,0,0,0.08)',
    'padding': '12px'
}

# Altura fixa do gráfico (o mais importante!)
GRAPH_STYLE = {
    'height': '420px'           # trava o crescimento
}

GRAPH_CONFIG = {
    'displayModeBar': False,
    'responsive': True
}

def layout_login():
    return html.Div(
        style={
            'backgroundColor': '#e8eaf6',
            'fontFamily': 'Arial',
            'display': 'flex',
            'justify-content': 'center',
            'alignItems': 'center',
            'height': '100vh'
        },
        children=[
            html.Div(
                style={
                    'padding': '40px',
                    'borderRadius': '8px',
                    'backgroundColor': '#ffffff',
                    'boxShadow': '0px 4px 8px rgba(0, 0, 0, 0.2)',
                    'width': '300px',
                    'textAlign': 'center'
                },
                children=[
                    html.H2("Login", style={'color': PRIMARY, 'margin-bottom': '20px'}),
                    dcc.Input(
                        id='username',
                        type='text',
                        placeholder='Usuário',
                        style={'width': '100%', 'padding': '10px', 'margin-bottom': '10px', 'borderRadius': '5px'}
                    ),
                    dcc.Input(
                        id='password',
                        type='password',
                        placeholder='Senha',
                        style={'width': '100%', 'padding': '10px', 'margin-bottom': '20px', 'borderRadius': '5px'}
                    ),
                    html.Button(
                        'Entrar',
                        id='login-button',
                        n_clicks=0,
                        style={'width': '100%', 'padding': '10px', 'backgroundColor': PRIMARY, 'color': 'white', 'border': 'none', 'borderRadius': '5px'}
                    ),
                    html.Div(id='login-message', style={'color': 'red', 'margin-top': '10px'})
                ]
            )
        ]
    )

def layout_dashboard():
    min_dt = df['Data_Hora'].min()
    max_dt = df['Data_Hora'].max()

    # fallback se o excel vier vazio/NaT
    start_date = min_dt.date() if pd.notna(min_dt) else pd.Timestamp.today().date()
    end_date = max_dt.date() if pd.notna(max_dt) else pd.Timestamp.today().date()

    return html.Div(
        style={'backgroundColor': PAGE_BG, 'fontFamily': 'Arial', 'minHeight': '100vh'},
        children=[
            html.H1("Controle de Ponto Empresarial", style={'textAlign': 'center', 'color': PRIMARY, 'padding': '16px 0', 'margin': '0'}),

            # ====== GRÁFICOS (com altura fixa) ======
            html.Div(
                style=GRAPH_CONTAINER_STYLE,
                children=[
                    html.Div(
                        style=GRAPH_CARD_STYLE,
                        children=[
                            dcc.Graph(id='total-horas', style=GRAPH_STYLE, config=GRAPH_CONFIG)
                        ]
                    ),
                    html.Div(
                        style=GRAPH_CARD_STYLE,
                        children=[
                            dcc.Graph(id='grafico-irregularidades', style=GRAPH_STYLE, config=GRAPH_CONFIG)
                        ]
                    )
                ]
            ),

            # ====== FILTROS ======
            html.Div(
                style={'textAlign': 'center', 'marginTop': '22px', 'maxWidth': '1200px', 'margin': '22px auto 0 auto', 'padding': '0 16px'},
                children=[
                    html.H2("Filtros", style={'color': PRIMARY, 'marginBottom': '12px'}),
                    html.Div(
                        style={'display': 'flex', 'gap': '12px', 'justifyContent': 'center', 'flexWrap': 'wrap'},
                        children=[
                            dcc.Dropdown(
                                id='dropdown-funcionario',
                                options=[{'label': nome, 'value': nome} for nome in sorted(df['Nome'].dropna().unique())],
                                value=None,
                                placeholder="Selecione um Funcionário",
                                style={'width': '420px', 'minWidth': '280px'}
                            ),
                            dcc.DatePickerRange(
                                id='date-picker-range',
                                start_date=start_date,
                                end_date=end_date,
                                display_format='DD-MM-YYYY'
                            ),
                        ]
                    ),
                ]
            ),

            # ====== TABELA + PDF ======
            html.Div(
                style={'margin': '32px auto', 'maxWidth': '1200px', 'padding': '0 16px'},
                children=[
                    html.H2("Detalhamento do ponto", style={'color': PRIMARY}),
                    dash_table.DataTable(
                        id='tabela-detalhada',
                        columns=[{"name": i, "id": i} for i in ['Nome', 'Cargo', 'Data_Hora', 'Status']],
                        page_size=10,
                        style_table={'height': '420px', 'overflowY': 'auto'},
                        style_cell={
                            'textAlign': 'center',
                            'padding': '10px',
                            'backgroundColor': '#f2f2f2',
                            'color': PRIMARY
                        },
                        style_header={
                            'backgroundColor': PRIMARY,
                            'color': 'white',
                            'fontWeight': 'bold'
                        }
                    ),
                    html.A(
                        "Relatório PDF",
                        id="download-link-pdf",
                        download="relatorio_presenca.pdf",
                        href="",
                        target="_blank",
                        style={'marginTop': '16px', 'display': 'block', 'textAlign': 'center', 'color': PRIMARY, 'fontWeight': 'bold'}
                    )
                ]
            )
        ]
    )

login_layout = layout_login()
dashboard_layout = layout_dashboard()

app.layout = html.Div(id='page-content', children=[login_layout])

@app.callback(
    Output('page-content', 'children'),
    [Input('login-button', 'n_clicks')],
    [State('username', 'value'), State('password', 'value')]
)
def realizar_login(n_clicks, username, password):
    if n_clicks > 0:
        if username == "admin" and password == "1234":
            return dashboard_layout
        else:
            return html.Div(children=[
                login_layout,
                html.Div('Usuário ou senha inválidos.', style={'color': 'red', 'textAlign': 'center', 'marginTop': '10px'})
            ])
    return login_layout

@app.callback(
    Output('total-horas', 'figure'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def atualizar_total_horas(start_date, end_date):
    try:
        df_filtrado = df[(df['Data_Hora'] >= pd.to_datetime(start_date)) &
                         (df['Data_Hora'] <= pd.to_datetime(end_date))]

        df_irregulares = df_filtrado[df_filtrado['Status'] == 'Irregular']
        total_irregularidades = df_irregulares.groupby('Nome').size().reset_index(name='Total Irregularidades')

        if total_irregularidades.empty:
            fig = px.bar(title="Nenhuma irregularidade registrada no período", template='plotly_white')
            fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
            return fig

        funcionario_max = total_irregularidades.loc[total_irregularidades['Total Irregularidades'].idxmax()]

        grafico = px.bar(
            total_irregularidades,
            x='Nome',
            y='Total Irregularidades',
            title='Funcionários com mais Irregularidades',
            labels={'Nome': 'Funcionário', 'Total Irregularidades': 'Quantidade'},
            template='plotly_white'
        )

        grafico.add_annotation(
            x=funcionario_max['Nome'],
            y=funcionario_max['Total Irregularidades'],
            text='Maior Irregularidade',
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40
        )

        grafico.update_layout(
            height=420,
            title_font_size=20,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        return grafico

    except Exception:
        fig = px.bar(title="Erro ao atualizar gráfico", template='plotly_white')
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
        return fig

@app.callback(
    Output('grafico-irregularidades', 'figure'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def atualizar_grafico_irregularidades(start_date, end_date):
    df_filtrado = df[(df['Data_Hora'] >= pd.to_datetime(start_date)) &
                     (df['Data_Hora'] <= pd.to_datetime(end_date))]

    contagem_irregularidades = df_filtrado['Status'].value_counts().reset_index()
    contagem_irregularidades.columns = ['Status', 'Quantidade']

    grafico = px.pie(
        contagem_irregularidades,
        names='Status',
        values='Quantidade',
        title='Total de Status por Tipo',
        labels={'Status': 'Tipo de Status', 'Quantidade': 'Quantidade'},
        template='plotly_white'
    )

    grafico.update_layout(
        height=420,
        title_font_size=20,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return grafico

@app.callback(
    Output('tabela-detalhada', 'data'),
    [Input('dropdown-funcionario', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def atualizar_tabela(funcionario, start_date, end_date):
    df_filtrado = df[(df['Data_Hora'] >= pd.to_datetime(start_date)) &
                     (df['Data_Hora'] <= pd.to_datetime(end_date))].copy()

    if funcionario:
        df_filtrado = df_filtrado[df_filtrado['Nome'] == funcionario].copy()

    df_filtrado['Data_Hora'] = df_filtrado['Data_Hora'].dt.strftime('%d/%m/%Y %H:%M:%S')
    return df_filtrado[['Nome', 'Cargo', 'Data_Hora', 'Status']].to_dict('records')

@app.callback(
    Output("download-link-pdf", "href"),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('dropdown-funcionario', 'value')]
)
def gerar_pdf(start_date, end_date, nome_usuario):
    if not nome_usuario:
        return ""

    df_filtrado = df[
        (df['Data_Hora'] >= pd.to_datetime(start_date)) &
        (df['Data_Hora'] <= pd.to_datetime(end_date)) &
        (df['Nome'] == nome_usuario)
    ].copy()

    if df_filtrado.empty:
        return ""

    pdf = FPDF(format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    nome_empresa = "Nome da Empresa"
    pdf.cell(200, 10, txt=nome_empresa, ln=True, align='C')
    pdf.cell(200, 10, txt="Folha Ponto", ln=True, align='C')

    funcao_usuario = df[df['Nome'] == nome_usuario]['Cargo'].values[0]
    pdf.cell(200, 10, txt=f"Colaborador: {nome_usuario}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Função: {funcao_usuario}", ln=True, align='C')

    start_date_br = pd.to_datetime(start_date).strftime('%d/%m/%Y')
    end_date_br = pd.to_datetime(end_date).strftime('%d/%m/%Y')
    pdf.cell(0, 10, txt=f"Período: {start_date_br} a {end_date_br}", ln=True, align='C')
    pdf.ln(4)

    pdf.set_font("Arial", size=10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, txt="Data e Hora", border=1, align='C', fill=True)
    pdf.cell(90, 10, txt="Status", border=1, align='C', fill=True)
    pdf.ln()

    for _, row in df_filtrado.iterrows():
        data_hora = row['Data_Hora'].strftime('%d/%m/%Y %H:%M:%S')
        status = str(row['Status'])
        pdf.cell(100, 7, txt=data_hora, border=1, align='C')
        pdf.cell(90, 7, txt=status, border=1, align='C')
        pdf.ln()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        temp_name = temp_file.name
        pdf.output(temp_name)

    with open(temp_name, 'rb') as f:
        pdf_data = f.read()

    try:
        os.remove(temp_name)
    except Exception:
        pass

    pdf_base64 = base64.b64encode(pdf_data).decode()
    return f"data:application/pdf;base64,{pdf_base64}"

if __name__ == '__main__':
    app.run(debug=True)
