# %%
import re
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# %% 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Dashboard ATVOS - Amostragens",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; }
    .main-title { font-size: 32px; font-weight: bold; color: #000000; margin-bottom: 20px; }
    </style>
""",
    unsafe_allow_html=True,
)

# %% 2. CARREGAMENTO DOS DADOS COM CACHE
@st.cache_data(ttl=3600)
def carregar_dados_locais():
    """Busca as planilhas na pasta padrão do OneDrive"""
    entrada = Path("pedidos")
    if not entrada.exists():
        return pd.DataFrame()

    planilhas_fertilidade = list(entrada.rglob("F2026*S.xlsx"))
    planilhas_pav = list(entrada.rglob("PAV2026*S.xlsx"))
    lista_combinada = []

    # Processamento Fertilidade
    for planilha in planilhas_fertilidade:
        try:
            # CORREÇÃO: Removido o engine="calamine" para usar o padrão openpyxl
            df_temp = pd.read_excel(planilha)
            
            remessa = re.search(r"(?<=F2026)(\d{3})", str(planilha.stem)).group(0)
            df_temp.insert(0, "Remessa", str(remessa))
            df_temp.insert(1, "Tipo", "Fertilidade")
            df_temp.columns = df_temp.columns.str.strip()
            lista_combinada.append(df_temp)
        except Exception as e:
            # Mostra o erro na tela caso a leitura de alguma planilha específica falhe
            st.error(f"Erro ao ler a planilha {planilha.name}: {e}")

    # Processamento PAV
    for planilha in planilhas_pav:
        try:
            # CORREÇÃO: Removido o engine="calamine" para usar o padrão openpyxl
            df_temp = pd.read_excel(planilha)
            
            remessa = re.search(r"(?<=PAV2026)(\d{3})", str(planilha.stem)).group(0)
            df_temp.insert(0, "Remessa", str(remessa))
            df_temp.insert(1, "Tipo", "PAV")
            df_temp.columns = df_temp.columns.str.strip()
            lista_combinada.append(df_temp)
        except Exception as e:
            # Mostra o erro na tela caso a leitura de alguma planilha específica falhe
            st.error(f"Erro ao ler a planilha {planilha.name}: {e}")

    if not lista_combinada:
        return pd.DataFrame()
        
    return pd.concat(lista_combinada, ignore_index=True)


# %% 3. INPUT DE DADOS
st.sidebar.image(
    "logo-agrorobotica-png.png",
    width=300,
)

if st.sidebar.button("🔄 Atualizar Dados", use_container_width = True):
    st.cache_data.clear()
    st.rerun()

df_bruto = carregar_dados_locais()
df_fazendas = pd.read_excel("fazendas.xlsx")

df_bruto = df_bruto.merge(df_fazendas, how = 'inner', left_on = 'Fazenda', right_on = 'Cod_Fazenda')
df_bruto['Nome_Fazenda'] = df_bruto['Nome_Fazenda'].str.strip()

# Padronização e criação da coluna de Status baseada na referência do Ca
col_ref = "Ca_(mmolc/dm3)"
if col_ref not in df_bruto.columns:
    st.error(
        f"A coluna de referência '{col_ref}' não foi encontrada nos dados carregados."
    )
    st.stop()

df_bruto["Status"] = df_bruto[col_ref].apply(
    lambda x: "Concluído" if pd.notna(x) else "Pendente"
)

# %% 4. FILTROS DINÂMICOS EM CASCATA
st.sidebar.subheader("Filtros de Pesquisa")

# 1º Passo: Busca Livre (Universal) dita as regras do resto
busca_livre = st.sidebar.text_input(
    "Busca Fazenda", 
    placeholder="Ex: 420136",
    help="Pesquise utilizando o código da fazenda"
)

# Aplica a busca no dataframe bruto ANTES de montar as listas dos filtros
df_filtrado = df_bruto.copy()

if busca_livre:
    termo = busca_livre.lower()
    
    mask_cod = df_filtrado["Fazenda"].astype(str).str.lower().str.contains(termo, na=False) if "Fazenda" in df_filtrado.columns else False
  
    df_filtrado = df_filtrado[mask_cod]

# 2º Passo: Filtro de Tipo de Análise (Já reflete a busca)
tipos_disponiveis = sorted(df_filtrado["Tipo"].unique()) if "Tipo" in df_filtrado.columns else ["Geral"]
tipo_select = st.sidebar.multiselect(
    "Tipo de Análise", options=tipos_disponiveis, default=tipos_disponiveis
)
if tipo_select:
    df_filtrado = df_filtrado[df_filtrado["Tipo"].isin(tipo_select)]

# 3º Passo: Filtro de Remessa (Reflete a busca e o Tipo)
remessas_disponiveis = (
    sorted(df_filtrado["Remessa"].unique())
    if "Remessa" in df_filtrado.columns
    else []
)
remessa_select = st.sidebar.multiselect(
    "Remessas", options=remessas_disponiveis, default=remessas_disponiveis
)
if remessa_select:
    df_filtrado = df_filtrado[df_filtrado["Remessa"].isin(remessa_select)]

# 4º Passo: Filtro de Unidade (Reflete a busca, Tipo e Remessa)
unidades_disponiveis = (
    sorted(df_filtrado["Unidade"].unique())
    if "Unidade" in df_filtrado.columns
    else []
)
unidade_select = st.sidebar.multiselect(
    "Unidades", options=unidades_disponiveis, default=unidades_disponiveis
)
if unidade_select:
    df_filtrado = df_filtrado[df_filtrado["Unidade"].isin(unidade_select)]

# %% 5. CORPO PRINCIPAL DO DASHBOARD
st.markdown(
    "<div class='main-title'>Acompanhamento de Amostragens — ATVOS</div>",
    unsafe_allow_html=True,
)

if df_filtrado.empty:
    st.info("Nenhum dado corresponde aos filtros selecionados na barra lateral.")
    st.stop()

# --- CÁLCULO DE MÉTRICAS GERAIS ---
total_amostras = len(df_filtrado)
concluidas = (df_filtrado["Status"] == "Concluído").sum()
pendentes = (df_filtrado["Status"] == "Pendente").sum()
pct_progresso = concluidas / total_amostras if total_amostras > 0 else 0

# Formatação dos números (ponto para milhar, vírgula para decimal)
str_total = f"{total_amostras:,}".replace(",", ".")
str_concluidas = f"{concluidas:,}".replace(",", ".")
str_pendentes = f"{pendentes:,}".replace(",", ".")

str_delta_conc = f"{pct_progresso:.1%}".replace(".", ",")
str_delta_pend = f"-{(1 - pct_progresso):.1%}".replace(".", ",")
str_taxa = f"{pct_progresso:.1%}".replace(".", ",")

# Exibição dos KPIs
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(label="Total de Amostras", value=f"{str_total} un")

kpi2.metric(
    label="Entregue",
    value=f"{str_concluidas} un",
    delta=str_delta_conc,
)

kpi3.metric(
    label="Pendentes",
    value=f"{str_pendentes} un",
    delta=str_delta_pend,
    delta_color="red",
)

kpi4.metric(
    label="Taxa de Conclusão", 
    value=str_taxa
)
# Barra de progresso horizontal
st.progress(pct_progresso)
st.markdown("---")

# %% 6. VISÃO GRÁFICA INTERATIVA
st.subheader("Volumetria por Unidade")

# Gráfico de Barras Empilhadas mostrando a volumetria por Unidade
df_graf_unidade = (
    df_filtrado.groupby(["Unidade", "Status"]).size().reset_index(name="Quantidade")
)

fig_unidade = px.bar(
    df_graf_unidade,
    x="Unidade",
    y="Quantidade",
    color="Status",
    title="<b>Amostras por Unidade e Status</b>",
    color_discrete_map={"Concluído": "#2E7D32", "Pendente": "#C62828"},
    barmode="stack",
    text_auto=True
)

fig_unidade.update_layout(
    margin=dict(t=40, b=20, l=20, r=20),
    height=400, # Aumentei um pouco a altura para aproveitar o espaço
    xaxis_title="Unidade",
    yaxis_title="Nº Amostras",
    legend_title_text="Status",
    separators=",.",
    yaxis_tickformat=",d"
)

# Exibe o gráfico ocupando 100% da largura da página
st.plotly_chart(fig_unidade, use_container_width=True)

st.markdown("---")

# %% 7. DETALHAMENTO DE FAZENDAS AGRUPADAS POR UNIDADE (VISÃO TABULAR)
st.subheader("Demostrativo - Fazendas por Unidade")

# Filtro global para esta seção: Toggle para limpar a tela das finalizadas
ocultar_concluidas = st.toggle("Esconder fazendas 100% concluídas", value=False, help="Ative para focar apenas no que possui pendência.")

# Definindo as colunas exatas
col_cod_fazenda = "Fazenda"
col_nome_fazenda = "Nome_Fazenda"

# Verifica quais colunas realmente existem no DataFrame
tem_cod = col_cod_fazenda in df_filtrado.columns
tem_nome = col_nome_fazenda in df_filtrado.columns

if "Unidade" in df_filtrado.columns and (tem_cod or tem_nome):
    unidades_unicas = sorted(df_filtrado["Unidade"].dropna().unique())
    
    if not unidades_unicas:
        st.warning("Nenhuma unidade encontrada nos dados filtrados.")
    
    # Criamos um loop para gerar um bloco expansível para CADA Unidade
    for unidade in unidades_unicas:
        df_unidade = df_filtrado[df_filtrado["Unidade"] == unidade]
        
        # Métricas gerais apenas dessa Unidade para o título
        total_uni = len(df_unidade)
        conc_uni = (df_unidade["Status"] == "Concluído").sum()
        pend_uni = (df_unidade["Status"] == "Pendente").sum()
        prog_uni = conc_uni / total_uni if total_uni > 0 else 0
        
        # Define um ícone visual para o cabeçalho dependendo do status da unidade
        icone = "✅" if prog_uni == 1 else "⏳" if prog_uni > 0 else "🔴"
        
        # Cria o bloco expansível
        titulo_expander = f"{icone} Unidade {unidade} — {prog_uni:.1%} Concluído ({conc_uni} de {total_uni} amostras)"
        
        with st.expander(titulo_expander, expanded=False):
            
            # Define as colunas de agrupamento dinamicamente
            colunas_agrupamento = []
            
            # Adiciona a Remessa PRIMEIRO para que ela seja a primeira coluna da tabela
            if "Remessa" in df_unidade.columns: 
                colunas_agrupamento.append("Remessa")
            
            if "Tipo" in df_unidade.columns:
                colunas_agrupamento.append("Tipo")
                
            if tem_cod: colunas_agrupamento.append(col_cod_fazenda)
            if tem_nome: colunas_agrupamento.append(col_nome_fazenda)
            
            # Agrupamento estritamente tabular
            resumo_tabela = df_unidade.groupby(colunas_agrupamento).agg(
                Total=("Status", "count"),
                Concluídas=("Status", lambda x: (x == "Concluído").sum()),
                Pendentes=("Status", lambda x: (x == "Pendente").sum())
            ).reset_index()
            
            # Calcula a porcentagem (escala de 0 a 100 para a barra de progresso)
            resumo_tabela["Progresso"] = (resumo_tabela["Concluídas"] / resumo_tabela["Total"]) * 100
            
            # APLICAÇÃO DO FILTRO: Remove fazendas com 100% se o botão estiver ativado
            if ocultar_concluidas:
                resumo_tabela = resumo_tabela[resumo_tabela["Progresso"] < 100]
            
            # Verifica se sobrou alguma fazenda para mostrar após o filtro
            if resumo_tabela.empty:
                st.success("Todas as fazendas listadas para esta unidade já estão 100% concluídas.")
            else:
                # Ordena colocando as fazendas com mais pendências no topo da tabela
                resumo_tabela = resumo_tabela.sort_values(by=["Progresso", "Total"], ascending=[True, False])
                
                # Configuração visual das colunas da tabela
                config_colunas = {
                    "Total": st.column_config.NumberColumn("Total de Amostras", format="%d"),
                    "Concluídas": st.column_config.NumberColumn("✅ Realizadas", format="%d"),
                    "Pendentes": st.column_config.NumberColumn("⏳ Faltantes", format="%d"),
                    "Progresso": st.column_config.ProgressColumn(
                        "% Conclusão",
                        help="Barra visual de progresso da fazenda",
                        format="%.1f %%",
                        min_value=0,
                        max_value=100
                    )
                }
                
                # Adiciona as configurações de texto dependendo das colunas que existem
                # Garantindo que a Remessa seja tratada como texto para não formatar com pontos de milhar
                if "Remessa" in df_unidade.columns:
                    config_colunas["Remessa"] = st.column_config.TextColumn("Remessa", width="small")
                if "Tipo" in df_unidade.columns:
                    config_colunas["Tipo"] = st.column_config.TextColumn("Amostragem", width="small")
                if tem_cod:
                    config_colunas[col_cod_fazenda] = st.column_config.TextColumn("Código Fazenda", width="small")
                if tem_nome:
                    config_colunas[col_nome_fazenda] = st.column_config.TextColumn("Nome da Fazenda", width="medium")
                
                # Exibe a tabela de dados
                st.dataframe(
                    resumo_tabela,
                    column_config=config_colunas,
                    hide_index=True,
                    use_container_width=True
                )
else:
    st.info("Colunas de Unidade, Fazenda ou Nome_Fazenda não encontradas no arquivo de dados para gerar essa visualização.")