# %%
# ============================================================
# PAINEL - ACOMPANHAMENTO DE AMOSTRAGENS | ATVOS
# ============================================================

import re
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# CONFIGURAÇÕES GERAIS E PALETA DE CORES
# ============================================================

st.set_page_config(
    page_title="Dashboard ATVOS - Amostragens",
    layout="wide",
    initial_sidebar_state="expanded",
)

CORES = {
    "verde_escuro": "#12372A",
    "verde": "#2D6A4F",
    "verde_claro": "#74C69D",
    "fundo": "#FFFFFF",
    "card": "#FFFFFF",
    "texto": "#1F2937",
    "cinza": "#6B7280",
    "borda": "#E5E7EB",
    "alerta": "#F59E0B",
    "azul": "#2563EB",
    "vermelho": "#FF2C2C",
}

# ============================================================
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ============================================================

st.markdown(
    f"""
    <style>
        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }}

        .main {{
            background-color: {CORES["fundo"]};
        }}

        section[data-testid="stSidebar"] {{
            background-color: #FFFFFF;
            border-right: 1px solid {CORES["borda"]};
        }}

        .hero {{
            background: linear-gradient(135deg, #12372A 0%, #2D6A4F 60%, #40916C 100%);
            padding: 28px 32px;
            border-radius: 24px;
            color: white;
            margin-bottom: 22px;
            box-shadow: 0 12px 30px rgba(18, 55, 42, 0.18);
        }}

        .hero-title {{
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 6px;
        }}

        .hero-subtitle {{
            font-size: 15px;
            color: #E8F5E9;
        }}

        .kpi-card {{
            background-color: white;
            border-radius: 20px;
            padding: 20px 22px;
            border: 1px solid {CORES["borda"]};
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            min-height: 125px;
        }}

        .kpi-label {{
            font-size: 14px;
            color: {CORES["cinza"]};
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-size: 30px;
            color: {CORES["verde_escuro"]};
            font-weight: 800;
            margin-bottom: 4px;
        }}

        .kpi-help {{
            font-size: 13px;
            color: {CORES["cinza"]};
        }}

        .section-card {{
            background-color: white;
            padding: 22px;
            border-radius: 22px;
            border: 1px solid {CORES["borda"]};
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
            margin-bottom: 18px;
        }}

        div[data-testid="stMetricValue"] {{
            font-size: 28px;
            font-weight: 800;
            color: {CORES["verde_escuro"]};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================

def format_num(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def card_kpi(titulo, valor, detalhe):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{titulo}</div>
            <div class="kpi-value">{valor}</div>
            <div class="kpi-help">{detalhe}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def aplicar_layout_grafico(fig, altura=400):
    fig.update_layout(
        height=altura,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=40, b=30, l=20, r=20),
        font=dict(color=CORES["texto"]),
    )
    return fig


# ============================================================
# CARREGAMENTO DOS DADOS COM CACHE
# ============================================================

@st.cache_data(ttl=3600, show_spinner="Carregando planilhas do OneDrive...")
def carregar_dados_locais():
    entrada = Path("pedidos")
    if not entrada.exists():
        return pd.DataFrame()

    planilhas_fertilidade = list(entrada.rglob("F2026*S.xlsx"))
    planilhas_pav = list(entrada.rglob("PAV2026*S.xlsx"))
    lista_combinada = []

    # Processamento Fertilidade
    for planilha in planilhas_fertilidade:
        try:
            df_temp = pd.read_excel(planilha)
            remessa = re.search(r"(?<=F2026)(\d{3})", str(planilha.stem)).group(0)
            df_temp.insert(0, "Remessa", str(remessa))
            df_temp.insert(1, "Tipo", "Fertilidade")
            df_temp.columns = df_temp.columns.str.strip()
            lista_combinada.append(df_temp)
        except Exception as e:
            st.error(f"Erro ao ler a planilha {planilha.name}: {e}")

    # Processamento PAV
    for planilha in planilhas_pav:
        try:
            df_temp = pd.read_excel(planilha)
            remessa = re.search(r"(?<=PAV2026)(\d{3})", str(planilha.stem)).group(0)
            df_temp.insert(0, "Remessa", str(remessa))
            df_temp.insert(1, "Tipo", "PAV")
            df_temp.columns = df_temp.columns.str.strip()
            lista_combinada.append(df_temp)
        except Exception as e:
            st.error(f"Erro ao ler a planilha {planilha.name}: {e}")

    if not lista_combinada:
        return pd.DataFrame()
        
    return pd.concat(lista_combinada, ignore_index=True)


# ============================================================
# PROCESSAMENTO E TRATAMENTO DA BASE
# ============================================================

df_bruto = carregar_dados_locais()

if df_bruto.empty:
    st.error("Nenhum dado bruto pôde ser carregado da pasta `pedidos`.")
    st.stop()

df_fazendas = pd.read_excel("fazendas.xlsx")
df_bruto = df_bruto.merge(df_fazendas, how='inner', left_on='Fazenda', right_on='Cod_Fazenda')
df_bruto['Nome_Fazenda'] = df_bruto['Nome_Fazenda'].str.strip()

col_ref = "Ca_(mmolc/dm3)"
if col_ref not in df_bruto.columns:
    st.error(f"A coluna de referência '{col_ref}' não foi encontrada nos dados carregados.")
    st.stop()

df_bruto["Status"] = df_bruto[col_ref].apply(
    lambda x: "Concluído" if pd.notna(x) else "Pendente"
)


# ============================================================
# SIDEBAR (FILTROS)
# ============================================================

with st.sidebar:
    logo_path = Path("logo-agrorobotica-png.png")
    if logo_path.exists():
        st.image(str(logo_path), width=250)

    st.markdown("## Gestão de Amostras")
    st.caption("Filtros gerais")

    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    busca_livre = st.text_input(
        "Busca Fazenda", 
        placeholder="Ex: 420136",
        help="Pesquise utilizando o código da fazenda"
    )

    df_filtrado = df_bruto.copy()

    if busca_livre:
        termo = busca_livre.lower()
        mask_cod = df_filtrado["Fazenda"].astype(str).str.lower().str.contains(termo, na=False)
        df_filtrado = df_filtrado[mask_cod]

    tipos_disponiveis = sorted(df_filtrado["Tipo"].unique()) if "Tipo" in df_filtrado.columns else ["Geral"]
    tipo_select = st.multiselect(
        "Tipo de Análise", options=tipos_disponiveis, default=tipos_disponiveis
    )
    if tipo_select:
        df_filtrado = df_filtrado[df_filtrado["Tipo"].isin(tipo_select)]

    remessas_disponiveis = sorted(df_filtrado["Remessa"].unique()) if "Remessa" in df_filtrado.columns else []
    remessa_select = st.multiselect(
        "Remessas", options=remessas_disponiveis, default=remessas_disponiveis
    )
    if remessa_select:
        df_filtrado = df_filtrado[df_filtrado["Remessa"].isin(remessa_select)]

    unidades_disponiveis = sorted(df_filtrado["Unidade"].unique()) if "Unidade" in df_filtrado.columns else []
    unidade_select = st.multiselect(
        "Unidades", options=unidades_disponiveis, default=unidades_disponiveis
    )
    if unidade_select:
        df_filtrado = df_filtrado[df_filtrado["Unidade"].isin(unidade_select)]


# ============================================================
# HEADER PRINCIPAL (HERO BANNER)
# ============================================================

hora_brasilia = dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">Acompanhamento de Amostragens — ATVOS</div>
        <div class="hero-subtitle">
            Monitoramento do quantitativo de amostras e status de conclusão por remesa, tipo e unidade | 
            Atualizado em {hora_brasilia.strftime("%d/%m/%Y %H:%M")}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if df_filtrado.empty:
    st.info("Nenhum dado corresponde aos filtros selecionados na barra lateral.")
    st.stop()


# ============================================================
# MÉTRICAS (KPI CARDS CUSTOMIZADOS)
# ============================================================

total_amostras = len(df_filtrado)
concluidas = (df_filtrado["Status"] == "Concluído").sum()
pendentes = (df_filtrado["Status"] == "Pendente").sum()
pct_progresso = concluidas / total_amostras if total_amostras > 0 else 0

c1, c2, c3 = st.columns(3)

with c1:
    card_kpi("Total de Amostras", f"{format_num(total_amostras)} un", "Amostras recebidas")

with c2:
    card_kpi("Entregue", f"{format_num(concluidas)} un", f"{pct_progresso:.1%} concluído")

with c3:
    card_kpi("Pendentes", f"{format_num(pendentes)} un", f"{(1 - pct_progresso):.1%} em andamento")

st.markdown("<br>", unsafe_allow_html=True)
st.progress(pct_progresso)


# ============================================================
# VISÃO GRÁFICA INTERATIVA
# ============================================================

st.divider()

col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    df_graf_remessa = df_filtrado.groupby(["Remessa", "Status", "Tipo"]).size().reset_index(name="Quantidade")
    ordem_remessas = sorted(df_graf_remessa["Remessa"].unique())

    fig_remessa = px.bar(
        df_graf_remessa,
        x="Remessa",
        y="Quantidade",
        color="Status",
        facet_row="Tipo",
        facet_row_spacing=0.15,
        color_discrete_map={"Concluído": CORES["verde"], "Pendente": CORES["vermelho"]},
        barmode="stack",
        text_auto=True,
        title="<b>Amostras por Remessa e Tipo</b>"
    )

    fig_remessa.update_layout(
        xaxis_title="Remessa",
        yaxis_title="Nº Amostras",
        legend_title_text="Status",
        separators=",.",
        yaxis_tickformat=",d"
    )

    fig_remessa.update_yaxes(title_text="Nº Amostras")
    fig_remessa.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=ordem_remessas,
        title_text=""
    )

    # Controla dinamicamente a exibição dos rótulos do eixo X com base nos tipos ativos
    tipos_ativos = df_graf_remessa["Tipo"].unique()
    
    if len(tipos_ativos) == 2:
        # Se os dois tipos estão ativos, limpa o de cima (row=2) e mantém o de baixo (row=1)
        fig_remessa.update_xaxes(showticklabels=True, row=1, col=1, title_text="Remessa")
        fig_remessa.update_xaxes(showticklabels=False, row=2, col=1)
    else:
        # Se apenas um tipo está ativo, o Plotly por padrão joga para o row=1. Forçamos o rótulo nele.
        fig_remessa.update_xaxes(showticklabels=True, row=1, col=1, title_text="Remessa")

    # Move os títulos originais da direita para o topo dinamicamente (eles somem se o tipo sumir)
    for anno in fig_remessa['layout']['annotations']:
        texto_limpo = anno['text'].split('=')[-1]
        
        # Define o eixo Y correto de forma fixa com base no texto para evitar sobreposição
        if len(tipos_ativos) == 2:
            # Se os dois estão na tela, PAV fica em cima (y2) e Fertilidade embaixo (y)
            eixo_y_correto = 'y2 domain' if texto_limpo == 'PAV' else 'y domain'
        else:
            # Se apenas um está na tela, ele sempre usará o primeiro eixo disponível (y)
            eixo_y_correto = 'y domain'
        
        anno.update(
            text=f"<b>{texto_limpo}</b>",
            x=0.5,
            yref=eixo_y_correto,
            y=1.04,            # Distância perfeita acima de cada respectivo subgráfico
            textangle=0,       # Texto na horizontal
            xanchor='center',
            yanchor='bottom'
        )

    st.plotly_chart(aplicar_layout_grafico(fig_remessa, 400), use_container_width=True)

with col_graf2:
    df_graf_unidade = df_filtrado.groupby(["Unidade", "Status"]).size().reset_index(name="Quantidade")

    fig_unidade = px.bar(
        df_graf_unidade,
        x="Unidade",
        y="Quantidade",
        color="Status",
        color_discrete_map={"Concluído": CORES["verde"], "Pendente": CORES["vermelho"]},
        barmode="stack",
        text_auto=True,
        title="<b>Amostras por Unidade</b>"
    )

    fig_unidade.update_layout(
        xaxis_title="Unidade",
        yaxis_title="Nº Amostras",
        legend_title_text="Status",
        separators=",.",
        yaxis_tickformat=",d"
    )

    st.plotly_chart(aplicar_layout_grafico(fig_unidade, 400), use_container_width=True)

st.divider()


# ============================================================
# DETALHAMENTO DE FAZENDAS (VISÃO TABULAR)
# ============================================================

st.markdown("### Demonstrativo - Fazendas por Unidade")

ocultar_concluidas = st.toggle(
    "Esconder fazendas 100% concluídas", 
    value=False, 
    help="Ative para focar apenas no que possui pendência."
)

col_cod_fazenda = "Fazenda"
col_nome_fazenda = "Nome_Fazenda"

tem_cod = col_cod_fazenda in df_filtrado.columns
tem_nome = col_nome_fazenda in df_filtrado.columns

if "Unidade" in df_filtrado.columns and (tem_cod or tem_nome):
    unidades_unicas = sorted(df_filtrado["Unidade"].dropna().unique())
    
    if not unidades_unicas:
        st.warning("Nenhuma unidade encontrada nos dados filtrados.")
    
    for unidade in unidades_unicas:
        df_unidade = df_filtrado[df_filtrado["Unidade"] == unidade]
        
        total_uni = len(df_unidade)
        conc_uni = (df_unidade["Status"] == "Concluído").sum()
        prog_uni = conc_uni / total_uni if total_uni > 0 else 0
        
        icone = "✅" if prog_uni == 1 else "⏳" if prog_uni > 0 else "🔴"
        titulo_expander = f"{icone} Unidade {unidade} — {prog_uni:.1%} Concluído ({conc_uni} de {total_uni} amostras)"
        
        with st.expander(titulo_expander, expanded=False):
            colunas_agrupamento = []
            
            if "Remessa" in df_unidade.columns: 
                colunas_agrupamento.append("Remessa")
            if "Tipo" in df_unidade.columns:
                colunas_agrupamento.append("Tipo")
                
            if tem_cod: colunas_agrupamento.append(col_cod_fazenda)
            if tem_nome: colunas_agrupamento.append(col_nome_fazenda)
            
            resumo_tabela = df_unidade.groupby(colunas_agrupamento).agg(
                Total=("Status", "count"),
                Concluídas=("Status", lambda x: (x == "Concluído").sum()),
                Pendentes=("Status", lambda x: (x == "Pendente").sum())
            ).reset_index()
            
            resumo_tabela["Progresso"] = (resumo_tabela["Concluídas"] / resumo_tabela["Total"]) * 100
            
            if ocultar_concluidas:
                resumo_tabela = resumo_tabela[resumo_tabela["Progresso"] < 100]
            
            if resumo_tabela.empty:
                st.success("Todas as fazendas listadas para esta unidade já estão 100% concluídas.")
            else:
                resumo_tabela = resumo_tabela.sort_values(by=["Progresso", "Total"], ascending=[True, False])
                
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
                
                if "Remessa" in df_unidade.columns:
                    config_colunas["Remessa"] = st.column_config.TextColumn("Remessa", width="small")
                if "Tipo" in df_unidade.columns:
                    config_colunas["Tipo"] = st.column_config.TextColumn("Amostragem", width="small")
                if tem_cod:
                    config_colunas[col_cod_fazenda] = st.column_config.TextColumn("Código Fazenda", width="small")
                if tem_nome:
                    config_colunas[col_nome_fazenda] = st.column_config.TextColumn("Nome da Fazenda", width="medium")
                
                st.dataframe(
                    resumo_tabela,
                    column_config=config_colunas,
                    hide_index=True,
                    use_container_width=True
                )
else:
    st.info("Colunas essenciais de Unidade/Fazenda não encontradas para gerar a visão tabular.")

# ============================================================
# RODAPÉ
# ============================================================
st.divider()

st.markdown(
    """
    <div style="text-align: center; color: #6B7280; font-size: 14px;">
        Dashboard desenvolvido para acompanhamento do quantitativo de amostras e status de conclusão das ordens de serviço ATVOS.
        © 2026 Agrorobótica
    </div>
    """,
    unsafe_allow_html=  True
)