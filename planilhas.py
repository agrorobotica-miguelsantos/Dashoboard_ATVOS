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
    page_title="Monitoramento de Entregas - ATVOS",
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
    "vermelho": "#B91C1C",  # Vermelho corporativo mais amigável e sóbrio
}

# Data global de referência atual para os cálculos do sistema
hoje = pd.Timestamp(dt.date.today())

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
df_datas = pd.read_excel("datas_remessas.xlsx", dtype={'Remessa': str})
df_bruto = (
    df_bruto
    .merge(df_fazendas, how='inner', left_on='Fazenda', right_on='Cod_Fazenda')
    .merge(df_datas, how='inner', left_on=['Remessa', 'Unidade', 'Tipo'], right_on=['Remessa', 'Unidade', 'Tipo'])
)
df_bruto['Nome_Fazenda'] = df_bruto['Nome_Fazenda'].str.strip()

col_ref = "Ca_(mmolc/dm3)"
if col_ref not in df_bruto.columns:
    st.error(f"A coluna de referência '{col_ref}' não foi encontrada nos dados carregados.")
    st.stop()

df_bruto["Status"] = df_bruto[col_ref].apply(
    lambda x: "Concluído" if pd.notna(x) else "Pendente"
)


# ============================================================
# SIDEBAR (FILTROS COM MULTI-BUSCA POR REGEX)
# ============================================================

with st.sidebar:
    logo_path = Path("logo-agrorobotica-png.png")
    if logo_path.exists():
        st.image(str(logo_path), width=250)

    st.caption("Filtros gerais")

    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    busca_fazenda = st.text_input(
        "Busca por Fazenda", 
        placeholder="Ex: 440335, 120528",
        help="Pesquise códigos separados por espaço, vírgula ou ponto e vírgula"
    )

    df_filtrado = df_bruto.copy()

    if busca_fazenda:
        termos = [re.escape(t.strip().lower()) for t in re.split(r'[,;\s]+', busca_fazenda) if t.strip()]
        if termos:
            padrao_regex = "|".join(termos)
            mask_cod = df_filtrado["Fazenda"].astype(str).str.lower().str.contains(padrao_regex, na=False, regex=True)
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
    if unity_select := unidade_select:
        df_filtrado = df_filtrado[df_filtrado["Unidade"].isin(unity_select)]


# ============================================================
# HEADER PRINCIPAL (HERO BANNER)
# ============================================================

hora_brasilia = dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">Monitoramento de Entregas — ATVOS</div>
        <div class="hero-subtitle">
            Acompanhamento do quantitativo de amostras e status de conclusão por remessa, tipo e unidade | 
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
# ESTRUTURAÇÃO EM ABAS
# ============================================================

tab_geral, tab_prazos = st.tabs(["Quantitativo e Status", "Prazos"])

# ------------------------------------------------------------
# ABA 1: QUANTITATIVO E STATUS (VOLUMETRIA MACRO)
# ------------------------------------------------------------
with tab_geral:
    total_amostras = len(df_filtrado)
    concluidas = (df_filtrado["Status"] == "Concluído").sum()
    pendentes = (df_filtrado["Status"] == "Pendente").sum()
    pct_progresso = concluidas / total_amostras if total_amostras > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        card_kpi("Total de Amostras", f"{format_num(total_amostras)} un", "Volume total recebido")
    with c2:
        card_kpi("Entregue", f"{format_num(concluidas)} un", f"{pct_progresso:.0%} concluído")
    with c3:
        card_kpi("Pendentes", f"{format_num(pendentes)} un", f"{(1 - pct_progresso):.0%} em andamento")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        df_graf_remessa = df_filtrado.groupby(["Remessa", "Status", "Tipo"]).size().reset_index(name="Quantidade")
        df_graf_remessa["Remessa"] = df_graf_remessa["Remessa"].astype(str)
        ordem_remessas = sorted(df_graf_remessa["Remessa"].unique())

        fig_remessa = px.bar(
            df_graf_remessa,
            x="Remessa", y="Quantidade", color="Status",
            facet_row="Tipo", facet_row_spacing=0.15,
            color_discrete_map={"Concluído": CORES["verde"], "Pendente": CORES["vermelho"]},
            barmode="stack", text_auto=True,
            title="<b>Amostras por Remessa e Tipo</b>"
        )
        fig_remessa.update_layout(legend_title_text="Status", separators=",.", yaxis_tickformat=",d")
        fig_remessa.update_yaxes(title_text="Nº Amostras")
        fig_remessa.update_xaxes(type="category", categoryorder="array", categoryarray=ordem_remessas, title_text="")
        fig_remessa.update_traces(textangle=0, cliponaxis=False)
        
        tipos_ativos = df_graf_remessa["Tipo"].unique()
        if len(tipos_ativos) == 2:
            fig_remessa.update_xaxes(showticklabels=True, row=1, col=1, title_text="Remessa")
            fig_remessa.update_xaxes(showticklabels=False, row=2, col=1)
        else:
            fig_remessa.update_xaxes(showticklabels=True, row=1, col=1, title_text="Remessa")

        for idx, anno in enumerate(fig_remessa['layout']['annotations']):
            texto_limpo = anno.text.split('=')[-1].strip()
            eixo_y_correto = 'y2 domain' if len(tipos_ativos) == 2 and texto_limpo == 'Fertilidade' else 'y domain'
            anno.update(text=f"<b>{texto_limpo}</b>", x=0.5, yref=eixo_y_correto, y=1.04, textangle=0, xanchor='center', yanchor='bottom')

        st.plotly_chart(aplicar_layout_grafico(fig_remessa, 420), use_container_width=True)

    with col_graf2:
        df_graf_unidade = df_filtrado.groupby(["Unidade", "Status"]).size().reset_index(name="Quantidade")
        fig_unidade = px.bar(
            df_graf_unidade,
            x="Unidade", y="Quantidade", color="Status",
            color_discrete_map={"Concluído": CORES["verde"], "Pendente": CORES["vermelho"]},
            barmode="stack", text_auto=True, title="<b>Amostras por Unidade</b>"
        )
        fig_unidade.update_layout(xaxis_title="Unidade", yaxis_title="Nº Amostras", legend_title_text="Status", separators=",.", yaxis_tickformat=",d")
        st.plotly_chart(aplicar_layout_grafico(fig_unidade, 420), use_container_width=True)

    st.divider()

    # --- TABELA DE DETALHAMENTO MACRO ---
    st.markdown("### Demonstrativo - Fazendas por Unidade")
    ocultar_concluidas = st.toggle("Esconder fazendas 100% concluídas", value=False)
    
    col_cod_fazenda, col_nome_fazenda = "Fazenda", "Nome_Fazenda"
    if "Unidade" in df_filtrado.columns:
        for unidade in sorted(df_filtrado["Unidade"].dropna().unique()):
            df_unidade = df_filtrado[df_filtrado["Unidade"] == unidade]
            t_uni, c_uni = len(df_unidade), (df_unidade["Status"] == "Concluído").sum()
            p_uni = c_uni / t_uni if t_uni > 0 else 0
            
            icone = "✅" if p_uni == 1 else "⏳" if p_uni > 0 else "🔴"
            with st.expander(f"{icone} Unidade {unidade} — {p_uni:.1%} Concluído ({c_uni} de {t_uni} amostras)"):
                resumo = df_unidade.groupby(["Remessa", "Tipo", col_cod_fazenda, col_nome_fazenda]).agg(
                    Total=("Status", "count"),
                    Realizadas=("Status", lambda x: (x == "Concluído").sum()),
                    Faltantes=("Status", lambda x: (x == "Pendente").sum())
                ).reset_index()
                resumo["Progresso"] = (resumo["Realizadas"] / resumo["Total"]) * 100
                
                if ocultar_concluidas:
                    resumo = resumo[resumo["Progresso"] < 100]
                
                if resumo.empty:
                    st.success("Todas as fazendas desta unidade estão concluídas.")
                else:
                    st.dataframe(
                        resumo.sort_values(by=["Progresso", "Total"], ascending=[True, False]),
                        column_config={
                            "Total": st.column_config.NumberColumn("Total"),
                            "Realizadas": st.column_config.NumberColumn("✅ Realizadas"),
                            "Faltantes": st.column_config.NumberColumn("⏳ Faltantes"),
                            "Progresso": st.column_config.ProgressColumn("% Conclusão", format="%.1f %%", min_value=0, max_value=100),
                            "Remessa": st.column_config.TextColumn("Remessa")
                        },
                        hide_index=True, use_container_width=True
                    )

    # --- INTERFACE SOB DEMANDA: DRILL-DOWN POR TALHÃO VIA CÓDIGO ---
    st.divider()
    st.markdown("### 🔍 Detalhamento por Talhão (Sob Demanda)")
    st.caption("Insira o código de uma fazenda para investigar o status e os dados de área ao nível de talhão.")

    codigo_padrao = ""
    if busca_fazenda:
        termos_busca = [t.strip() for t in re.split(r'[,;\s]+', busca_fazenda) if t.strip()]
        if termos_busca:
            codigo_padrao = termos_busca[0]

    fzd_codigo_input = st.text_input(
        "Digite o Código da Fazenda:",
        value=codigo_padrao,
        placeholder="Ex: 440335",
        help="Digite o código numérico da fazenda para listar seus talhões",
        key="txt_talhao_drilldown"
    )

    if fzd_codigo_input:
        df_talhao_fzd = df_filtrado[df_filtrado[col_cod_fazenda].astype(str) == fzd_codigo_input.strip()]
        
        if not df_talhao_fzd.empty:
            nome_fzd_encontrado = df_talhao_fzd[col_nome_fazenda].iloc[0]
            unidade_fzd = df_talhao_fzd["Unidade"].iloc[0]
            
            st.markdown(f"**Fazenda Localizada:** `{fzd_codigo_input}` - **{nome_fzd_encontrado}** (Unidade: *{unidade_fzd}*)")
            
            cols_agrup_talhao = []
            cols_config = {}
            
            if "Talhao" in df_talhao_fzd.columns:
                cols_agrup_talhao.append("Talhao")
                cols_config["Talhao"] = st.column_config.TextColumn("Talhão")
            if "Area_Ha" in df_talhao_fzd.columns:
                cols_agrup_talhao.append("Area_Ha")
                cols_config["Area_Ha"] = st.column_config.NumberColumn("Área (Ha)", format="%.2f Ha")
            if "Tipo" in df_talhao_fzd.columns:
                cols_agrup_talhao.append("Tipo")
                cols_config["Tipo"] = st.column_config.TextColumn("Tipo de Amostragem")
            if "Status" in df_talhao_fzd.columns:
                cols_agrup_talhao.append("Status")
                cols_config["Status"] = st.column_config.TextColumn("Status")
            
            if "Talhao" in df_talhao_fzd.columns:
                df_detalhe_talhao = df_talhao_fzd[cols_agrup_talhao].drop_duplicates().sort_values(by="Talhao")
                st.dataframe(
                    df_detalhe_talhao,
                    column_config=cols_config,
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning("⚠️ A coluna de detalhe 'Talhao' não foi encontrada no arquivo carregado.")
        else:
            st.error(f"❌ Nenhuma fazenda encontrada com o código `{fzd_codigo_input}` nos filtros atuais.")
    else:
        st.info("💡 Digite o código de uma fazenda acima (or utilize o filtro da barra lateral) para carregar os talhões.")

# ------------------------------------------------------------
# ABA 2: PRAZOS, IMPEDIMENTOS & CURVA S (CÓDIGO CORRIGIDO)
# ------------------------------------------------------------
with tab_prazos:
    st.markdown("### ⏳ Cronograma de Entregas & Análise de Gargalos")
    st.caption("Acompanhamento das previsões de laudos e motivos de paralisação física no campo.")

    @st.cache_data(ttl=3600)
    def carregar_prioridades_campo():
        caminho_prio = Path("Prioridades amostragem.xlsx")
        if not caminho_prio.exists():
            return pd.DataFrame()
        try:
            df = pd.read_excel(caminho_prio, sheet_name="FERTILIDADE")
            df.columns = df.columns.str.strip()
            return df
        except:
            return pd.DataFrame()

    df_prio_bruto = carregar_prioridades_campo()

    if df_prio_bruto.empty:
        st.info("Aguardando estruturação do arquivo 'Prioridades amostragem.xlsx' para exibição do cronograma de campo.")
    else:
        # --- ALINHAMENTO DINÂMICO DOS FILTROS DA SIDEBAR ---
        df_prio = df_prio_bruto.copy()

        # 1. Aplica o filtro de Busca por Fazenda usando 'Cod_Fzda'
        if busca_fazenda and 'termos' in locals() and termos:
            mask_prio_fzd = df_prio["Cod_Fzda"].astype(str).str.lower().str.contains(padrao_regex, na=False, regex=True)
            df_prio = df_prio[mask_prio_fzd]

        # 2. Aplica o filtro de Unidades usando a coluna 'Emp'
        if unidade_select:
            df_prio = df_prio[df_prio["Emp"].isin(unidade_select)]

        # 3. Aplica o filtro de Tipo (Como a aba atual é estritamente Fertilidade)
        if tipo_select and "Fertilidade" not in tipo_select:
            df_prio = pd.DataFrame(columns=df_prio.columns) # Esvazia se Fertilidade for desmarcada

        # Nota: O filtro de Remessa é ignorado com segurança aqui, já que esta base não possui essa divisão.

        if df_prio.empty:
            st.info("Nenhum registro de cronograma corresponde aos filtros selecionados na barra lateral.")
        else:
            # --- ENGENHARIA DE MÉTRICAS OPERACIONAIS ---
            area_total_prio = df_prio["Area_Ha"].sum()
            df_parados = df_prio[df_prio["Report_fertilidade"].str.contains("Parado", na=False, case=False)]
            area_parada = df_parados["Area_Ha"].sum()
            pct_parado = area_parada / area_total_prio if area_total_prio > 0 else 0

            df_prio["Previsao_entrega_laudos"] = pd.to_datetime(df_prio["Previsao_entrega_laudos"], errors="coerce")
            proxima_data = df_prio[df_prio["Previsao_entrega_laudos"] >= hoje]["Previsao_entrega_laudos"].min()
            proxima_data_str = proxima_data.strftime("%d/%m/%Y") if pd.notna(proxima_data) else "Sem previsões"

            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                card_kpi("Área Mapeada no Plano", f"{format_num(area_total_prio)} Ha", "Total filtrado para fertilidade")
            with cp2:
                card_kpi("Área Paralisada (Impedimentos)", f"{format_num(area_parada)} Ha", f"{pct_parado:.1%} do cronograma afetado")
            with cp3:
                card_kpi("Próximo Alvo de Entrega", proxima_data_str, "Prazo estimado do próximo lote de laudos")

            st.markdown("<br>", unsafe_allow_html=True)

            col_prio1, col_prio2 = st.columns([4, 5])

            with col_prio1:
                st.markdown("#### Distribuição de Área por Status")
                df_graf_prio = df_prio.groupby("Report_fertilidade")["Area_Ha"].sum().reset_index()
                
                fig_prio_status = px.bar(
                    df_graf_prio,
                    x="Area_Ha", y="Report_fertilidade",
                    orientation="h", text_auto=".1f",
                    color="Report_fertilidade",
                    color_discrete_map={
                        "Andamento": CORES["verde"],
                        "Aguardando Inicio": CORES["azul"],
                        "Parado - Mato Alto": CORES["vermelho"],
                        "Parado - Milheto": "#E11D48",
                        "Parado - Mandioca": "#BE123C",
                        "Cancelado": CORES["cinza"]
                    },
                    title="<b>Hectares por Situação do Relatório</b>"
                )
                fig_prio_status.update_layout(xaxis_title="Hectares (Ha)", yaxis_title="", showlegend=False)
                st.plotly_chart(aplicar_layout_grafico(fig_prio_status, 350), use_container_width=True)

            with col_prio2:
                st.markdown("#### 🎯 Clique em uma linha para Auditar os Talhões")
                
                resumo_prio = df_prio.groupby("Report_fertilidade").agg(
                    Talhoes=("Talhao", "count"),
                    Area_Total=("Area_Ha", "sum")
                ).reset_index().sort_values(by="Area_Total", ascending=False)

                tabela_interativa = st.dataframe(
                    resumo_prio,
                    column_config={
                        "Report_fertilidade": st.column_config.TextColumn("Status / Impedimento"),
                        "Talhoes": st.column_config.NumberColumn("Qtd Talhões"),
                        "Area_Total": st.column_config.NumberColumn("Área Total", format="%.2f Ha")
                    },
                    hide_index=True,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )

            # --- SEÇÃO DRILL-DOWN INTERATIVA DA TABELA DE PRIORIDADES ---
            linhas_selecionadas = tabela_interativa.get("selection", {}).get("rows", [])
            
            if linhas_selecionadas:
                idx_linha = list(linhas_selecionadas)[0]
                status_escolhido = resumo_prio.iloc[idx_linha]["Report_fertilidade"]
                
                st.markdown(f"### 🔍 Detalhamento Micro: `{status_escolhido}`")
                df_detalhe_prio = df_prio[df_prio["Report_fertilidade"] == status_escolhido].copy()
                
                for col_data in ["Previsao_amostragem", "Previsao_chegada", "Previsao_entrega_laudos"]:
                    if col_data in df_detalhe_prio.columns:
                        df_detalhe_prio[col_data] = pd.to_datetime(df_detalhe_prio[col_data]).dt.strftime("%d/%m/%Y").fillna("-")

                st.dataframe(
                    df_detalhe_prio[["Emp", "Fazenda", "Setor", "Talhao", "Area_Ha", "Priopridade_amostragem", "Previsao_entrega_laudos"]].sort_values(by="Area_Ha", ascending=False),
                    column_config={
                        "Emp": st.column_config.TextColumn("Polo"),
                        "Fazenda": st.column_config.TextColumn("Fazenda"),
                        "Talhao": st.column_config.TextColumn("Talhão"),
                        "Area_Ha": st.column_config.NumberColumn("Área", format="%.2f Ha"),
                        "Priopridade_amostragem": st.column_config.TextColumn("Prioridade"),
                        "Previsao_entrega_laudos": st.column_config.TextColumn("Previsão Entrega")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.markdown("""
                    <div style='text-align: center; padding: 20px; border: 1px dashed #E5E7EB; border-radius: 12px; color: #6B7280;'>
                        💡 Clique em qualquer linha da tabela de status acima para abrir a auditoria detalhada de talhões sem poluir a tela.
                    </div>
                """, unsafe_allow_html=True)

            # ============================================================
            # CONSTRUÇÃO DA CURVA S (PLANEJAMENTO DE HECTARES)
            # ============================================================
            st.divider()
            st.markdown("### 📈 Curva S — Planejamento de Avanço da Safra")
            st.caption("Evolução acumulada em Hectares (Ha) comparando o ritmo de amostragem no campo com a liberação dos laudos.")

            df_curva = df_prio.dropna(subset=["Previsao_amostragem", "Previsao_entrega_laudos"]).copy()
            df_curva["Previsao_amostragem"] = pd.to_datetime(df_curva["Previsao_amostragem"])
            df_curva["Previsao_entrega_laudos"] = pd.to_datetime(df_curva["Previsao_entrega_laudos"])
            
            df_curva = df_curva[df_curva["Previsao_entrega_laudos"].dt.year == 2026]

            if not df_curva.empty:
                df_campo_dia = df_curva.groupby("Previsao_amostragem")["Area_Ha"].sum().reset_index(name="Area_Campo")
                df_lab_dia = df_curva.groupby("Previsao_entrega_laudos")["Area_Ha"].sum().reset_index(name="Area_Lab")

                data_inicio = df_curva["Previsao_amostragem"].min()
                data_fim = df_curva["Previsao_entrega_laudos"].max()
                eixo_tempo = pd.date_range(start=data_inicio, end=data_fim).to_frame(index=False, name="Data")

                df_s = eixo_tempo.merge(df_campo_dia, left_on="Data", right_on="Previsao_amostragem", how="left")
                df_s = df_s.merge(df_lab_dia, left_on="Data", right_on="Previsao_entrega_laudos", how="left")
                df_s.drop(columns=["Previsao_amostragem", "Previsao_entrega_laudos"], inplace=True, errors="ignore")
                df_s.fillna(0, inplace=True)

                df_s["Amostragem Planejada (Acumulado)"] = df_s["Area_Campo"].cumsum()
                df_s["Entrega de Laudos Planejada (Acumulado)"] = df_s["Area_Lab"].cumsum()

                df_plot_s = df_s.melt(
                    id_vars=["Data"],
                    value_vars=["Amostragem Planejada (Acumulado)", "Entrega de Laudos Planejada (Acumulado)"],
                    var_name="Cronograma",
                    value_name="Hectares Acumulados"
                )

                fig_s = px.line(
                    df_plot_s,
                    x="Data",
                    y="Hectares Acumulados",
                    color="Cronograma",
                    color_discrete_map={
                        "Amostragem Planejada (Acumulado)": CORES["verde_claro"],
                        "Entrega de Laudos Planejada (Acumulado)": CORES["verde_escuro"]
                    },
                    title="<b>Evolução Cronológica da Área Atendida (Ha)</b>"
                )

                fig_s.update_traces(line=dict(width=4))
                fig_s.update_layout(
                    xaxis_title="Linha do Tempo (Dias/Semanas)",
                    yaxis_title="Área Acumulada (Ha)",
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.12, x=0, title_text="")
                )
                fig_s.update_xaxes(tickformat="%d/%m")

                st.plotly_chart(aplicar_layout_grafico(fig_s, 400), use_container_width=True)
            else:
                st.info("💡 Sem dados de previsão cronológica para o ano corrente de 2026 para gerar a Curva S.")

# ============================================================
# RODAPÉ CENTRALIZADO
# ============================================================
st.divider()

st.markdown(
    """
    <div style="text-align: center; color: #6B7280; font-size: 14px; line-height: 1.6;">
        Dashboard desenvolvido para acompanhamento do quantitativo de amostras e status de conclusão das ordens de serviço ATVOS.<br>
        © 2026 Agrorobótica - Monitoramento de Entregas ATVOS
    </div>
    """,
    unsafe_allow_html=True
)