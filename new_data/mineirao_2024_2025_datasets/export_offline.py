import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

# --- 1. CONFIGURAÇÃO E CARREGAMENTO DE DADOS ---
# Use o mesmo carregamento de dados e processamento do script anterior
files = {
    "dim_canal.csv": "uploaded:dim_canal.csv", "dim_data.csv": "uploaded:dim_data.csv",
    "dim_perfil_torcedor.csv": "uploaded:dim_perfil_torcedor.csv", "dim_produto.csv": "uploaded:dim_produto.csv",
    "dim_setor.csv": "uploaded:dim_setor.csv", "fato_consumo.csv": "uploaded:fato_consumo.csv",
    "fato_jogos.csv": "uploaded:fato_jogos.csv", "fato_mercado_ingressos.csv": "uploaded:fato_mercado_ingressos.csv",
    "fato_mobilidade_incidentes.csv": "uploaded:fato_mobilidade_incidentes.csv", "fato_projecao.csv": "uploaded:fato_projecao.csv",
    "dim_adversario.csv": "uploaded:dim_adversario.csv", "fato_receita_agregada.csv": "uploaded:fato_receita_agregada.csv"
}

def load_and_clean(file_id):
    try:
        df = pd.read_csv(file_id, sep=';', decimal=',')
    except:
        file_name = file_id.split(':')[-1] if ':' in file_id else file_id
        df = pd.read_csv(file_name, delimiter=';', decimal=',')

    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['receita', 'publico', 'ticket', 'tempo', 'consumo', 'capacidade', 'taxa', 'preco', 'socios', 'adesoes', 'vendas', 'min']):
            try:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False).astype(float)
            except:
                pass
    return df

dataframes = {name.replace('.csv', ''): load_and_clean(id) for name, id in files.items()}

# --- 2. CONSOLIDAÇÃO E CRIAÇÃO DA TABELA MESTRE (df_dashboard) ---
# (Manter a lógica de processamento de dados para gerar df_dashboard, df_consumo_detalhe, etc.)
# ... [Lógica de processamento de dados completa do script anterior] ...
dataframes['fato_jogos'] = dataframes['fato_jogos'].rename(columns={'receita_ingresso_mil_rs': 'receita_ingresso_mil_rs_real','publico_pago': 'publico_pago_real'})
dataframes['fato_projecao'] = dataframes['fato_projecao'].rename(columns={'publico_projetado': 'publico_pago_projetado','receita_projetada_mil_rs': 'receita_ingresso_mil_rs_projetada'})
df_consumo_agg = dataframes['fato_consumo'].groupby('jogo_id').agg(receita_total_consumo_rs=('receita_produto_rs', 'sum')).reset_index()
df_master = dataframes['fato_jogos'].merge(dataframes['dim_data'][['data_id', 'data']], on='data_id', how='left')
df_master = df_master.merge(dataframes['dim_adversario'][['adversario_id', 'nome_adversario', 'competicao', 'nivel_confronto', 'classico_local']], on='adversario_id', how='left')
df_master = df_master.merge(dataframes['fato_projecao'][['jogo_id', 'publico_pago_projetado', 'receita_ingresso_mil_rs_projetada']], on='jogo_id', how='left')
df_master = df_master.merge(df_consumo_agg, on='jogo_id', how='left')
df_ingressos_agg = dataframes['fato_mercado_ingressos'].groupby('data_id').agg(socios_ativos_dia=('socios_ativos', 'max'), novas_adesoes_dia=('novas_adesoes', 'max'), vendas_total_ingressos=('vendas_canal', 'sum')).reset_index()
df_mobilidade_agg = dataframes['fato_mobilidade_incidentes'].groupby('jogo_id').agg(tempo_entrada_medio_min=('tempo_entrada_medio_min', 'mean'), tempo_saida_medio_min=('tempo_saida_medio_min', 'mean'), incidentes_total=('incidente_contagem', 'sum')).reset_index()
df_master = df_master.merge(df_ingressos_agg, on='data_id', how='left')
df_master = df_master.merge(df_mobilidade_agg, on='jogo_id', how='left')
df_master['receita_total_consumo_mil_rs'] = df_master['receita_total_consumo_rs'] / 1000
df_master['receita_total_mil_rs_real'] = df_master['receita_ingresso_mil_rs_real'] + df_master['receita_total_consumo_mil_rs'].fillna(0)
df_master['ticket_medio_consumo_rs_real'] = df_master['receita_total_consumo_rs'] / df_master['publico_pago_real']
df_master['ticket_medio_total_rs'] = df_master['ticket_medio_ingresso_rs'] + df_master['ticket_medio_consumo_rs_real'].fillna(0)
df_master['data_jogo'] = pd.to_datetime(df_master['data']).dt.date
df_dashboard = df_master.copy()
df_consumo_detalhe = dataframes['fato_consumo'].merge(dataframes['dim_produto'], on='produto_id', how='left')
df_ingressos_canal = dataframes['fato_mercado_ingressos'].merge(dataframes['dim_canal'], on='canal_id', how='left')
df_mobilidade_detalhe = dataframes['fato_mobilidade_incidentes'].merge(dataframes['dim_setor'], on='setor_id', how='left')
df_perfil = dataframes['dim_perfil_torcedor']


# --- 3. GERAÇÃO DAS 9 FIGURAS PLOTLY ---
# (O código de geração dos gráficos fig1 a fig9 é o mesmo que o anterior)
# PAINEL 1
fig1 = px.bar(df_dashboard.sort_values('data_jogo'), x='data_jogo', y=['publico_pago_real', 'publico_pago_projetado'], barmode='group', labels={'value': 'Público Pago (Pessoas)', 'variable': 'Métrica'}, title='1. Comparativo de Público Pago: Realizado vs. Projetado')
fig1.update_layout(hovermode="x unified")
fig2 = px.line(df_dashboard.sort_values('data_jogo'), x='data_jogo', y='ticket_medio_total_rs', title='2. Evolução do Ticket Médio Total (Ingresso + Consumo)', labels={'data_jogo': 'Data do Jogo', 'ticket_medio_total_rs': 'Ticket Médio Total (R$)'}, markers=True, color_discrete_sequence=['#F6511D'])
fig2.update_layout(hovermode="x unified")
order = ['Grande', 'Medio', 'Pequeno', 'Classico']
df_box = df_dashboard.copy()
df_box['nivel_confronto'] = pd.Categorical(df_box['nivel_confronto'], categories=order, ordered=True)
df_box = df_box.sort_values('nivel_confronto')
fig3 = px.box(df_box.dropna(subset=['receita_total_mil_rs_real']), x='nivel_confronto', y='receita_total_mil_rs_real', color='nivel_confronto', title='3. Distribuição da Receita Total (Milhões de R$) por Nível de Confronto', labels={'nivel_confronto': 'Nível do Confronto', 'receita_total_mil_rs_real': 'Receita Total (Milhões de R$)'})

# PAINEL 2
df_receita_categoria = df_consumo_detalhe.groupby('categoria')['receita_produto_rs'].sum().reset_index()
df_receita_categoria['receita_produto_mil_rs'] = df_receita_categoria['receita_produto_rs'] / 1000
fig4 = px.pie(df_receita_categoria, values='receita_produto_mil_rs', names='categoria', title='4. Distribuição da Receita de Consumo por Categoria', hole=.3, color_discrete_sequence=px.colors.qualitative.Pastel)
fig4.update_traces(textposition='inside', textinfo='percent+label')
df_top_itens = df_consumo_detalhe.groupby('item_vendido')['receita_produto_rs'].sum().reset_index()
df_top_itens = df_top_itens.sort_values(by='receita_produto_rs', ascending=False).head(5)
df_top_itens['receita_produto_mil_rs'] = df_top_itens['receita_produto_rs'] / 1000
fig5 = px.bar(df_top_itens, x='item_vendido', y='receita_produto_mil_rs', title='5. Top 5 Itens Vendidos por Receita Total', labels={'item_vendido': 'Item', 'receita_produto_mil_rs': 'Receita Total (Milhares de R$)'}, color='item_vendido', color_discrete_sequence=px.colors.qualitative.Dark2)
df_vendas_tipo = df_ingressos_canal.groupby('tipo_operacao')['vendas_canal'].sum().reset_index()
fig6 = px.bar(df_vendas_tipo, x='tipo_operacao', y='vendas_canal', title='6. Volume Total de Vendas de Ingressos por Tipo de Canal', labels={'tipo_operacao': 'Tipo de Operação', 'vendas_canal': 'Total de Ingressos Vendidos'}, color='tipo_operacao', color_discrete_sequence=['#4B0082', '#00BFFF'])

# PAINEL 3
df_mobilidade_agg_setor = df_mobilidade_detalhe.groupby('nome_setor').agg(tempo_entrada_medio=('tempo_entrada_medio_min', 'mean'), tempo_saida_medio=('tempo_saida_medio_min', 'mean')).reset_index()
fig7 = px.bar(df_mobilidade_agg_setor, x='nome_setor', y=['tempo_entrada_medio', 'tempo_saida_medio'], barmode='group', title='7. Tempo Médio de Entrada e Saída por Setor (Minutos)', labels={'value': 'Tempo Médio (Minutos)', 'variable': 'Métrica de Tempo', 'nome_setor': 'Setor'}, color_discrete_map={'tempo_entrada_medio': '#3CB371', 'tempo_saida_medio': '#FFA07A'})
df_incidentes_agg_setor = df_mobilidade_detalhe.groupby('nome_setor').agg(incidentes_total=('incidente_contagem', 'sum'), tempo_resposta_medio=('tempo_resposta_min', 'mean'), publico_total=('publico_setor', 'sum')).reset_index()
fig8 = px.scatter(df_incidentes_agg_setor, x='tempo_resposta_medio', y='incidentes_total', size='publico_total', color='nome_setor', hover_name='nome_setor', title='8. Análise de Incidentes: Total vs. Tempo Médio de Resposta por Setor', labels={'tempo_resposta_medio': 'Tempo Médio de Resposta (Minutos)', 'incidentes_total': 'Total de Incidentes', 'publico_total': 'Público Total Acumulado'}, size_max=50)
df_faixa_etaria = df_perfil.groupby('faixa_etaria').size().reset_index(name='contagem')
age_order = ['18-24 anos', '25-34 anos', '35-44 anos', '45-59 anos', '60+ anos']
df_faixa_etaria['faixa_etaria'] = pd.Categorical(df_faixa_etaria['faixa_etaria'], categories=age_order, ordered=True)
df_faixa_etaria = df_faixa_etaria.sort_values('faixa_etaria')
fig9 = px.pie(df_faixa_etaria, values='contagem', names='faixa_etaria', title='9. Distribuição do Público por Faixa Etária', hole=.4, color_discrete_sequence=px.colors.qualitative.Vivid)
fig9.update_traces(textposition='inside', textinfo='percent+label')


# --- 4. GERAÇÃO DO HTML ESTÁTICO 100% OFFLINE ---

# include_plotlyjs='cdn' --> Carrega de um servidor externo (Internet)
# include_plotlyjs=True  --> Inclui o código Plotly.js dentro do HTML (100% Offline)

html_fig1 = fig1.to_html(full_html=False, include_plotlyjs=True)
html_fig2 = fig2.to_html(full_html=False, include_plotlyjs=False) # Não precisa repetir o JS
html_fig3 = fig3.to_html(full_html=False, include_plotlyjs=False)
html_fig4 = fig4.to_html(full_html=False, include_plotlyjs=False)
html_fig5 = fig5.to_html(full_html=False, include_plotlyjs=False)
html_fig6 = fig6.to_html(full_html=False, include_plotlyjs=False)
html_fig7 = fig7.to_html(full_html=False, include_plotlyjs=False)
html_fig8 = fig8.to_html(full_html=False, include_plotlyjs=False)
html_fig9 = fig9.to_html(full_html=False, include_plotlyjs=False)


# Template HTML/CSS com o layout Dash simulado
html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Estático 100% Offline</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 0; }}
        .header {{ background-color: #ffffff; color: #1f2f4f; padding: 30px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .content {{ padding: 20px; max-width: 1400px; margin: auto; }}
        .panel-title {{ color: #1f2f4f; border-bottom: 2px solid #ccc; padding-bottom: 5px; margin-top: 30px; margin-bottom: 20px; }}
        .card {{ background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 15px; }}
        .row {{ display: flex; flex-wrap: wrap; margin: -15px; }}
        .col-50 {{ flex: 0 0 50%; max-width: 50%; }}
        .col-33 {{ flex: 0 0 33.33%; max-width: 33.33%; }}
        /* Responsividade básica para Dash */
        @media (max-width: 900px) {{
            .col-50, .col-33 {{ flex: 0 0 100%; max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏟️ Dashboard Interativo (100% Offline)</h1>
    </div>

    <div class="content">

        <h2 class="panel-title">📊 PAINEL 1: Desempenho Financeiro e de Público</h2>
        <div class="row">
            <div class="col-50"><div class="card">{html_fig1}</div></div>
            <div class="col-50"><div class="card">{html_fig2}</div></div>
        </div>
        <div class="row">
            <div class="col-100" style="width: 100%;"><div class="card">{html_fig3}</div></div>
        </div>

        <h2 class="panel-title">🛒 PAINEL 2: Detalhe do Consumo e Mercados</h2>
        <div class="row">
            <div class="col-33"><div class="card">{html_fig4}</div></div>
            <div class="col-33"><div class="card">{html_fig5}</div></div>
            <div class="col-33"><div class="card">{html_fig6}</div></div>
        </div>

        <h2 class="panel-title">🚧 PAINEL 3: Setor, Perfil e Mobilidade</h2>
        <div class="row">
            <div class="col-50"><div class="card">{html_fig7}</div></div>
            <div class="col-50"><div class="card">{html_fig8}</div></div>
        </div>
        <div class="row">
            <div class="col-100" style="width: 100%;"><div class="card">{html_fig9}</div></div>
        </div>
    </div>

</body>
</html>
"""

# Salvar o arquivo HTML
with open("dashboard_offline_completo.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("✅ Dashboard salvo com sucesso em: dashboard_offline_completo.html")