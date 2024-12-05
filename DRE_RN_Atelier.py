import requests
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def listar_api(url_api, call_api, titulo_json):

    pagina = 1

    registros_por_pagina = 500 

    todos_registros = []

    while True:

        payload_api = {"call": call_api, 
                    "app_key": "4482434850894", 
                    "app_secret": "622dabcb857a10b05522819ca57d6eea",
                    "param": [{"pagina": pagina, 
                                "registros_por_pagina": registros_por_pagina,
                                "apenas_importado_api": "N"
                                }
                                ]
                    }

        response = requests.post(url_api, headers={"Content-Type": "application/json"}, data=json.dumps(payload_api))

        dados = response.json()

        todos_registros.extend(dados.get(titulo_json, []))

        if len(dados.get(titulo_json, [])) < registros_por_pagina:

            break  

        else:

            pagina += 1  

    return todos_registros

def grafico_linha_RS(referencia, eixo_x, eixo_y_1, ref_1_label, titulo):

    referencia[eixo_x] = referencia[eixo_x].astype(str)
    
    fig, ax = plt.subplots(figsize=(15, 8))
    
    plt.plot(referencia[eixo_x], referencia[eixo_y_1], label = ref_1_label, linewidth = 0.5, color = 'black')

    for i in range(len(referencia[eixo_x])):
        texto = 'R$' + str(int(referencia[eixo_y_1][i]))
        plt.text(referencia[eixo_x][i], referencia[eixo_y_1][i], texto, ha='center', va='bottom')

    plt.title(titulo, fontsize=30)
    plt.xlabel('Ano/Mês')
    ax.legend(loc='lower right', bbox_to_anchor=(1.2, 1))
    st.pyplot(fig)
    plt.close(fig)

def tratar_df_pedidos(df_pedidos):

    colunas_dicionarios = ['exportacao', 'cabecalho', 'frete', 'infoCadastro', 'informacoes_adicionais', 'lista_parcelas', 'observacoes', 'total_pedido']

    for coluna in colunas_dicionarios:

        df_expanded = pd.json_normalize(df_pedidos[coluna])
        df_pedidos = pd.concat([df_pedidos, df_expanded], axis=1)

    df_pedidos = df_pedidos.drop(columns=colunas_dicionarios)

    df_pedidos = pd.merge(df_pedidos, st.session_state.df_clientes[['codigo_cliente', 'nome_fantasia']], on='codigo_cliente', how='left')

    df_pedidos = df_pedidos.drop(columns='codigo_cliente')

    df_pedidos = pd.merge(df_pedidos, st.session_state.df_categorias[['codigo', 'descricao']], left_on='codigo_categoria', right_on='codigo', how='left')

    df_pedidos = df_pedidos.drop(columns='codigo_categoria')

    df_pedidos = df_pedidos[df_pedidos['cancelado']=='N'].reset_index(drop=True)

    df_pedidos.loc[df_pedidos['cancelado']=='S', 'valor_total_pedido'] = -df_pedidos['valor_total_pedido']

    return df_pedidos

def gerar_df_vendas_mensais(df_pedidos):

    # trocar data_previsao p/ previsao_entrega

    df_vendas = df_pedidos[['previsao_entrega', 'valor_total_pedido', 'nome_fantasia', 'descricao']]

    df_vendas['previsao_entrega'] = pd.to_datetime(df_vendas['previsao_entrega'], format='%d/%m/%Y')

    df_vendas['mes'] = df_vendas['previsao_entrega'].dt.month

    df_vendas['ano'] = df_vendas['previsao_entrega'].dt.year

    df_vendas['ano'] = df_vendas['ano'].astype(int)
    df_vendas['mes'] = df_vendas['mes'].astype(int)

    df_vendas['previsao_entrega'] = pd.to_datetime(df_vendas['previsao_entrega']).dt.date

    df_vendas_mensais = df_vendas.groupby(['ano', 'mes'])['valor_total_pedido'].sum().reset_index()

    df_vendas_mensais['mes/ano'] = pd.to_datetime(df_vendas_mensais['ano'].astype(str) + '-' + df_vendas_mensais['mes'].astype(str)).dt.to_period('M')

    return df_vendas_mensais

def inserir_trimestres(df_vendas_mensais):

    df_vendas_mensais.loc[df_vendas_mensais['mes'].isin([1, 2, 3]), 'trimestre'] = 1

    df_vendas_mensais.loc[df_vendas_mensais['mes'].isin([4, 5, 6]), 'trimestre'] = 2

    df_vendas_mensais.loc[df_vendas_mensais['mes'].isin([7, 8, 9]), 'trimestre'] = 3

    df_vendas_mensais.loc[df_vendas_mensais['mes'].isin([10, 11, 12]), 'trimestre'] = 4

    df_vendas_mensais['tri/ano'] = 'T' + df_vendas_mensais['trimestre'].astype(int).astype(str) + '/' + df_vendas_mensais['ano'].astype(str).str[-2:]

    return df_vendas_mensais

def tratar_df_pagar(df_pagar):

    colunas_dicionarios = ['info']

    for coluna in colunas_dicionarios:

        df_expanded = pd.json_normalize(df_pagar[coluna])
        df_pagar = pd.concat([df_pagar, df_expanded], axis=1)

    df_pagar = df_pagar.drop(columns=colunas_dicionarios)

    df_pagar = pd.merge(df_pagar, st.session_state.df_clientes[['codigo_cliente', 'nome_fantasia']], left_on='codigo_cliente_fornecedor', right_on='codigo_cliente', how='left')

    df_pagar = df_pagar.drop(columns=['codigo_cliente_fornecedor', 'codigo_cliente'])

    df_pagar = pd.merge(df_pagar, st.session_state.df_categorias[['codigo', 'descricao', 'descricao_padrao', 'descricaoDRE']], left_on='codigo_categoria', right_on='codigo', how='left')

    df_pagar = df_pagar.drop(columns=['codigo_categoria', 'codigo'])

    return df_pagar

def gerar_df_despesas_mensais(df_pagar):

    df_despesas = df_pagar[['data_vencimento', 'status_titulo', 'valor_documento', 'nome_fantasia', 'descricao', 'descricao_padrao', 'descricaoDRE']]

    df_despesas['data_vencimento'] = pd.to_datetime(df_despesas['data_vencimento'], dayfirst=True)

    df_despesas['mes'] = df_despesas['data_vencimento'].dt.month

    df_despesas['ano'] = df_despesas['data_vencimento'].dt.year

    df_despesas['data_vencimento'] = pd.to_datetime(df_despesas['data_vencimento']).dt.date

    df_despesas_mensais = df_despesas.groupby(['ano', 'mes', 'descricaoDRE', 'descricao'])['valor_documento'].sum().reset_index()

    df_despesas_mensais['mes/ano'] = pd.to_datetime(df_despesas_mensais['ano'].astype(str) + '-' + df_despesas_mensais['mes'].astype(str)).dt.to_period('M')

    return df_despesas_mensais

def atualizar_omie():

    # st.session_state.df_receber = pd.DataFrame(listar_api('https://app.omie.com.br/api/v1/financas/contareceber/', 'ListarContasReceber', 'conta_receber_cadastro'))

    st.session_state.df_categorias = pd.DataFrame(listar_api('https://app.omie.com.br/api/v1/geral/categorias/', 'ListarCategorias', 'categoria_cadastro'))

    colunas_dicionarios = ['dadosDRE']

    for coluna in colunas_dicionarios:

        df_expanded = pd.json_normalize(st.session_state.df_categorias[coluna])
        st.session_state.df_categorias = pd.concat([st.session_state.df_categorias, df_expanded], axis=1)

    st.session_state.df_categorias = st.session_state.df_categorias.drop(columns=colunas_dicionarios)

    st.session_state.df_pedidos = pd.DataFrame(listar_api('https://app.omie.com.br/api/v1/produtos/pedido/', 'ListarPedidos', 'pedido_venda_produto'))

    st.session_state.df_clientes = pd.DataFrame(listar_api('https://app.omie.com.br/api/v1/geral/clientes/', 'ListarClientesResumido', 'clientes_cadastro_resumido'))

    st.session_state.df_pagar = pd.DataFrame(listar_api('https://app.omie.com.br/api/v1/financas/contapagar/', 'ListarContasPagar', 'conta_pagar_cadastro'))

    st.session_state.df_pedidos = tratar_df_pedidos(st.session_state.df_pedidos)

    st.session_state.df_vendas_mensais = gerar_df_vendas_mensais(st.session_state.df_pedidos)

    st.session_state.df_vendas_mensais = inserir_trimestres(st.session_state.df_vendas_mensais)

    st.session_state.df_vendas_anuais = st.session_state.df_vendas_mensais.groupby('ano')['valor_total_pedido'].sum().reset_index()

    st.session_state.df_pagar = tratar_df_pagar(st.session_state.df_pagar)

    st.session_state.df_despesas_mensais = gerar_df_despesas_mensais(st.session_state.df_pagar)

    st.session_state.df_despesas_mensais = inserir_trimestres(st.session_state.df_despesas_mensais)

    st.session_state.df_cpv_mensais = st.session_state.df_despesas_mensais[st.session_state.df_despesas_mensais['descricaoDRE'].isin(['Despesas Variáveis', 'Custo dos Serviços Prestados'])]\
        .reset_index(drop=True)

    st.session_state.df_cpv_mensais_geral = st.session_state.df_cpv_mensais.groupby('mes/ano')['valor_documento'].sum().reset_index().sort_values(by=('mes/ano')).reset_index(drop=True)

    st.session_state.df_dre = pd.merge(st.session_state.df_vendas_mensais, st.session_state.df_cpv_mensais_geral, on='mes/ano', how='left')

    st.session_state.df_dre = st.session_state.df_dre.rename(columns={'valor_documento': 'cpv'})

    st.session_state.df_dre['cpv'] = st.session_state.df_dre['cpv'].fillna(0)

    st.session_state.df_dre['resultado_bruto'] = st.session_state.df_dre['valor_total_pedido'] - st.session_state.df_dre['cpv']

    st.session_state.df_dre['margem_bruta'] = round(st.session_state.df_dre['resultado_bruto'] / st.session_state.df_dre['valor_total_pedido'], 2)

    st.session_state.df_do_mensais = st.session_state.df_despesas_mensais\
        [st.session_state.df_despesas_mensais['descricaoDRE'].isin(['Despesas Administrativas', 'Despesas com Pessoal', 'Despesas de Vendas e Marketing', 'Deduções de Receita'])].reset_index(drop=True)

    st.session_state.df_do_mensais_geral = st.session_state.df_do_mensais.groupby('mes/ano')['valor_documento'].sum().reset_index().sort_values(by=('mes/ano')).reset_index(drop=True)

    st.session_state.df_dre = pd.merge(st.session_state.df_dre, st.session_state.df_do_mensais_geral, on='mes/ano', how='left')

    st.session_state.df_dre = st.session_state.df_dre.rename(columns={'valor_documento': 'do'})

    st.session_state.df_dre['do'] = st.session_state.df_dre['do'].fillna(0)

    st.session_state.df_dre['resultado_operacional'] = st.session_state.df_dre['resultado_bruto'] - st.session_state.df_dre['do']

    st.session_state.df_dre['margem_operacional'] = round(st.session_state.df_dre['resultado_operacional'] / st.session_state.df_dre['valor_total_pedido'], 2)

    st.session_state.df_df_mensais = st.session_state.df_despesas_mensais\
        [st.session_state.df_despesas_mensais['descricaoDRE'].isin(['Ativos', 'Despesas Financeiras', 'Outros Tributos'])].reset_index(drop=True)

    st.session_state.df_df_mensais = st.session_state.df_df_mensais.groupby('mes/ano')['valor_documento'].sum().reset_index().sort_values(by=('mes/ano')).reset_index(drop=True)

    st.session_state.df_dre = pd.merge(st.session_state.df_dre, st.session_state.df_df_mensais, on='mes/ano', how='left')

    st.session_state.df_dre = st.session_state.df_dre.rename(columns={'valor_documento': 'df'})

    st.session_state.df_dre['df'] = st.session_state.df_dre['df'].fillna(0)

    st.session_state.df_dre['resultado_liquido'] = st.session_state.df_dre['resultado_operacional'] - st.session_state.df_dre['df']

    st.session_state.df_dre['margem_liquida'] = round(st.session_state.df_dre['resultado_liquido'] / st.session_state.df_dre['valor_total_pedido'], 2)

    st.session_state.df_df_apenas_financeiras_mensais = st.session_state.df_despesas_mensais\
        [st.session_state.df_despesas_mensais['descricaoDRE'].isin(['Ativos', 'Despesas Financeiras'])].reset_index(drop=True)
    
    st.session_state.df_df_apenas_financeiras_mensais = st.session_state.df_df_apenas_financeiras_mensais.groupby('mes/ano')['valor_documento'].sum().reset_index().sort_values(by=('mes/ano'))\
        .reset_index(drop=True)

    st.session_state.df_dre = pd.merge(st.session_state.df_dre, st.session_state.df_df_apenas_financeiras_mensais, on='mes/ano', how='left')

    st.session_state.df_dre = st.session_state.df_dre.rename(columns={'valor_documento': 'df_apenas_financeiras'})

    st.session_state.df_dre['df_apenas_financeiras'] = st.session_state.df_dre['df_apenas_financeiras'].fillna(0)

    st.session_state.df_impostos_mensais = st.session_state.df_despesas_mensais\
        [st.session_state.df_despesas_mensais['descricaoDRE'].isin(['Outros Tributos'])].reset_index(drop=True)
    
    st.session_state.df_impostos_mensais = st.session_state.df_impostos_mensais.groupby('mes/ano')['valor_documento'].sum().reset_index().sort_values(by=('mes/ano'))\
        .reset_index(drop=True)

    st.session_state.df_dre = pd.merge(st.session_state.df_dre, st.session_state.df_impostos_mensais, on='mes/ano', how='left')

    st.session_state.df_dre = st.session_state.df_dre.rename(columns={'valor_documento': 'impostos'})

    st.session_state.df_dre['impostos'] = st.session_state.df_dre['impostos'].fillna(0)

    for index, imposto_total in st.session_state.df_dre['impostos'].items():

        if index!=0:

            st.session_state.df_dre.at[index, 'aliquota_impostos'] = round(imposto_total / st.session_state.df_dre.at[index-1, 'valor_total_pedido'], 2)

        else:

            st.session_state.df_dre.at[index, 'aliquota_impostos'] = 0

def grafico_tres_linhas_percentual(referencia, eixo_x, eixo_y_1, ref_1_label, eixo_y_2, ref_2_label, eixo_y_3, ref_3_label, titulo):

    referencia[eixo_x] = referencia[eixo_x].astype(str)
    
    fig, ax = plt.subplots(figsize=(15, 8))
    
    plt.plot(referencia[eixo_x], referencia[eixo_y_1], label = ref_1_label, linewidth = 0.5, color = 'red')
    ax.plot(referencia[eixo_x], referencia[eixo_y_2], label = ref_2_label, linewidth = 0.5, color = 'blue')
    ax.plot(referencia[eixo_x], referencia[eixo_y_3], label = ref_3_label, linewidth = 0.5, color = 'black')
    
    for i in range(len(referencia[eixo_x])):
        texto = str(int(referencia[eixo_y_1][i] * 100)) + "%"
        plt.text(referencia[eixo_x][i], referencia[eixo_y_1][i], texto, ha='center', va='bottom')
    for i in range(len(referencia[eixo_x])):
        texto = str(int(referencia[eixo_y_2][i] * 100)) + "%"
        plt.text(referencia[eixo_x][i], referencia[eixo_y_2][i], texto, ha='center', va='bottom')
    for i in range(len(referencia[eixo_x])):
        texto = str(int(referencia[eixo_y_3][i] * 100)) + "%"
        plt.text(referencia[eixo_x][i], referencia[eixo_y_3][i], texto, ha='center', va='bottom')

    plt.title(titulo, fontsize=30)
    plt.xlabel('Ano/Mês')
    ax.legend(loc='lower right', bbox_to_anchor=(1.2, 1))
    st.pyplot(fig)
    plt.close(fig)

def grafico_quatro_linhas_RS(referencia, eixo_x, eixo_y_1, ref_1_label, eixo_y_2, ref_2_label, eixo_y_3, ref_3_label, eixo_y_4, ref_4_label, titulo):

    referencia[eixo_x] = referencia[eixo_x].astype(str)
    
    fig, ax = plt.subplots(figsize=(15, 8))
    
    plt.plot(referencia[eixo_x], referencia[eixo_y_1], label = ref_1_label, linewidth = 0.5, color = 'red')
    ax.plot(referencia[eixo_x], referencia[eixo_y_2], label = ref_2_label, linewidth = 0.5, color = 'blue')
    ax.plot(referencia[eixo_x], referencia[eixo_y_3], label = ref_3_label, linewidth = 0.5, color = 'black')
    ax.plot(referencia[eixo_x], referencia[eixo_y_4], label = ref_4_label, linewidth = 0.5, color = 'green')

    for i in range(len(referencia[eixo_x])):
        texto = 'R$' + str(int(referencia[eixo_y_1][i]))
        plt.text(referencia[eixo_x][i], referencia[eixo_y_1][i], texto, ha='center', va='bottom')
    for i in range(len(referencia[eixo_x])):
        texto = 'R$' + str(int(referencia[eixo_y_2][i]))
        plt.text(referencia[eixo_x][i], referencia[eixo_y_2][i], texto, ha='center', va='bottom')
    for i in range(len(referencia[eixo_x])):
        texto = 'R$' + str(int(referencia[eixo_y_3][i]))
        plt.text(referencia[eixo_x][i], referencia[eixo_y_3][i], texto, ha='center', va='bottom')
    for i in range(len(referencia[eixo_x])):
        texto = 'R$' + str(int(referencia[eixo_y_4][i]))
        plt.text(referencia[eixo_x][i], referencia[eixo_y_4][i], texto, ha='center', va='bottom')

    plt.title(titulo, fontsize=30)
    plt.xlabel('Ano/Mês')
    ax.legend(loc='lower right', bbox_to_anchor=(1.2, 1))
    st.pyplot(fig)
    plt.close(fig)

def grafico_linha_percentual(referencia, eixo_x, eixo_y_1, ref_1_label, titulo):

    referencia[eixo_x] = referencia[eixo_x].astype(str)
    
    fig, ax = plt.subplots(figsize=(15, 8))
    
    plt.plot(referencia[eixo_x], referencia[eixo_y_1], label = ref_1_label, linewidth = 0.5, color = 'black')
    
    for i in range(len(referencia[eixo_x])):
        texto = str(int(referencia[eixo_y_1][i] * 100)) + "%"
        plt.text(referencia[eixo_x][i], referencia[eixo_y_1][i], texto, ha='center', va='bottom')

    plt.title(titulo, fontsize=30)
    plt.xlabel('Ano/Mês')
    ax.legend(loc='lower right', bbox_to_anchor=(1.2, 1))
    st.pyplot(fig)
    plt.close(fig)

st.set_page_config(layout='wide')

dict_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

st.title('DRE | RN Atelier - OMIE')

st.divider()    

row1 = st.columns(3)

row2 = st.columns(2)

row3 = st.columns(1)

if not 'df_categorias' in st.session_state:

    atualizar_omie()

with row1[0]:

    atualizar_dados_omie = st.button('Atualizar Dados OMIE')

if atualizar_dados_omie:

    atualizar_omie()

with row1[0]:

    botao_anos = st.multiselect('Anos', range(2024, 2031), default=None)

    botao_mes_atual = st.selectbox('Mês de Análise', range(1, 13), index=None)

with row1[1]:

    analise = st.radio('Análise', ['Vendas Gerais', 'Margens | Bruta vs Operacional vs Líquida', 'Despesas Gerais', 'Margem Bruta', 'CPV', 'Margem Operacional', 'Folha', 'Despesas Operacionais', 
                                   'Margem Líquida', 'Despesas Financeiras', 'Impostos', 'Cálculo de Ponto de Equilíbrio'], index=None)

if botao_anos and analise and analise=='Vendas Gerais':

    df_vendas_mensais_filtro_ano = st.session_state.df_vendas_mensais[st.session_state.df_vendas_mensais['ano'].isin(botao_anos)].reset_index(drop=True)

    df_vendas_trimestrais = df_vendas_mensais_filtro_ano.groupby('tri/ano')['valor_total_pedido'].sum().reset_index()

    with row2[0]:

        grafico_linha_RS(df_vendas_mensais_filtro_ano, 'mes/ano', 'valor_total_pedido', 'Vendas', f"Vendas Mensais | {' '.join(map(str, botao_anos))}")

        grafico_linha_RS(df_vendas_trimestrais, 'tri/ano', 'valor_total_pedido', 'Vendas', f"Vendas Trimestrais | {' '.join(map(str, botao_anos))}")

    with row3[0]:

        grafico_linha_RS(st.session_state.df_vendas_anuais, 'ano', 'valor_total_pedido', 'Vendas', f"Vendas Anuais")

    if botao_mes_atual:

        df_vendas_mes_atual = st.session_state.df_vendas_mensais[st.session_state.df_vendas_mensais['mes']==botao_mes_atual].reset_index(drop=True)

        tri_atual = st.session_state.df_vendas_mensais.loc[st.session_state.df_vendas_mensais['mes']==botao_mes_atual, 'trimestre'].iloc[0].astype(int)

        df_vendas_tri_atual = st.session_state.df_vendas_mensais[st.session_state.df_vendas_mensais['trimestre']==tri_atual].groupby('tri/ano')['valor_total_pedido'].sum().reset_index()

        with row2[1]:

            grafico_linha_RS(df_vendas_mes_atual, 'mes/ano', 'valor_total_pedido', 'Vendas', f'Vendas Mensais | {dict_meses[botao_mes_atual]}')

            grafico_linha_RS(df_vendas_tri_atual, 'tri/ano', 'valor_total_pedido', 'Vendas', f'Vendas Trimestrais | {tri_atual}T')

elif botao_anos and analise and analise=='Margens | Bruta vs Operacional vs Líquida':

    df_dre_mensais_filtro_ano = st.session_state.df_dre[st.session_state.df_dre['ano'].isin(botao_anos)].reset_index(drop=True)

    df_dre_trimestrais = st.session_state.df_dre.groupby(['tri/ano', 'ano', 'trimestre'])[['valor_total_pedido', 'resultado_bruto', 'resultado_operacional', 'resultado_liquido']].sum().reset_index()

    df_dre_trimestrais['mb'] = round(df_dre_trimestrais['resultado_bruto'] / df_dre_trimestrais['valor_total_pedido'], 2)

    df_dre_trimestrais['mo'] = round(df_dre_trimestrais['resultado_operacional'] / df_dre_trimestrais['valor_total_pedido'], 2)

    df_dre_trimestrais['ml'] = round(df_dre_trimestrais['resultado_liquido'] / df_dre_trimestrais['valor_total_pedido'], 2)

    df_dre_anuais = st.session_state.df_dre.groupby(['ano'])[['valor_total_pedido', 'resultado_bruto', 'resultado_operacional', 'resultado_liquido']].sum().reset_index()

    df_dre_anuais['mb'] = round(df_dre_anuais['resultado_bruto'] / df_dre_anuais['valor_total_pedido'], 2)

    df_dre_anuais['mo'] = round(df_dre_anuais['resultado_operacional'] / df_dre_anuais['valor_total_pedido'], 2)

    df_dre_anuais['ml'] = round(df_dre_anuais['resultado_liquido'] / df_dre_anuais['valor_total_pedido'], 2)

    with row2[0]:

        df_grafico_mensal = df_dre_mensais_filtro_ano[df_dre_mensais_filtro_ano['margem_liquida']!=1].reset_index(drop=True)

        df_grafico_trimestral = df_dre_trimestrais[(df_dre_trimestrais['ml']!=1) & (df_dre_trimestrais['ano'].isin(botao_anos))].reset_index(drop=True)

        grafico_tres_linhas_percentual(df_grafico_mensal, 'mes/ano', 'margem_bruta', 'Margem Bruta', 'margem_operacional', 'Margem Operacional', 'margem_liquida', 'Margem Líquida', 
                                       f"Margens Mensais | {' '.join(map(str, botao_anos))}")

        grafico_tres_linhas_percentual(df_grafico_trimestral, 'tri/ano', 'mb', 'Margem Bruta', 'mo', 'Margem Operacional', 'ml', 'Margem Líquida', 
                                       f"Margens Trimestrais | {' '.join(map(str, botao_anos))}")
        
    with row3[0]:

        grafico_tres_linhas_percentual(df_dre_anuais, 'ano', 'mb', 'Margem Bruta', 'mo', 'Margem Operacional', 'ml', 'Margem Líquida', 
                                       f"Margens Anuais")
        
    if botao_mes_atual:

        df_dre_mes_atual = st.session_state.df_dre[st.session_state.df_dre['mes']==botao_mes_atual].reset_index(drop=True)

        tri_atual = st.session_state.df_dre.loc[st.session_state.df_dre['mes']==botao_mes_atual, 'trimestre'].iloc[0].astype(int)

        df_dre_tri_atual = df_dre_trimestrais[df_dre_trimestrais['trimestre']==tri_atual].reset_index(drop=True)

        with row2[1]:

            grafico_tres_linhas_percentual(df_dre_mes_atual, 'mes/ano', 'margem_bruta', 'Margem Bruta', 'margem_operacional', 'Margem Operacional', 'margem_liquida', 'Margem Líquida', 
                                           f'Margens Mensais | {dict_meses[botao_mes_atual]}')
            
            grafico_tres_linhas_percentual(df_dre_tri_atual, 'tri/ano', 'mb', 'Margem Bruta', 'mo', 'Margem Operacional', 'ml', 'Margem Líquida', 
                                           f'Margens Trimestrais | {tri_atual}T')

elif botao_anos and analise and analise=='Despesas Gerais':

    df_dre_mensais_filtro_ano = st.session_state.df_dre[st.session_state.df_dre['ano'].isin(botao_anos)].reset_index(drop=True)

    df_dre_trimestrais = st.session_state.df_dre.groupby(['tri/ano', 'ano', 'trimestre'])[['cpv', 'do', 'df_apenas_financeiras', 'impostos']].sum().reset_index()

    df_dre_anuais = st.session_state.df_dre.groupby(['ano'])[['cpv', 'do', 'df_apenas_financeiras', 'impostos']].sum().reset_index()

    with row2[0]:

        df_grafico_mensal = df_dre_mensais_filtro_ano[df_dre_mensais_filtro_ano['cpv']!=0].reset_index(drop=True)

        df_grafico_trimestral = df_dre_trimestrais[(df_dre_trimestrais['cpv']!=0) & (df_dre_trimestrais['ano'].isin(botao_anos))].reset_index(drop=True)

        grafico_quatro_linhas_RS(df_grafico_mensal, 'mes/ano', 'cpv', 'CPV', 'do', 'Despesas Operacionais', 'df_apenas_financeiras', 'Despesas Financeiras', 'impostos', 
                                       'Impostos', f"Despesas Mensais | {' '.join(map(str, botao_anos))}")

        grafico_quatro_linhas_RS(df_grafico_trimestral, 'tri/ano', 'cpv', 'CPV', 'do', 'Despesas Operacionais', 'df_apenas_financeiras', 'Despesas Financeiras', 'impostos', 
                                       'Impostos', f"Despesas Mensais | {' '.join(map(str, botao_anos))}")
        
    with row3[0]:

        grafico_quatro_linhas_RS(df_dre_anuais, 'ano', 'cpv', 'CPV', 'do', 'Despesas Operacionais', 'df_apenas_financeiras', 'Despesas Financeiras', 'impostos', 
                                       'Impostos', f"Despesas Anuais")
        
    if botao_mes_atual:

        df_dre_mes_atual = st.session_state.df_dre[st.session_state.df_dre['mes']==botao_mes_atual].reset_index(drop=True)

        tri_atual = st.session_state.df_dre.loc[st.session_state.df_dre['mes']==botao_mes_atual, 'trimestre'].iloc[0].astype(int)

        df_dre_tri_atual = df_dre_trimestrais[df_dre_trimestrais['trimestre']==tri_atual].reset_index(drop=True)

        with row2[1]:

            grafico_quatro_linhas_RS(df_dre_mes_atual, 'mes/ano', 'cpv', 'CPV', 'do', 'Despesas Operacionais', 'df_apenas_financeiras', 'Despesas Financeiras', 'impostos', 
                                       'Impostos', f'Despesas Mensais | {dict_meses[botao_mes_atual]}')
            
            grafico_quatro_linhas_RS(df_dre_tri_atual, 'tri/ano', 'cpv', 'CPV', 'do', 'Despesas Operacionais', 'df_apenas_financeiras', 'Despesas Financeiras', 'impostos', 
                                       'Impostos', f'Despesas Trimestrais | {tri_atual}T')

elif botao_anos and analise and (analise=='Margem Bruta' or analise=='Margem Operacional' or analise=='Margem Líquida'):

    df_dre_mensais_filtro_ano = st.session_state.df_dre[st.session_state.df_dre['ano'].isin(botao_anos)].reset_index(drop=True)

    df_dre_trimestrais = st.session_state.df_dre.groupby(['tri/ano', 'ano', 'trimestre'])[['valor_total_pedido', 'resultado_bruto', 'resultado_operacional', 'resultado_liquido']].sum().reset_index()

    df_dre_trimestrais['mb'] = round(df_dre_trimestrais['resultado_bruto'] / df_dre_trimestrais['valor_total_pedido'], 2)

    df_dre_trimestrais['mo'] = round(df_dre_trimestrais['resultado_operacional'] / df_dre_trimestrais['valor_total_pedido'], 2)

    df_dre_trimestrais['ml'] = round(df_dre_trimestrais['resultado_liquido'] / df_dre_trimestrais['valor_total_pedido'], 2)

    df_dre_anuais = st.session_state.df_dre.groupby(['ano'])[['valor_total_pedido', 'resultado_bruto', 'resultado_operacional', 'resultado_liquido']].sum().reset_index()

    df_dre_anuais['mb'] = round(df_dre_anuais['resultado_bruto'] / df_dre_anuais['valor_total_pedido'], 2)

    df_dre_anuais['mo'] = round(df_dre_anuais['resultado_operacional'] / df_dre_anuais['valor_total_pedido'], 2)

    df_dre_anuais['ml'] = round(df_dre_anuais['resultado_liquido'] / df_dre_anuais['valor_total_pedido'], 2)

    with row2[0]:

        df_grafico_mensal = df_dre_mensais_filtro_ano[df_dre_mensais_filtro_ano['margem_liquida']!=1].reset_index(drop=True)

        df_grafico_trimestral = df_dre_trimestrais[(df_dre_trimestrais['ml']!=1) & (df_dre_trimestrais['ano'].isin(botao_anos))].reset_index(drop=True)

        if analise=='Margem Bruta':

            grafico_linha_percentual(df_grafico_mensal, 'mes/ano', 'margem_bruta', 'Margem Bruta', f"Margens Brutas Mensais | {' '.join(map(str, botao_anos))}")

            grafico_linha_percentual(df_grafico_trimestral, 'tri/ano', 'mb', 'Margem Bruta', f"Margens Brutas Trimestrais | {' '.join(map(str, botao_anos))}")

        elif analise=='Margem Operacional':

            grafico_linha_percentual(df_grafico_mensal, 'mes/ano', 'margem_operacional', 'Margem Operacional', f"Margens Operacionais Mensais | {' '.join(map(str, botao_anos))}")

            grafico_linha_percentual(df_grafico_trimestral, 'tri/ano', 'mo', 'Margem Operacional', f"Margens Operacionais Trimestrais | {' '.join(map(str, botao_anos))}")

        elif analise=='Margem Líquida':

            grafico_linha_percentual(df_grafico_mensal, 'mes/ano', 'margem_liquida', 'Margem Líquida', f"Margens Líquidas Mensais | {' '.join(map(str, botao_anos))}")

            grafico_linha_percentual(df_grafico_trimestral, 'tri/ano', 'ml', 'Margem Líquida', f"Margens Líquidas Trimestrais | {' '.join(map(str, botao_anos))}")

    with row3[0]:

        if analise=='Margem Bruta':

            grafico_linha_percentual(df_dre_anuais, 'ano', 'mb', 'Margem Bruta', f"Margens Brutas Anuais")

        elif analise=='Margem Operacional':

            grafico_linha_percentual(df_dre_anuais, 'ano', 'mo', 'Margem Operacional', f"Margens Operacionais Anuais")

        elif analise=='Margem Líquida':

            grafico_linha_percentual(df_dre_anuais, 'ano', 'ml', 'Margem Líquida', f"Margens Líquidas Anuais")

    if botao_mes_atual:

        df_dre_mes_atual = st.session_state.df_dre[st.session_state.df_dre['mes']==botao_mes_atual].reset_index(drop=True)

        tri_atual = st.session_state.df_dre.loc[st.session_state.df_dre['mes']==botao_mes_atual, 'trimestre'].iloc[0].astype(int)

        df_dre_tri_atual = df_dre_trimestrais[df_dre_trimestrais['trimestre']==tri_atual].reset_index(drop=True)

        with row2[1]:

            if analise=='Margem Bruta':

                grafico_linha_percentual(df_dre_mes_atual, 'mes/ano', 'margem_bruta', 'Margem Bruta', f'Margens Brutas Mensais | {dict_meses[botao_mes_atual]}')
            
                grafico_linha_percentual(df_dre_tri_atual, 'tri/ano', 'mb', 'Margem Bruta', f'Margens Brutas Trimestrais | {tri_atual}T')

            elif analise=='Margem Operacional':

                grafico_linha_percentual(df_dre_mes_atual, 'mes/ano', 'margem_operacional', 'Margem Operacional', f'Margens Operacionais Mensais | {dict_meses[botao_mes_atual]}')
            
                grafico_linha_percentual(df_dre_tri_atual, 'tri/ano', 'mo', 'Margem Operacional', f'Margens Operacionais Trimestrais | {tri_atual}T')

            elif analise=='Margem Líquida':

                grafico_linha_percentual(df_dre_mes_atual, 'mes/ano', 'margem_liquida', 'Margem Líquida', f'Margens Líquidas Mensais | {dict_meses[botao_mes_atual]}')
            
                grafico_linha_percentual(df_dre_tri_atual, 'tri/ano', 'ml', 'Margem Líquida', f'Margens Líquidas Trimestrais | {tri_atual}T')

elif botao_anos and analise and (analise=='CPV' or analise=='Despesas Operacionais' or analise=='Despesas Financeiras'):

    if analise=='CPV':

        filtro_contas = ['Despesas Variáveis', 'Custo dos Serviços Prestados']

    if analise=='Despesas Operacionais':

        filtro_contas = ['Despesas Administrativas', 'Despesas com Pessoal', 'Despesas de Vendas e Marketing', 'Deduções de Receita']

    if analise=='Despesas Financeiras':

        filtro_contas = ['Ativos', 'Despesas Financeiras']

    with row1[2]:

        apenas_marketing = st.multiselect('Apenas Marketing', ['Sim'], default=None)

        apenas_pessoal = st.multiselect('Apenas Pessoal', ['Sim'], default=None)

    df_ref_mensal = st.session_state.df_despesas_mensais[st.session_state.df_despesas_mensais['descricaoDRE'].isin(filtro_contas)].reset_index(drop=True)

    if apenas_marketing and apenas_marketing[0] == 'Sim':

        df_ref_mensal = df_ref_mensal[df_ref_mensal['descricaoDRE']=='Despesas de Vendas e Marketing'].reset_index(drop=True)

        lista_categorias = ['Todas']

        lista_categorias.extend(sorted(df_ref_mensal['descricao'].unique().tolist()))

    elif apenas_pessoal and apenas_pessoal[0] == 'Sim':

        df_ref_mensal = df_ref_mensal[df_ref_mensal['descricaoDRE']=='Despesas com Pessoal'].reset_index(drop=True)

        lista_categorias = ['Todas']

        lista_categorias.extend(sorted(df_ref_mensal['descricao'].unique().tolist()))

    else:

        lista_categorias = sorted(df_ref_mensal['descricao'].unique().tolist())

    with row1[2]:

        container_categoria = st.container(height=200)

        categoria_analise = container_categoria.radio('Categoria', lista_categorias, index=None)

    if categoria_analise:

        if categoria_analise!='Todas':

            df_ref_categoria = df_ref_mensal[df_ref_mensal['descricao']==categoria_analise].reset_index(drop=True)

        else:

            df_ref_categoria = df_ref_mensal.groupby(['ano', 'mes', 'descricaoDRE', 'mes/ano', 'trimestre', 'tri/ano'])['valor_documento'].sum().reset_index()

        df_ref_categoria_filtro_ano = df_ref_categoria[df_ref_categoria['ano'].isin(botao_anos)].reset_index(drop=True)

        df_ref_categoria_trimestrais = df_ref_categoria_filtro_ano.groupby('tri/ano')['valor_documento'].sum().reset_index()

        df_ref_categoria_anual = df_ref_categoria.groupby('ano')['valor_documento'].sum().reset_index()

        with row2[0]:

            grafico_linha_RS(df_ref_categoria, 'mes/ano', 'valor_documento', categoria_analise, f"Despesas Mensais {categoria_analise} | {' '.join(map(str, botao_anos))}")

            grafico_linha_RS(df_ref_categoria_trimestrais, 'tri/ano', 'valor_documento', categoria_analise, f"Despesas Trimestrais {categoria_analise} | {' '.join(map(str, botao_anos))}")

        with row3[0]:

            grafico_linha_RS(df_ref_categoria_anual, 'ano', 'valor_documento', categoria_analise, f"Despesas Anuais {categoria_analise}")

        if botao_mes_atual:

            df_ref_categoria_mes_atual = df_ref_categoria[df_ref_categoria['mes']==botao_mes_atual].reset_index(drop=True)

            tri_atual = st.session_state.df_dre.loc[st.session_state.df_dre['mes']==botao_mes_atual, 'trimestre'].iloc[0].astype(int)

            df_ref_categoria_tri_atual = df_ref_categoria[df_ref_categoria['trimestre']==tri_atual].groupby('tri/ano')['valor_documento'].sum().reset_index()

            with row2[1]:

                grafico_linha_RS(df_ref_categoria_mes_atual, 'mes/ano', 'valor_documento', categoria_analise, f'Despesas Mensais {categoria_analise} | {dict_meses[botao_mes_atual]}')

                grafico_linha_RS(df_ref_categoria_tri_atual, 'tri/ano', 'valor_documento', categoria_analise, f'Despesas Trimestrais {categoria_analise} | {tri_atual}T')

elif botao_anos and analise and analise=='Cálculo de Ponto de Equilíbrio':

    aliquota_imposto = st.number_input('Alíquota p/ Cálculo', step=0.5, value=5.0)

    desconto_despesas = st.number_input('Despesas Não Recorrentes', step=1, value=0)

    def_ref_peq = st.session_state.df_dre[st.session_state.df_dre['margem_liquida']!=1].reset_index(drop=True)

    def_ref_peq['despesas_n_recorrentes'] = desconto_despesas

    def_ref_peq['ponto_equilibrio'] = (def_ref_peq['do'] + def_ref_peq['df'] - def_ref_peq['despesas_n_recorrentes']) / (def_ref_peq['margem_bruta'] - (aliquota_imposto/100))

    grafico_linha_RS(def_ref_peq, 'mes/ano', 'ponto_equilibrio', 'Ponto de Equilíbrio', 'Ponto de Equilíbrio Mensal')


