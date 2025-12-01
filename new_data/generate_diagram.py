import graphviz

# ==============================================================================
# 1. Definição do Modelo Star Schema
# ==============================================================================

# Definição das tabelas e suas chaves
schema = {
    "FATOS": {
        "FATO_JOGOS": ["jogo_id (PK)", "data_id (FK)", "adversario_id (FK)", "publico_pago", "receita_ingresso_mil_rs", "taxa_ocupacao"],
        "FATO_CONSUMO": ["jogo_id (FK)", "produto_id (FK)", "qtd_vendida", "receita_produto_rs"],
        "FATO_MOBILIDADE_INCIDENTES": ["jogo_id (FK)", "setor_id (FK)", "publico_setor", "tempo_entrada_medio_min", "incidente_contagem"],
        "FATO_MERCADO_INGRESSOS": ["data_id (FK)", "canal_id (FK)", "socios_ativos", "vendas_canal"],
        "FATO_PROJECAO": ["jogo_id (FK)", "publico_projetado", "receita_projetada_mil_rs"],
        "FATO_RECEITA_AGREGADA": ["categoria_receita", "receita_total_mil_rs"] # Tabela agregada - sem chaves FK
    },
    "DIMENSOES": {
        "DIM_DATA": ["data_id (PK)", "ano", "mes", "dia_semana"],
        "DIM_ADVERSARIO": ["adversario_id (PK)", "nome_adversario", "competicao", "nivel_confronto"],
        "DIM_SETOR": ["setor_id (PK)", "nome_setor", "capacidade_mil"],
        "DIM_PRODUTO": ["produto_id (PK)", "item_vendido", "categoria", "preco_medio_rs"],
        "DIM_CANAL": ["canal_id (PK)", "nome_canal", "tipo_operacao"],
        "DIM_PERFIL_TORCEDOR": ["perfil_id (PK)", "faixa_etaria", "genero"] # Não possui FK nos fatos, mas é parte da dimensão conceitual
    }
}

# Definição dos Relacionamentos (Fatos -> Dimensões/Outros Fatos)
relationships = [
    # FATO_JOGOS (Fato Central)
    ("FATO_JOGOS", "DIM_DATA", "data_id"),
    ("FATO_JOGOS", "DIM_ADVERSARIO", "adversario_id"),
    
    # Fatos Granulares que se ligam ao JOGO
    ("FATO_CONSUMO", "FATO_JOGOS", "jogo_id (Fato-a-Fato)"),
    ("FATO_MOBILIDADE_INCIDENTES", "FATO_JOGOS", "jogo_id (Fato-a-Fato)"),
    ("FATO_PROJECAO", "FATO_JOGOS", "jogo_id (Fato-a-Fato)"),

    # Dimensões específicas dos Fatos Granulares
    ("FATO_CONSUMO", "DIM_PRODUTO", "produto_id"),
    ("FATO_MOBILIDADE_INCIDENTES", "DIM_SETOR", "setor_id"),
    
    # FATO_MERCADO_INGRESSOS
    ("FATO_MERCADO_INGRESSOS", "DIM_DATA", "data_id"),
    ("FATO_MERCADO_INGRESSOS", "DIM_CANAL", "canal_id"),
]

# ==============================================================================
# 2. Geração do Diagrama Graphviz
# ==============================================================================

# Inicializa o gráfico
dot = graphviz.Digraph(
    'StarSchemaMineirao', 
    comment='Star Schema do Mineirão (Cruzeiro EC) - Simulação',
    graph_attr={'rankdir': 'LR', 'splines': 'spline', 'bgcolor': '#f5f5f5'},
    node_attr={'shape': 'box', 'style': 'filled', 'fontname': 'Inter'}
)

# 2.1. Criação dos Nós (Tabelas)
for group, tables in schema.items():
    
    # Define o estilo do nó baseado no tipo (Fato ou Dimensão)
    if group == "FATOS":
        color = '#004c99' # Azul escuro (Cruzeiro)
        fillcolor = '#C9DAF8' # Azul claro (Fatos)
        fontcolor = 'white'
    else:
        color = '#1C4587' # Azul médio
        fillcolor = '#D9EAD3' # Verde claro (Dimensões)
        fontcolor = 'black'

    for table_name, columns in tables.items():
        # Cria o rótulo em formato HTML para melhor visualização das colunas
        label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{fillcolor}">'
        
        # O cabeçalho da tabela deve sempre ter COLSPAN=2 para cobrir as colunas de Nome e Tipo de Chave.
        label += f'<TR><TD COLSPAN="2" BGCOLOR="{color}"><B><FONT COLOR="white">{table_name}</FONT></B></TD></TR>'
        
        # Colunas (cada coluna em uma linha separada para manter a clareza)
        for col in columns:
            col_color = 'red' if 'PK' in col else 'black'
            col_label = col.replace('(PK)', '').replace('(FK)', '')
            
            # FIX DE ERRO: Garante que col_type não seja uma string vazia (que causa erro de sintaxe no dot)
            # Se não for PK ou FK, usamos um espaço simples (' ')
            col_type = 'PK' if 'PK' in col else ('FK' if 'FK' in col else ' ') 
            
            label += f'<TR><TD ALIGN="LEFT"><FONT COLOR="{col_color}">{col_label}</FONT></TD><TD ALIGN="RIGHT"><FONT COLOR="gray" POINT-SIZE="10">{col_type}</FONT></TD></TR>'

        label += '</TABLE>>'
        
        # Adiciona o nó ao gráfico
        dot.node(table_name, label=label, shape='none')

# 2.2. Criação das Arestas (Relacionamentos)
for source, target, label in relationships:
    # Arestas de Fato para Dimensão são sólidas
    style = 'solid'
    
    if "Fato-a-Fato" in label:
        # Arestas de Fato para Fato são tracejadas
        style = 'dashed'
        label = label.replace(" (Fato-a-Fato)", "")
        
    dot.edge(source, target, label=label, style=style, color='gray', fontname='Inter')


# 2.3. Renderização
output_file = 'diagrama_star_schema'
dot.render(output_file, view=False, format='png') 
print(f"\n---")
print(f"✅ Diagrama de Relacionamento gerado com sucesso!")
print(f"Arquivo gerado: {output_file}.png (Requer a instalação do Graphviz no sistema)")