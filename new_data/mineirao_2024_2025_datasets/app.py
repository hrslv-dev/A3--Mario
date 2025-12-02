import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc
from dash import html
from plotly.subplots import make_subplots
import io

# --- 1. CONFIGURAÇÃO E CARREGAMENTO DE DADOS ---
# IDs dos arquivos carregados pelo usuário
# NOTA: Estes IDs são placeholders e dependem do ambiente de execução.
# Em um ambiente real (fora deste chat), você usaria os nomes dos arquivos CSV.
files = {
    "dim_canal.csv": "uploaded:dim_canal.csv",
    "dim_data.csv": "uploaded:dim_data.csv",
    "dim_perfil_torcedor.csv": "uploaded:dim_perfil_torcedor.csv",
    "dim_produto.csv": "uploaded:dim_produto.csv",
    "dim_setor.csv": "uploaded:dim_setor.csv",
    "fato_consumo.csv": "uploaded:fato_consumo.csv",
    "fato_jogos.csv": "uploaded:fato_jogos.csv",
    "fato_mercado_ingressos.csv": "uploaded:fato_mercado_ingressos.csv",
    "fato_mobilidade_incidentes.csv": "uploaded:fato_mobilidade_incidentes.csv",
    "fato_projecao.csv": "uploaded:fato_projecao.csv",
    "dim_adversario.csv": "uploaded:dim_adversario.csv",
    "fato_receita_agregada.csv": "uploaded:fato_receita_agregada.csv"
}

# Função auxiliar para carregar e limpar dados
def load_and_clean(file_id):
    try:
        # Tenta carregar usando o ID de arquivo do ambiente
        df = pd.read_csv(file_id, sep=';', decimal=',')
    except:
        # Tenta carregar localmente caso o ID de arquivo falhe (você pode substituir isso
        # pela leitura direta do nome do arquivo se os CSVs estiverem na mesma pasta)
        df = pd.read_csv(file_id.split(':')[-1], delimiter=';', decimal=',')

    # Limpeza e conversão de colunas numéricas
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['receita', 'publico', 'ticket', 'tempo', 'consumo', 'capacidade', 'taxa', 'preco', 'socios', 'adesoes', 'vendas', 'min']):
            try:
                # Substitui vírgula por ponto para conversão em float
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False).astype(float)
            except:
                pass
    return df

# Carregamento de todos os arquivos
# NOTE: Certifique-se de que os arquivos CSV estejam na mesma pasta que o app.py
dataframes = {name.replace('.csv', ''): load_and_clean(id) for name, id in files.items()}


# --- 2. CONSOLIDAÇÃO E CRIAÇÃO DA TABELA MESTRE (df_dashboard) ---

# Renomear colunas para padronizar
dataframes['fato_jogos'] = dataframes['fato_jogos'].rename(columns={
    'receita_ingresso_mil_rs': 'receita_ingresso_mil_rs_real',
    'publico_pago': 'publico_pago_real'
})
dataframes['fato_projecao'] = dataframes['fato_projecao'].rename(columns={
    'publico_projetado': 'publico_pago_projetado',
    'receita_projetada_mil_rs': 'receita_ingresso_mil_rs_projetada'
})

# Agregação de Fato_Consumo
df_consumo_agg = dataframes['fato_consumo'].groupby('jogo_id').agg(
    receita_total_consumo_rs=('receita_produto_rs', 'sum')
).reset_index()

# Merge Inicial: Fato_Jogos com Dimensões
df_master = dataframes['fato_jogos'].merge(
    dataframes['dim_data'][['data_id', 'data']],
    on='data_id', how='left'
)
df_master = df_master.merge(
    dataframes['dim_adversario'][['adversario_id', 'nome_adversario', 'competicao', 'nivel_confronto', 'classico_local']],
    on='adversario_id', how='left'
)
df_master = df_master.merge(
    dataframes['fato_projecao'][['jogo_id', 'publico_pago_projetado', 'receita_ingresso_mil_rs_projetada']],
    on='jogo_id', how='left'
)
df_master = df_master.merge(df_consumo_agg, on='jogo_id', how='left')

# Ingressos e Mobilidade (Agregados)
df_ingressos_agg = dataframes['fato_mercado_ingressos'].groupby('data_id').agg(
    socios_ativos_dia=('socios_ativos', 'max'),
    novas_adesoes_dia=('novas_adesoes', 'max'),
    vendas_total_ingressos=('vendas_canal', 'sum')
).reset_index()
df_mobilidade_agg = dataframes['fato_mobilidade_incidentes'].groupby('jogo_id').agg(
    tempo_entrada_medio_min=('tempo_entrada_medio_min', 'mean'),
    tempo_saida_medio_min=('tempo_saida_medio_min', 'mean'),
    incidentes_total=('incidente_contagem', 'sum')
).reset_index()
df_master = df_master.merge(df_ingressos_agg, on='data_id', how='left')
df_master = df_master.merge(df_mobilidade_agg, on='jogo_id', how='left')

# Cálculo de Métricas Derivadas (KPIs)
df_master['receita_total_consumo_mil_rs'] = df_master['receita_total_consumo_rs'] / 1000
df_master['receita_total_mil_rs_real'] = df_master['receita_ingresso_mil_rs_real'] + df_master['receita_total_consumo_mil_rs'].fillna(0)
df_master['gap_publico_pago_perc'] = ((df_master['publico_pago_real'] - df_master['publico_pago_projetado']) / df_master['publico_pago_projetado']) * 100
df_master['gap_publico_pago_perc'] = df_master['gap_publico_pago_perc'].replace([np.inf, -np.inf], np.nan).round(2)
df_master['ticket_medio_consumo_rs_real'] = df_master['receita_total_consumo_rs'] / df_master['publico_pago_real']
df_master['ticket_medio_total_rs'] = df_master['ticket_medio_ingresso_rs'] + df_master['ticket_medio_consumo_rs_real'].fillna(0)

df_master['data_jogo'] = pd.to_datetime(df_master['data']).dt.date
df_dashboard = df_master.copy()

# Dataframes Detalhe para Painéis 2 e 3
df_consumo_detalhe = dataframes['fato_consumo'].merge(dataframes['dim_produto'], on='produto_id', how='left')
df_ingressos_canal = dataframes['fato_mercado_ingressos'].merge(dataframes['dim_canal'], on='canal_id', how='left')
df_mobilidade_detalhe = dataframes['fato_mobilidade_incidentes'].merge(dataframes['dim_setor'], on='setor_id', how='left')
df_perfil = dataframes['dim_perfil_torcedor']


# --- 3. GERAÇÃO DAS 9 FIGURAS PLOTLY ---

# --- PAINEL 1 ---
fig1 = px.bar(
    df_dashboard.sort_values('data_jogo'),
    x='data_jogo',
    y=['publico_pago_real', 'publico_pago_projetado'],
    barmode='group',
    labels={'value': 'Público Pago (Pessoas)', 'variable': 'Métrica'},
    title='1. Comparativo de Público Pago: Realizado vs. Projetado'
)
fig1.update_layout(hovermode="x unified")

fig2 = px.line(
    df_dashboard.sort_values('data_jogo'),
    x='data_jogo',
    y='ticket_medio_total_rs',
    title='2. Evolução do Ticket Médio Total (Ingresso + Consumo)',
    labels={'data_jogo': 'Data do Jogo', 'ticket_medio_total_rs': 'Ticket Médio Total (R$)'},
    markers=True,
    color_discrete_sequence=['#F6511D']
)
fig2.update_layout(hovermode="x unified")

order = ['Grande', 'Medio', 'Pequeno', 'Classico']
df_box = df_dashboard.copy()
df_box['nivel_confronto'] = pd.Categorical(df_box['nivel_confronto'], categories=order, ordered=True)
df_box = df_box.sort_values('nivel_confronto')

fig3 = px.box(
    df_box.dropna(subset=['receita_total_mil_rs_real']),
    x='nivel_confronto',
    y='receita_total_mil_rs_real',
    color='nivel_confronto',
    title='3. Distribuição da Receita Total (Milhões de R$) por Nível de Confronto',
    labels={'nivel_confronto': 'Nível do Confronto', 'receita_total_mil_rs_real': 'Receita Total (Milhões de R$)'},
)

# --- PAINEL 2 ---
df_receita_categoria = df_consumo_detalhe.groupby('categoria')['receita_produto_rs'].sum().reset_index()
df_receita_categoria['receita_produto_mil_rs'] = df_receita_categoria['receita_produto_rs'] / 1000

fig4 = px.pie(
    df_receita_categoria,
    values='receita_produto_mil_rs',
    names='categoria',
    title='4. Distribuição da Receita de Consumo por Categoria',
    hole=.3, 
    color_discrete_sequence=px.colors.qualitative.Pastel
)
fig4.update_traces(textposition='inside', textinfo='percent+label')

df_top_itens = df_consumo_detalhe.groupby('item_vendido')['receita_produto_rs'].sum().reset_index()
df_top_itens = df_top_itens.sort_values(by='receita_produto_rs', ascending=False).head(5)
df_top_itens['receita_produto_mil_rs'] = df_top_itens['receita_produto_rs'] / 1000

fig5 = px.bar(
    df_top_itens,
    x='item_vendido',
    y='receita_produto_mil_rs',
    title='5. Top 5 Itens Vendidos por Receita Total',
    labels={'item_vendido': 'Item', 'receita_produto_mil_rs': 'Receita Total (Milhares de R$)'},
    color='item_vendido',
    color_discrete_sequence=px.colors.qualitative.Dark2
)

df_vendas_tipo = df_ingressos_canal.groupby('tipo_operacao')['vendas_canal'].sum().reset_index()

fig6 = px.bar(
    df_vendas_tipo,
    x='tipo_operacao',
    y='vendas_canal',
    title='6. Volume Total de Vendas de Ingressos por Tipo de Canal',
    labels={'tipo_operacao': 'Tipo de Operação', 'vendas_canal': 'Total de Ingressos Vendidos'},
    color='tipo_operacao',
    color_discrete_sequence=['#4B0082', '#00BFFF']
)

# --- PAINEL 3 ---
df_mobilidade_agg_setor = df_mobilidade_detalhe.groupby('nome_setor').agg(
    tempo_entrada_medio=('tempo_entrada_medio_min', 'mean'),
    tempo_saida_medio=('tempo_saida_medio_min', 'mean'),
).reset_index()

fig7 = px.bar(
    df_mobilidade_agg_setor,
    x='nome_setor',
    y=['tempo_entrada_medio', 'tempo_saida_medio'],
    barmode='group',
    title='7. Tempo Médio de Entrada e Saída por Setor (Minutos)',
    labels={'value': 'Tempo Médio (Minutos)', 'variable': 'Métrica de Tempo', 'nome_setor': 'Setor'},
    color_discrete_map={'tempo_entrada_medio': '#3CB371', 'tempo_saida_medio': '#FFA07A'}
)

df_incidentes_agg_setor = df_mobilidade_detalhe.groupby('nome_setor').agg(
    incidentes_total=('incidente_contagem', 'sum'),
    tempo_resposta_medio=('tempo_resposta_min', 'mean'),
    publico_total=('publico_setor', 'sum') 
).reset_index()

fig8 = px.scatter(
    df_incidentes_agg_setor,
    x='tempo_resposta_medio',
    y='incidentes_total',
    size='publico_total', 
    color='nome_setor',
    hover_name='nome_setor',
    title='8. Análise de Incidentes: Total vs. Tempo Médio de Resposta por Setor',
    labels={'tempo_resposta_medio': 'Tempo Médio de Resposta (Minutos)', 'incidentes_total': 'Total de Incidentes', 'publico_total': 'Público Total Acumulado'},
    size_max=50
)

df_faixa_etaria = df_perfil.groupby('faixa_etaria').size().reset_index(name='contagem')
age_order = ['18-24 anos', '25-34 anos', '35-44 anos', '45-59 anos', '60+ anos']
df_faixa_etaria['faixa_etaria'] = pd.Categorical(df_faixa_etaria['faixa_etaria'], categories=age_order, ordered=True)
df_faixa_etaria = df_faixa_etaria.sort_values('faixa_etaria')

fig9 = px.pie(
    df_faixa_etaria,
    values='contagem',
    names='faixa_etaria',
    title='9. Distribuição do Público por Faixa Etária',
    hole=.4,
    color_discrete_sequence=px.colors.qualitative.Vivid
)
fig9.update_traces(textposition='inside', textinfo='percent+label')


# --- 4. ESTRUTURA DASH E LAYOUT HTML ---

# Inicializar o aplicativo Dash
app = dash.Dash(__name__)

# Estilo para os cards do dashboard (simula um design mais limpo e moderno)
card_style = {
    'backgroundColor': '#ffffff',
    'padding': '15px',
    'borderRadius': '10px',
    'boxShadow': '0 4px 12px 0 rgba(0,0,0,0.1)',
    'margin': '15px'
}

# Definição do Layout (HTML)
app.layout = html.Div(style={'backgroundColor': '#f0f2f5', 'fontFamily': 'Arial, sans-serif'}, children=[

    # Cabeçalho Principal
    html.H1(
        children='🏟️ Dashboard de Desempenho e Operações do Estádio',
        style={
            'textAlign': 'center',
            'color': '#1f2f4f',
            'padding': '30px',
            'backgroundColor': '#ffffff',
            'marginBottom': '0'
        }
    ),
    
    # --- PAINEL 1: Desempenho Financeiro e de Público ---
    html.Div(style={'padding': '10px 20px'}, children=[
        html.H2('📊 PAINEL 1: Desempenho Financeiro e de Público', style={'color': '#1f2f4f', 'textAlign': 'left', 'paddingTop': '10px'}),
        
        # Linha 1: Gráficos 1 e 2
        html.Div(style={'display': 'flex', 'flexDirection': 'row', 'flexWrap': 'wrap'}, children=[
            # Gráfico 1: Público Real vs. Projetado
            html.Div(style={'width': '50%', **card_style}, children=[
                dcc.Graph(id='grafico-publico', figure=fig1)
            ]),
            # Gráfico 2: Evolução do Ticket Médio Total
            html.Div(style={'width': '50%', **card_style}, children=[
                dcc.Graph(id='grafico-ticket-medio', figure=fig2)
            ])
        ]),
        
        # Linha 2: Gráfico 3
        html.Div(style={'padding': '0 15px'}, children=[
            html.Div(style={**card_style, 'width': '100%', 'margin': '0'}, children=[
                dcc.Graph(id='grafico-receita-confronto', figure=fig3)
            ])
        ])
    ]),
    
    html.Hr(style={'borderColor': '#ccc', 'margin': '20px'}),
    
    # --- PAINEL 2: Detalhe do Consumo e Mercados ---
    html.Div(style={'padding': '10px 20px'}, children=[
        html.H2('🛒 PAINEL 2: Detalhe do Consumo e Mercados', style={'color': '#1f2f4f', 'textAlign': 'left', 'paddingTop': '10px'}),
        
        # Linha 3: Gráficos 4, 5 e 6
        html.Div(style={'display': 'flex', 'flexDirection': 'row', 'flexWrap': 'wrap'}, children=[
            # Gráfico 4: Receita por Categoria (Rosca)
            html.Div(style={'width': '33.33%', **card_style}, children=[
                dcc.Graph(id='grafico-receita-categoria', figure=fig4)
            ]),
            # Gráfico 5: Top 5 Itens
            html.Div(style={'width': '33.33%', **card_style}, children=[
                dcc.Graph(id='grafico-top-itens', figure=fig5)
            ]),
            # Gráfico 6: Vendas por Canal
            html.Div(style={'width': '33.33%', **card_style}, children=[
                dcc.Graph(id='grafico-vendas-canal', figure=fig6)
            ])
        ])
    ]),

    html.Hr(style={'borderColor': '#ccc', 'margin': '20px'}),

    # --- PAINEL 3: Setor, Perfil e Mobilidade ---
    html.Div(style={'padding': '10px 20px'}, children=[
        html.H2('🚧 PAINEL 3: Setor, Perfil e Mobilidade', style={'color': '#1f2f4f', 'textAlign': 'left', 'paddingTop': '10px'}),
        
        # Linha 4: Gráficos 7 e 8
        html.Div(style={'display': 'flex', 'flexDirection': 'row', 'flexWrap': 'wrap'}, children=[
            # Gráfico 7: Tempo Médio de Entrada/Saída
            html.Div(style={'width': '50%', **card_style}, children=[
                dcc.Graph(id='grafico-mobilidade', figure=fig7)
            ]),
            # Gráfico 8: Incidentes vs. Tempo de Resposta
            html.Div(style={'width': '50%', **card_style}, children=[
                dcc.Graph(id='grafico-incidentes', figure=fig8)
            ])
        ]),
        
        # Linha 5: Gráfico 9
        html.Div(style={'padding': '0 15px'}, children=[
            html.Div(style={**card_style, 'width': '100%', 'margin': '0'}, children=[
                dcc.Graph(id='grafico-faixa-etaria', figure=fig9)
            ])
        ])
    ]),
    
    # Rodapé simples
    html.Div(style={'textAlign': 'center', 'padding': '20px', 'fontSize': '0.8em', 'color': '#777'}, children=[
        html.P('Análise de Dados do Estádio - Implementação Plotly Dash. Desenvolvido em Python.')
    ])
])

# 5. Rodar o servidor
if __name__ == '__main__':
    # O dashboard estará acessível em http://127.0.0.1:8050/
    app.run(debug=True)