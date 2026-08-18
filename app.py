# %%
# ============================================================
# PAINEL - ACOMPANHAMENTO DE AMOSTRAGENS | ATVOS
# ============================================================

import datetime as dt
import re
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURAÇÕES GERAIS E PALETA DE CORES
# ============================================================

st.set_page_config(
    page_title="Monitoramento de Entregas - ATVOS",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.set_option("client.toolbarMode", "minimal")

st.html("""
<style>
    header[data-testid="stHeader"] {
        display: none !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
    }

    [data-testid="stToolbarActions"] {
        display: none !important;
    }

    [data-testid="stMainMenu"] {
        display: none !important;
    }

    .stAppViewContainer {
        margin-top: 0 !important;
    }

    .block-container {
        padding-top: 1rem !important;
    }
</style>
""")

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
    "vermelho": "#B91C1C",
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

        .kpi-card-ociosidade {{
            background-color: white;
            border-radius: 20px;
            padding: 20px 22px;
            border: 1px dashed {CORES["borda"]};
            box-shadow: none;
            min-height: 125px;
        }}

        .kpi-value-ociosidade {{
            font-size: 30px;
            color: {CORES["verde_escuro"]};
            font-weight: 800;
            margin-bottom: 4px;
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


def card_kpi_ociosidade(titulo, valor, detalhe):
    st.markdown(
        f"""
        <div class="kpi-card-ociosidade">
            <div class="kpi-label">{titulo}</div>
            <div class="kpi-value-ociosidade">{valor}</div>
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

padrao_pedido = re.compile(
    r"^(?P<prefixo>F|PAV)(?P<ano>\d{4})(?P<remessa>\d{3})S"
    r"(?P<parcial>_parcial)?$",
    flags=re.IGNORECASE,
)


def obter_assinatura_planilhas():
    entrada = Path("pedidos")
    if not entrada.exists():
        return tuple()

    return tuple(
        (str(planilha), planilha.stat().st_mtime_ns, planilha.stat().st_size)
        for planilha in sorted(entrada.rglob("*.xlsx"))
    )


@st.cache_data(ttl=3600, show_spinner="Carregando planilhas do OneDrive...")
def carregar_dados_locais(assinatura_planilhas):
    if not assinatura_planilhas:
        return pd.DataFrame()

    planilhas = [Path(caminho) for caminho, _, _ in assinatura_planilhas]
    arquivos_carregados = []

    for planilha in planilhas:
        match = padrao_pedido.fullmatch(planilha.stem)

        if not match:
            st.warning(
                f"Arquivo ignorado por nome incompatível: {planilha.name}"
            )
            continue

        prefixo = match.group("prefixo").upper()
        ano = match.group("ano")
        remessa = match.group("remessa")
        tipo = "Fertilidade" if prefixo == "F" else "PAV"
        eh_parcial = match.group("parcial") is not None

        try:
            df_temp = pd.read_excel(planilha)
            df_temp.columns = df_temp.columns.astype(str).str.strip()

            df_temp.insert(0, "Remessa", remessa)
            df_temp.insert(1, "Ano", ano)
            df_temp.insert(2, "Tipo", tipo)
            df_temp.insert(3, "Arquivo_Origem", planilha.name)

            arquivos_carregados.append((eh_parcial, planilha.name.lower(), df_temp))

        except PermissionError:
            st.error(
                f"O arquivo {planilha.name} está aberto ou bloqueado. Feche o arquivo e atualize os dados"
            )

        except Exception as e:
            st.error(f"Erro ao ler a planilha {planilha.name}: {e}")

    if not arquivos_carregados:
        return pd.DataFrame()

    # Arquivos completos formam a base sem alterar o comportamento anterior.
    # Parciais, lidos depois, atualizam somente os valores preenchidos das
    # mesmas amostras e acrescentam apenas amostras realmente novas.
    chaves_amostra = ["Ano", "Remessa", "Tipo", "QR-Code"]
    arquivos_base = [
        (nome, df_temp)
        for eh_parcial, nome, df_temp in arquivos_carregados
        if not eh_parcial
    ]
    arquivos_parciais = [
        (nome, df_temp)
        for eh_parcial, nome, df_temp in arquivos_carregados
        if eh_parcial
    ]

    if arquivos_base:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=(
                    "The behavior of DataFrame concatenation with empty or "
                    "all-NA entries is deprecated.*"
                ),
                category=FutureWarning,
            )
            df_consolidado = pd.concat(
                [df_temp for _, df_temp in sorted(arquivos_base)],
                ignore_index=True,
            )
    else:
        df_consolidado = pd.DataFrame()

    for _, df_temp in sorted(arquivos_parciais):
        colunas_faltantes = [
            coluna for coluna in chaves_amostra if coluna not in df_temp.columns
        ]
        if colunas_faltantes:
            arquivo = df_temp["Arquivo_Origem"].iloc[0]
            st.error(
                f"Arquivo {arquivo} ignorado: colunas-chave ausentes: "
                f"{', '.join(colunas_faltantes)}"
            )
            continue

        if df_consolidado.empty:
            df_consolidado = df_temp.copy()
            continue

        colunas_faltantes_base = [
            coluna for coluna in chaves_amostra if coluna not in df_consolidado.columns
        ]
        if colunas_faltantes_base:
            st.error(
                "Não foi possível consolidar arquivos parciais: colunas-chave "
                f"ausentes na base: {', '.join(colunas_faltantes_base)}"
            )
            continue

        for coluna in df_temp.columns.difference(df_consolidado.columns):
            df_consolidado[coluna] = pd.NA
        for coluna in df_consolidado.columns.difference(df_temp.columns):
            df_temp[coluna] = pd.NA
        df_temp = df_temp.reindex(columns=df_consolidado.columns)

        chave_valida_parcial = df_temp[chaves_amostra].notna().all(axis=1)
        chave_valida_parcial &= (
            df_temp["QR-Code"].astype("string").str.strip().ne("").fillna(False)
        )
        df_parcial_valido = df_temp.loc[chave_valida_parcial].copy()
        df_parcial_valido = df_parcial_valido.replace(r"^\s*$", pd.NA, regex=True)

        if df_parcial_valido.duplicated(chaves_amostra).any():
            arquivo = df_temp["Arquivo_Origem"].iloc[0]
            st.warning(
                f"O arquivo {arquivo} contém amostras duplicadas; "
                "foi mantida a última ocorrência de cada QR-Code."
            )
            df_parcial_valido = df_parcial_valido.drop_duplicates(
                chaves_amostra, keep="last"
            )

        chave_valida_base = df_consolidado[chaves_amostra].notna().all(axis=1)
        chave_valida_base &= (
            df_consolidado["QR-Code"]
            .astype("string")
            .str.strip()
            .ne("")
            .fillna(False)
        )
        indices_base = df_consolidado.index[chave_valida_base]
        chaves_base = pd.MultiIndex.from_frame(
            df_consolidado.loc[indices_base, chaves_amostra]
        )
        parcial_indexado = df_parcial_valido.set_index(chaves_amostra)

        atualizacoes = parcial_indexado.reindex(chaves_base)
        atualizacoes.index = indices_base
        df_consolidado.update(atualizacoes)

        chaves_existentes = pd.MultiIndex.from_frame(
            df_consolidado.loc[chave_valida_base, chaves_amostra]
        )
        amostras_novas = parcial_indexado.loc[
            ~parcial_indexado.index.isin(chaves_existentes)
        ].reset_index()
        linhas_sem_chave = df_temp.loc[~chave_valida_parcial]

        linhas_para_adicionar = [
            df_novo
            for df_novo in (amostras_novas, linhas_sem_chave)
            if not df_novo.empty
        ]
        if linhas_para_adicionar:
            df_consolidado = pd.concat(
                [df_consolidado, *linhas_para_adicionar], ignore_index=True
            )

    if df_consolidado.empty:
        return pd.DataFrame()

    return df_consolidado.reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner="Carregando Dados de Área e Solicitações...")
def carregar_solicitacao():
    caminho_solicitacao = Path("atvos_solicitacao2.xlsx")
    if not caminho_solicitacao.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(caminho_solicitacao, sheet_name="tratado")
        df.columns = df.columns.str.strip()

        # Tratamento de tipos
        if "remessa_logistica" in df.columns:
            df["remessa_logistica"] = (
                pd.to_numeric(df["remessa_logistica"], errors="coerce")
                .fillna(-1)
                .astype(int)
                .astype(str)
            )
            df["remessa_logistica"] = df["remessa_logistica"].replace("-1", "")
        if "unidade" in df.columns:
            df["unidade"] = df["unidade"].astype("string").str.strip()

        # Tratamento de datas
        colunas_datas = [
            "data_inicio_amostragem",
            "data_conclusao_amostragem",
            "data_inicio_logistica",
            "data_conclusao_logistica",
            "data_inicio_analise",
            "data_conclusao_analise",
            "data_inicio_laudo",
            "data_conclusao_laudo",
        ]
        for col in colunas_datas:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
    except Exception as e:
        st.error(f"Erro ao carregar solicitações: {e}")
        return pd.DataFrame()


# ============================================================
# PROCESSAMENTO E TRATAMENTO DA BASE PRINCIPAL
# ============================================================

assinatura_pedidos = obter_assinatura_planilhas()
df_bruto = carregar_dados_locais(assinatura_pedidos)
df_solicitacao = carregar_solicitacao()

if df_bruto.empty:
    st.error("Nenhum dado bruto pôde ser carregado da pasta `pedidos`.")
    st.stop()

df_fazendas = pd.read_excel("fazendas.xlsx")
df_fazendas["Nome_Fazenda"] = df_fazendas["Nome_Fazenda"].astype(str).str.strip()
df_fazendas["Cod_Fazenda"] = pd.to_numeric(
    df_fazendas["Cod_Fazenda"], errors="coerce"
).astype("Int64")
df_fazendas = df_fazendas.drop_duplicates(subset=["Cod_Fazenda", "Nome_Fazenda"])

df_bruto = df_bruto.merge(
    df_fazendas, how="inner", left_on="Fazenda", right_on="Cod_Fazenda"
)
df_bruto["Nome_Fazenda"] = df_bruto["Nome_Fazenda"].str.strip()

col_ref = "Ca_(mmolc/dm3)"
if col_ref not in df_bruto.columns:
    st.error(
        f"A coluna de referência '{col_ref}' não foi encontrada nos dados carregados."
    )
    st.stop()

df_bruto["Status"] = df_bruto[col_ref].apply(
    lambda x: "Concluído" if pd.notna(x) else "Pendente"
)


# ============================================================
# SIDEBAR (FILTROS GLOBAIS)
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
        placeholder="Ex: 420136",
        help="Pesquise utilizando o código da fazenda",
    )

    df_filtrado = df_bruto.copy()

    if busca_fazenda:
        termos = [
            re.escape(t.strip().lower())
            for t in re.split(r"[,;\s]+", busca_fazenda)
            if t.strip()
        ]
        if termos:
            padrao_regex = "|".join(termos)
            mask_cod = (
                df_filtrado["Fazenda"]
                .astype(str)
                .str.lower()
                .str.contains(padrao_regex, na=False, regex=True)
            )
            df_filtrado = df_filtrado[mask_cod]

    anos_disponiveis = sorted(df_filtrado["Ano"].dropna().unique())
    ano_select = st.multiselect(
        "Ano", options=anos_disponiveis, default=anos_disponiveis
    )
    if ano_select:
        df_filtrado = df_filtrado[df_filtrado["Ano"].isin(ano_select)]

    tipos_disponiveis = (
        sorted(df_filtrado["Tipo"].unique())
        if "Tipo" in df_filtrado.columns
        else ["Geral"]
    )
    tipo_select = st.multiselect(
        "Tipo de Análise", options=tipos_disponiveis, default=tipos_disponiveis
    )
    if tipo_select:
        df_filtrado = df_filtrado[df_filtrado["Tipo"].isin(tipo_select)]

    remessas_disponiveis = (
        sorted(df_filtrado["Remessa"].unique())
        if "Remessa" in df_filtrado.columns
        else []
    )
    remessa_select = st.multiselect(
        "Remessas", options=remessas_disponiveis, default=remessas_disponiveis
    )
    if remessa_select:
        df_filtrado = df_filtrado[df_filtrado["Remessa"].isin(remessa_select)]

    unidades_disponiveis = (
        sorted(df_filtrado["Unidade"].unique())
        if "Unidade" in df_filtrado.columns
        else []
    )
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
        <div class="hero-title">Monitoramento de Entregas — ATVOS</div>
        <div class="hero-subtitle">
            Acompanhamento do quantitativo de amostras, status de conclusão e áreas mapeadas | 
            Atualizado em {hora_brasilia.strftime("%d/%m/%Y %H:%M")}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ESTRUTURAÇÃO EM ABAS
# ============================================================

tab_geral, tab_prazos_area, tab_planejamento = st.tabs(
    ["Quantitativo e Status", "Prazos e Áreas", "Planejamento Semanal"]
)

with tab_geral:
    st.markdown("###### **Visão Geral de Entregas**")
    if df_filtrado.empty:
        st.info("Nenhum dado corresponde aos filtros selecionados na barra lateral.")
    else:
        total_amostras = len(df_filtrado)
        concluidas = (df_filtrado["Status"] == "Concluído").sum()
        pendentes = (df_filtrado["Status"] == "Pendente").sum()
        pct_progresso = concluidas / total_amostras if total_amostras > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1:
            card_kpi(
                "Total de Amostras",
                f"{format_num(total_amostras)} un",
                "Volume total recebido",
            )
        with c2:
            card_kpi(
                "Entregue",
                f"{format_num(concluidas)} un",
                f"{pct_progresso:.0%} concluído",
            )
        with c3:
            card_kpi(
                "Pendentes",
                f"{format_num(pendentes)} un",
                f"{(1 - pct_progresso):.0%} em andamento",
            )

        st.divider()

        col_graf1, col_graf2 = st.columns(2)

        with col_graf1:
            df_graf_remessa = (
                df_filtrado.groupby(["Remessa", "Status", "Tipo"])
                .size()
                .reset_index(name="Quantidade")
            )
            df_graf_remessa["Remessa"] = df_graf_remessa["Remessa"].astype(str)
            ordem_remessas = sorted(df_graf_remessa["Remessa"].unique())
            tipos_ativos = df_graf_remessa["Tipo"].dropna().unique().tolist()
            ordem_tipos = [
                tipo for tipo in ["Fertilidade", "PAV"] if tipo in tipos_ativos
            ]
            ordem_tipos.extend(
                sorted(tipo for tipo in tipos_ativos if tipo not in ordem_tipos)
            )

            fig_remessa = px.bar(
                df_graf_remessa,
                x="Remessa",
                y="Quantidade",
                color="Status",
                facet_row="Tipo",
                category_orders={"Tipo": ordem_tipos},
                facet_row_spacing=0.15,
                color_discrete_map={
                    "Concluído": CORES["verde"],
                    "Pendente": CORES["vermelho"],
                },
                barmode="stack",
                text_auto=True,
                title="<b>Amostras por Remessa e Tipo</b>",
            )
            fig_remessa.update_layout(
                legend_title_text="Status", separators=",.", yaxis_tickformat=",d"
            )
            fig_remessa.update_yaxes(title_text="Nº Amostras")
            fig_remessa.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=ordem_remessas,
                title_text="",
            )
            fig_remessa.update_traces(textangle=0, cliponaxis=False)

            if len(tipos_ativos) == 2:
                fig_remessa.update_xaxes(
                    showticklabels=True, row=1, col=1, title_text="Remessa"
                )
                fig_remessa.update_xaxes(showticklabels=False, row=2, col=1)
            else:
                fig_remessa.update_xaxes(
                    showticklabels=True, row=1, col=1, title_text="Remessa"
                )

            for idx, anno in enumerate(fig_remessa["layout"]["annotations"]):
                texto_limpo = anno.text.split("=")[-1].strip()
                eixo_y_correto = (
                    "y2 domain"
                    if len(tipos_ativos) == 2 and texto_limpo == "Fertilidade"
                    else "y domain"
                )
                anno.update(
                    text=f"<b>{texto_limpo}</b>",
                    x=0.5,
                    yref=eixo_y_correto,
                    y=1.04,
                    textangle=0,
                    xanchor="center",
                    yanchor="bottom",
                )

            st.plotly_chart(
                aplicar_layout_grafico(fig_remessa, 420), use_container_width=True
            )

        with col_graf2:
            df_graf_unidade = (
                df_filtrado.groupby(["Unidade", "Status"])
                .size()
                .reset_index(name="Quantidade")
            )
            fig_unidade = px.bar(
                df_graf_unidade,
                x="Unidade",
                y="Quantidade",
                color="Status",
                color_discrete_map={
                    "Concluído": CORES["verde"],
                    "Pendente": CORES["vermelho"],
                },
                barmode="stack",
                text_auto=True,
                title="<b>Amostras por Unidade</b>",
            )
            fig_unidade.update_layout(
                xaxis_title="Unidade",
                yaxis_title="Nº Amostras",
                legend_title_text="Status",
                separators=",.",
                yaxis_tickformat=",d",
            )
            st.plotly_chart(
                aplicar_layout_grafico(fig_unidade, 420), use_container_width=True
            )

        st.divider()

        # --- TABELA DE DETALHAMENTO MACRO ---
        st.markdown("### Demonstrativo - Fazendas por Unidade")
        ocultar_concluidas = st.toggle("Esconder fazendas 100% concluídas", value=False)

        col_cod_fazenda, col_nome_fazenda = "Fazenda", "Nome_Fazenda"
        if "Unidade" in df_filtrado.columns:
            for unidade in sorted(df_filtrado["Unidade"].dropna().unique()):
                df_unidade = df_filtrado[df_filtrado["Unidade"] == unidade]
                t_uni, c_uni = (
                    len(df_unidade),
                    (df_unidade["Status"] == "Concluído").sum(),
                )
                p_uni = c_uni / t_uni if t_uni > 0 else 0

                icone = "✅" if p_uni == 1 else "⏳" if p_uni > 0 else "🔴"
                with st.expander(
                    f"{icone} Unidade {unidade} — {p_uni:.1%} Concluído ({c_uni} de {t_uni} amostras)"
                ):
                    resumo = (
                        df_unidade.groupby(
                            ["Remessa", "Tipo", col_cod_fazenda, col_nome_fazenda]
                        )
                        .agg(
                            Total=("Status", "count"),
                            Realizadas=("Status", lambda x: (x == "Concluído").sum()),
                            Faltantes=("Status", lambda x: (x == "Pendente").sum()),
                        )
                        .reset_index()
                    )
                    resumo["Progresso"] = (resumo["Realizadas"] / resumo["Total"]) * 100

                    if ocultar_concluidas:
                        resumo = resumo[resumo["Progresso"] < 100]

                    if resumo.empty:
                        st.success("Todas as fazendas desta unidade estão concluídas.")
                    else:
                        st.dataframe(
                            resumo.sort_values(
                                by=["Progresso", "Total"], ascending=[True, False]
                            ),
                            column_config={
                                "Total": st.column_config.NumberColumn("Total"),
                                "Realizadas": st.column_config.NumberColumn(
                                    "✅ Realizadas"
                                ),
                                "Faltantes": st.column_config.NumberColumn(
                                    "⏳ Faltantes"
                                ),
                                "Progresso": st.column_config.ProgressColumn(
                                    "% Conclusão",
                                    format="%.1f %%",
                                    min_value=0,
                                    max_value=100,
                                ),
                                "Remessa": st.column_config.TextColumn("Remessa"),
                            },
                            hide_index=True,
                            use_container_width=True,
                        )

        # ============================================================
        # DRILL-DOWN Unidade > Fazenda > Talhão > Amostra
        # ============================================================
        st.divider()
        st.markdown("### Detalhamento Operacional")
        st.caption(
            "Navegue da unidade até as amostras individuais e localize rapidamente "
            "os talhões que ainda possuem pendências."
        )

        if "Unidade" not in df_filtrado.columns:
            st.warning("A coluna 'Unidade' não foi encontrada nos dados carregados.")
        elif "Fazenda" not in df_filtrado.columns:
            st.warning("A coluna 'Fazenda' não foi encontrada nos dados carregados.")
        elif "Talhão" not in df_filtrado.columns:
            st.warning("A coluna 'Talhão' não foi encontrada nos dados carregados.")
        else:
            unidades_drill = sorted(
                df_filtrado["Unidade"].dropna().astype(str).unique().tolist()
            )

            if not unidades_drill:
                st.info("Nenhuma unidade disponível nos filtros atuais.")
            else:
                col_drill1, col_drill2, col_drill3, col_drill4 = st.columns(
                    [1.0, 2.2, 1.1, 1.3]
                )

                with col_drill1:
                    unidade_drill = st.selectbox(
                        "Unidade",
                        options=unidades_drill,
                        key="drill_unidade",
                    )

                df_drill_unidade = df_filtrado[
                    df_filtrado["Unidade"].astype(str) == unidade_drill
                ].copy()

                fazendas_drill = (
                    df_drill_unidade[[col_cod_fazenda, col_nome_fazenda]]
                    .dropna(subset=[col_cod_fazenda])
                    .drop_duplicates(subset=[col_cod_fazenda])
                    .copy()
                )
                fazendas_drill["codigo_texto"] = fazendas_drill[
                    col_cod_fazenda
                ].map(
                    lambda valor: (
                        str(int(valor))
                        if isinstance(valor, (int, float)) and float(valor).is_integer()
                        else str(valor)
                    )
                )
                fazendas_drill["nome_texto"] = (
                    fazendas_drill[col_nome_fazenda]
                    .fillna("Fazenda sem descrição")
                    .astype(str)
                    .str.strip()
                )
                fazendas_drill["rotulo"] = (
                    fazendas_drill["codigo_texto"]
                    + " — "
                    + fazendas_drill["nome_texto"]
                )
                fazendas_drill = fazendas_drill.sort_values(
                    ["nome_texto", "codigo_texto"]
                )

                opcoes_fazenda = fazendas_drill["rotulo"].tolist()
                indice_fazenda = 0
                if busca_fazenda and opcoes_fazenda:
                    termos_busca = [
                        termo.strip()
                        for termo in re.split(r"[,;\s]+", busca_fazenda)
                        if termo.strip()
                    ]
                    if termos_busca:
                        codigo_busca = termos_busca[0]
                        indices_encontrados = fazendas_drill.index[
                            fazendas_drill["codigo_texto"] == codigo_busca
                        ].tolist()
                        if indices_encontrados:
                            rotulo_encontrado = fazendas_drill.loc[
                                indices_encontrados[0], "rotulo"
                            ]
                            indice_fazenda = opcoes_fazenda.index(rotulo_encontrado)

                with col_drill2:
                    fazenda_drill = st.selectbox(
                        "Fazenda",
                        options=opcoes_fazenda,
                        index=indice_fazenda if opcoes_fazenda else None,
                        placeholder="Selecione uma fazenda",
                        key="drill_fazenda",
                    )

                if fazenda_drill:
                    registro_fazenda = fazendas_drill[
                        fazendas_drill["rotulo"] == fazenda_drill
                    ].iloc[0]
                    codigo_fazenda_drill = registro_fazenda[col_cod_fazenda]
                    codigo_fazenda_texto = registro_fazenda["codigo_texto"]
                    nome_fazenda_drill = registro_fazenda["nome_texto"]

                    df_drill_fazenda = df_drill_unidade[
                        df_drill_unidade[col_cod_fazenda] == codigo_fazenda_drill
                    ].copy()

                    tipos_drill = (
                        sorted(
                            df_drill_fazenda["Tipo"]
                            .dropna()
                            .astype(str)
                            .unique()
                            .tolist()
                        )
                        if "Tipo" in df_drill_fazenda.columns
                        else []
                    )

                    with col_drill3:
                        tipo_drill = st.selectbox(
                            "Tipo",
                            options=["Todos"] + tipos_drill,
                            key="drill_tipo",
                        )

                    with col_drill4:
                        somente_pendentes_drill = st.toggle(
                            "Somente pendentes",
                            value=False,
                            key="drill_somente_pendentes",
                        )

                    if tipo_drill != "Todos" and "Tipo" in df_drill_fazenda.columns:
                        df_drill_fazenda = df_drill_fazenda[
                            df_drill_fazenda["Tipo"].astype(str) == tipo_drill
                        ].copy()

                    total_fazenda = len(df_drill_fazenda)
                    entregues_fazenda = (
                        df_drill_fazenda["Status"] == "Concluído"
                    ).sum()
                    pendentes_fazenda = (
                        df_drill_fazenda["Status"] == "Pendente"
                    ).sum()
                    progresso_fazenda = (
                        entregues_fazenda / total_fazenda
                        if total_fazenda > 0
                        else 0
                    )

                    st.markdown(
                        f"**{codigo_fazenda_texto} — {nome_fazenda_drill}** "
                        f"· Unidade **{unidade_drill}**"
                    )

                    c_drill1, c_drill2, c_drill3, c_drill4 = st.columns(4)
                    with c_drill1:
                        card_kpi(
                            "Total da fazenda",
                            f"{format_num(total_fazenda)} un",
                            "Amostras nos filtros atuais",
                        )
                    with c_drill2:
                        card_kpi(
                            "Entregues",
                            f"{format_num(entregues_fazenda)} un",
                            f"{progresso_fazenda:.1%} concluído",
                        )
                    with c_drill3:
                        card_kpi(
                            "Pendentes",
                            f"{format_num(pendentes_fazenda)} un",
                            f"{(1 - progresso_fazenda):.1%} em aberto",
                        )
                    with c_drill4:
                        card_kpi(
                            "Progresso",
                            f"{progresso_fazenda:.1%}",
                            "Percentual entregue",
                        )

                    df_drill_fazenda["Talhão_drill"] = (
                        df_drill_fazenda["Talhão"]
                        .astype("string")
                        .fillna("Sem talhão")
                    )
                    if "Tipo" in df_drill_fazenda.columns:
                        df_drill_fazenda["Tipo_drill"] = (
                            df_drill_fazenda["Tipo"]
                            .astype("string")
                            .fillna("Sem tipo")
                        )
                    else:
                        df_drill_fazenda["Tipo_drill"] = "Sem tipo"

                    resumo_talhoes = (
                        df_drill_fazenda.groupby(
                            ["Talhão_drill", "Tipo_drill"],
                            as_index=False,
                        )
                        .agg(
                            Total=("Status", "size"),
                            Entregues=(
                                "Status",
                                lambda valores: (valores == "Concluído").sum(),
                            ),
                            Pendentes=(
                                "Status",
                                lambda valores: (valores == "Pendente").sum(),
                            ),
                        )
                    )
                    resumo_talhoes["Progresso"] = (
                        resumo_talhoes["Entregues"] / resumo_talhoes["Total"]
                    ) * 100
                    resumo_talhoes = resumo_talhoes.rename(
                        columns={
                            "Talhão_drill": "Talhão",
                            "Tipo_drill": "Tipo",
                        }
                    )

                    if somente_pendentes_drill:
                        resumo_talhoes = resumo_talhoes[
                            resumo_talhoes["Pendentes"] > 0
                        ].copy()

                    resumo_talhoes = resumo_talhoes.sort_values(
                        ["Pendentes", "Progresso", "Total"],
                        ascending=[False, True, False],
                    ).reset_index(drop=True)

                    st.markdown("##### Progresso por talhão")
                    st.caption(
                        "Selecione uma linha para abrir as amostras daquele talhão."
                    )

                    if resumo_talhoes.empty:
                        st.success(
                            "Não existem talhões pendentes para os filtros selecionados."
                        )
                    else:
                        selecao_talhao = st.dataframe(
                            resumo_talhoes,
                            column_config={
                                "Talhão": st.column_config.TextColumn("Talhão"),
                                "Tipo": st.column_config.TextColumn("Tipo"),
                                "Total": st.column_config.NumberColumn("Total"),
                                "Entregues": st.column_config.NumberColumn(
                                    "✅ Entregues"
                                ),
                                "Pendentes": st.column_config.NumberColumn(
                                    "⏳ Pendentes"
                                ),
                                "Progresso": st.column_config.ProgressColumn(
                                    "% Conclusão",
                                    format="%.1f %%",
                                    min_value=0,
                                    max_value=100,
                                ),
                            },
                            hide_index=True,
                            use_container_width=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            key="drill_tabela_talhoes",
                        )

                        linhas_selecionadas = selecao_talhao.selection.rows
                        if linhas_selecionadas:
                            linha_talhao = resumo_talhoes.iloc[
                                linhas_selecionadas[0]
                            ]
                            talhao_selecionado = str(linha_talhao["Talhão"])
                            tipo_talhao_selecionado = str(linha_talhao["Tipo"])

                            df_amostras_talhao = df_drill_fazenda[
                                (
                                    df_drill_fazenda["Talhão_drill"].astype(str)
                                    == talhao_selecionado
                                )
                                & (
                                    df_drill_fazenda["Tipo_drill"].astype(str)
                                    == tipo_talhao_selecionado
                                )
                            ].copy()

                            if somente_pendentes_drill:
                                df_amostras_talhao = df_amostras_talhao[
                                    df_amostras_talhao["Status"] == "Pendente"
                                ].copy()

                            st.markdown(
                                f"##### Amostras do talhão {talhao_selecionado}"
                            )

                            colunas_amostras = [
                                "QR-Code",
                                "Remessa",
                                "Ponto",
                                "Profundidade",
                                "Status"
                            ]
                            colunas_amostras = [
                                coluna
                                for coluna in colunas_amostras
                                if coluna in df_amostras_talhao.columns
                            ]
                            df_amostras_exibicao = df_amostras_talhao[
                                colunas_amostras
                            ].copy()

                            st.dataframe(
                                df_amostras_exibicao,
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Data": st.column_config.DateColumn(
                                        "Data", format="DD/MM/YYYY"
                                    ),
                                    "Data_Emissao": st.column_config.DateColumn(
                                        "Data de emissão", format="DD/MM/YYYY"
                                    ),
                                },
                            )

                            csv_amostras = df_amostras_exibicao.to_csv(
                                index=False,
                                sep=";",
                                decimal=",",
                            ).encode("utf-8-sig")
                            st.download_button(
                                "Baixar amostras do talhão",
                                data=csv_amostras,
                                file_name=(
                                    f"amostras_{codigo_fazenda_texto}_"
                                    f"talhao_{talhao_selecionado}.csv"
                                ),
                                mime="text/csv",
                                key="download_amostras_talhao",
                            )
                        else:
                            st.info(
                                "Selecione um talhão na tabela para visualizar "
                                "as amostras individuais."
                            )


with tab_prazos_area:
    if not df_solicitacao.empty:
        df_sol_filtrado = df_solicitacao.copy()

        # ============================================================
        # SINCRONIZAÇÃO DE FILTROS DA SIDEBAR
        # ============================================================
        if busca_fazenda:
            termos = [
                re.escape(t.strip().lower())
                for t in re.split(r"[,;\s]+", busca_fazenda)
                if t.strip()
            ]
            if termos and "cod_fazenda" in df_sol_filtrado.columns:
                padrao_regex = "|".join(termos)
                mask_cod_sol = (
                    df_sol_filtrado["cod_fazenda"]
                    .astype(str)
                    .str.lower()
                    .str.contains(padrao_regex, na=False, regex=True)
                )
                df_sol_filtrado = df_sol_filtrado[mask_cod_sol]

        if (
            tipo_select
            and len(tipo_select) < len(tipos_disponiveis)
            and "tipo_amostra" in df_sol_filtrado.columns
        ):
            df_sol_filtrado = df_sol_filtrado[
                df_sol_filtrado["tipo_amostra"].isin(tipo_select)
            ]

        if (
            remessa_select
            and len(remessa_select) < len(remessas_disponiveis)
            and "remessa_logistica" in df_sol_filtrado.columns
        ):
            remessas_limpas = [
                str(int(r)) if str(r).isdigit() else str(r) for r in remessa_select
            ]
            df_sol_filtrado = df_sol_filtrado[
                df_sol_filtrado["remessa_logistica"].isin(remessas_limpas)
            ]

        if (
            unidade_select
            and len(unidade_select) < len(unidades_disponiveis)
            and "unidade" in df_sol_filtrado.columns
        ):
            unidades_limpas = [str(u).strip() for u in unidade_select]
            df_sol_filtrado = df_sol_filtrado[
                df_sol_filtrado["unidade"].isin(unidades_limpas)
            ]

        if "area_ha" in df_sol_filtrado.columns:

            # ============================================================
            # 1. CÁLCULO DE ÁREAS GERAIS
            # ============================================================
            df_sol_filtrado = df_sol_filtrado[df_sol_filtrado["status_geral"].fillna("").str.strip().str.casefold() != "cancelado"].copy()
            area_total = df_sol_filtrado["area_ha"].sum()
            area_amostrada = (
                df_sol_filtrado.loc[
                    df_sol_filtrado["data_conclusao_amostragem"].notna(), "area_ha"
                ].sum()
                if "data_conclusao_amostragem" in df_sol_filtrado.columns
                else 0
            )
            area_logistica = (
                df_sol_filtrado.loc[
                    df_sol_filtrado["data_conclusao_logistica"].notna(), "area_ha"
                ].sum()
                if "data_conclusao_logistica" in df_sol_filtrado.columns
                else 0
            )
            area_analisada = (
                df_sol_filtrado.loc[
                    df_sol_filtrado["data_conclusao_analise"].notna(), "area_ha"
                ].sum()
                if "data_conclusao_analise" in df_sol_filtrado.columns
                else 0
            )

            # ============================================================
            # 2. CÁLCULO DE TEMPOS (CICLO E ESPERA)
            # ============================================================

            # --- Ciclo de Execução (Trabalho Real) ---
            if (
                "data_inicio_amostragem" in df_sol_filtrado.columns
                and "data_conclusao_amostragem" in df_sol_filtrado.columns
            ):
                diferenca_amos = (
                    df_sol_filtrado["data_conclusao_amostragem"]
                    - df_sol_filtrado["data_inicio_amostragem"]
                ).dt.days
                df_sol_filtrado["ciclo_amos"] = diferenca_amos.clip(lower=1)
                avg_ciclo_amos = df_sol_filtrado["ciclo_amos"].median()
            else:
                avg_ciclo_amos = float("nan")

            if (
                "data_inicio_logistica" in df_sol_filtrado.columns
                and "data_conclusao_logistica" in df_sol_filtrado.columns
            ):
                diferenca_log = (
                    df_sol_filtrado["data_conclusao_logistica"]
                    - df_sol_filtrado["data_inicio_logistica"]
                ).dt.days
                df_sol_filtrado["ciclo_log"] = diferenca_log.clip(lower=1)
                avg_ciclo_log = df_sol_filtrado["ciclo_log"].median()
            else:
                avg_ciclo_log = float("nan")

            if (
                "data_inicio_analise" in df_sol_filtrado.columns
                and "data_conclusao_analise" in df_sol_filtrado.columns
            ):
                diferenca_ana = (
                    df_sol_filtrado["data_conclusao_analise"]
                    - df_sol_filtrado["data_inicio_analise"]
                ).dt.days
                df_sol_filtrado["ciclo_ana"] = diferenca_ana.clip(lower=1)
                avg_ciclo_ana = df_sol_filtrado["ciclo_ana"].median()
            else:
                avg_ciclo_ana = float("nan")

            if (
                "data_inicio_laudo" in df_sol_filtrado.columns
                and "data_conclusao_laudo" in df_sol_filtrado.columns
            ):
                diferenca_laudo = (
                    df_sol_filtrado["data_conclusao_laudo"]
                    - df_sol_filtrado["data_inicio_laudo"]
                ).dt.days
                df_sol_filtrado["ciclo_laudo"] = diferenca_laudo.clip(lower=1)
                avg_ciclo_laudo = df_sol_filtrado["ciclo_laudo"].median()
            else:
                avg_ciclo_laudo = float("nan")

            # --- Tempos de Espera (Ociosidade) ---
            if (
                "data_conclusao_amostragem" in df_sol_filtrado.columns
                and "data_inicio_logistica" in df_sol_filtrado.columns
            ):
                df_sol_filtrado["espera_campo_log"] = (
                    df_sol_filtrado["data_inicio_logistica"]
                    - df_sol_filtrado["data_conclusao_amostragem"]
                ).dt.days
                avg_espera_campo_log = df_sol_filtrado.loc[
                    df_sol_filtrado["espera_campo_log"] >= 0, "espera_campo_log"
                ].median()
            else:
                avg_espera_campo_log = float("nan")

            if (
                "data_conclusao_logistica" in df_sol_filtrado.columns
                and "data_inicio_analise" in df_sol_filtrado.columns
            ):
                df_sol_filtrado["espera_log_lab"] = (
                    df_sol_filtrado["data_inicio_analise"]
                    - df_sol_filtrado["data_conclusao_logistica"]
                ).dt.days
                avg_espera_log_lab = df_sol_filtrado.loc[
                    df_sol_filtrado["espera_log_lab"] >= 0, "espera_log_lab"
                ].median()
            else:
                avg_espera_log_lab = float("nan")

            # ============================================================
            # 3. RENDERIZAÇÃO DA TELA (KPIs E GRÁFICOS)
            # ============================================================

            # --- Bloco 1: Tempos Operacionais (2 Linhas) ---
            st.markdown("###### **Lead Time Operacional**")

            c1, c2, c3, c4, c5, c6 = st.columns(6)

            with c1:
                valor_ciclo = (
                    f"{avg_ciclo_amos:.0f} dias" if pd.notna(avg_ciclo_amos) else "N/A"
                )
                card_kpi("1. Coleta", valor_ciclo, "Amostragem")

            with c2:
                valor_espera = (
                    f"{avg_espera_campo_log:.0f} dias"
                    if pd.notna(avg_espera_campo_log)
                    else "N/A"
                )
                card_kpi_ociosidade(
                    "Ociosidade: Logística", valor_espera, "Até embarque"
                )

            with c3:
                valor_ciclo = (
                    f"{avg_ciclo_log:.0f} dias" if pd.notna(avg_ciclo_log) else "N/A"
                )
                card_kpi("2. Transporte", valor_ciclo, "Transporte das amostras")

            with c4:
                valor_espera = (
                    f"{avg_espera_log_lab:.0f} dias"
                    if pd.notna(avg_espera_log_lab)
                    else "N/A"
                )
                card_kpi_ociosidade(
                    "Ociosidade: Processos", valor_espera, "Até bancada"
                )

            with c5:
                valor_ciclo = (
                    f"{avg_ciclo_ana:.0f} dias" if pd.notna(avg_ciclo_ana) else "N/A"
                )
                card_kpi(
                    "3. Laboratório Químico", valor_ciclo, "Análises laboratoriais"
                )

            with c6:
                valor_ciclo = (
                    f"{avg_ciclo_laudo:.0f} dias"
                    if pd.notna(avg_ciclo_laudo)
                    else "N/A"
                )
                card_kpi("4. Gestão de Dados", valor_ciclo, "Emissão dos laudos")

            st.divider()

            # --- Bloco 2: Quantitativo de Área ---
            st.markdown("###### **Quantificação de Área**")
            c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

            with c_kpi1:
                card_kpi(
                    "Área Total (ha)",
                    f"{format_num(area_total)} ha",
                    "Área total em hectares da planilha base",
                )
            with c_kpi2:
                card_kpi(
                    "Área Amostrada (ha)",
                    f"{format_num(area_amostrada)} ha",
                    f"{(area_amostrada / area_total if area_total else 0):.1%} do total",
                )
            with c_kpi3:
                card_kpi(
                    "Área Logística Completa (ha)",
                    f"{format_num(area_logistica)} ha",
                    f"{(area_logistica / area_total if area_total else 0):.1%} do total",
                )
            with c_kpi4:
                card_kpi(
                    "Área Analisada (ha)",
                    f"{format_num(area_analisada)} ha",
                    f"{(area_analisada / area_total if area_total else 0):.1%} do total",
                )

            st.divider()

            # --- Bloco 3: Evolução Temporal (Gráfico Funil) ---
            st.markdown("##### **Ritmo de execução e entregas**")
            st.caption("Monitoramento do volume de hectares concluídos.")

            df_evo = pd.DataFrame()

            if "data_conclusao_amostragem" in df_sol_filtrado.columns:
                amos_evo = (
                    df_sol_filtrado.dropna(subset=["data_conclusao_amostragem"])
                    .groupby(pd.Grouper(key="data_conclusao_amostragem", freq="W"))[
                        "area_ha"
                    ]
                    .sum()
                    .reset_index()
                )
                amos_evo.columns = ["Data", "Area"]
                amos_evo["Etapa"] = "1.Área Amostrada (ha)"
                df_evo = pd.concat([df_evo, amos_evo])

            if "data_conclusao_logistica" in df_sol_filtrado.columns:
                log_evo = (
                    df_sol_filtrado.dropna(subset=["data_conclusao_logistica"])
                    .groupby(pd.Grouper(key="data_conclusao_logistica", freq="W"))[
                        "area_ha"
                    ]
                    .sum()
                    .reset_index()
                )
                log_evo.columns = ["Data", "Area"]
                log_evo["Etapa"] = "2.Área Logística Completa (ha)"
                df_evo = pd.concat([df_evo, log_evo])

            if "data_conclusao_analise" in df_sol_filtrado.columns:
                ana_evo = (
                    df_sol_filtrado.dropna(subset=["data_conclusao_analise"])
                    .groupby(pd.Grouper(key="data_conclusao_analise", freq="W"))[
                        "area_ha"
                    ]
                    .sum()
                    .reset_index()
                )
                ana_evo.columns = ["Data", "Area"]
                ana_evo["Etapa"] = "3.Área Analisada (ha)"
                df_evo = pd.concat([df_evo, ana_evo])

            if not df_evo.empty:
                df_evo_pivot = df_evo.pivot_table(
                    index="Data", columns="Etapa", values="Area", aggfunc="sum"
                ).fillna(0)
                df_pivot_acumulado = df_evo_pivot.cumsum()

                df_evo_plot = df_pivot_acumulado.reset_index().melt(
                    id_vars="Data", value_name="Area_Acumulada"
                )

                fig_evo = px.area(
                    df_evo_plot,
                    x="Data",
                    y="Area_Acumulada",
                    color="Etapa",
                    color_discrete_map={
                        "1.Área Amostrada (ha)": CORES["verde_claro"],
                        "2.Área Logística Completa (ha)": CORES["verde"],
                        "3.Área Analisada (ha)": CORES["verde_escuro"],
                    },
                    line_shape="linear",
                )
                fig_evo.update_traces(stackgroup=None, fill="tozeroy")
                fig_evo.update_layout(
                    xaxis_title="Período",
                    yaxis_title="Área Acumulada (ha)",
                    hovermode="x unified",
                    separators=".,",
                )
                fig_evo.update_yaxes(tickformat=".0f")

                st.plotly_chart(
                    aplicar_layout_grafico(fig_evo, 450), use_container_width=True
                )

        else:
            st.warning(
                "A coluna de área ('area_ha') não foi encontrada no arquivo de solicitações."
            )

with tab_planejamento:
    st.markdown("###### Planejamento e Backlog")
    st.caption(
        "Visão das áreas ativas ainda não entregues, organizada pela etapa real do processo."
    )

    if df_solicitacao.empty:
        st.warning("Não há dados de solicitações disponíveis para o planejamento.")
    else:
        df_plan = df_solicitacao.copy()

        # Mantém os filtros globais também na visão de planejamento.
        if busca_fazenda and "cod_fazenda" in df_plan.columns:
            termos = [
                re.escape(t.strip().lower())
                for t in re.split(r"[,;\s]+", busca_fazenda)
                if t.strip()
            ]
            if termos:
                padrao_regex = "|".join(termos)
                mask_cod_plan = (
                    df_plan["cod_fazenda"]
                    .astype(str)
                    .str.lower()
                    .str.contains(padrao_regex, na=False, regex=True)
                )
                df_plan = df_plan[mask_cod_plan]

        if (
            ano_select
            and len(ano_select) < len(anos_disponiveis)
            and "data_solicitacao" in df_plan.columns
        ):
            anos_plan = pd.to_numeric(pd.Series(ano_select), errors="coerce").dropna()
            datas_solicitacao = pd.to_datetime(
                df_plan["data_solicitacao"], errors="coerce"
            )
            df_plan = df_plan[datas_solicitacao.dt.year.isin(anos_plan.astype(int))]

        if (
            tipo_select
            and len(tipo_select) < len(tipos_disponiveis)
            and "tipo_amostra" in df_plan.columns
        ):
            df_plan = df_plan[df_plan["tipo_amostra"].isin(tipo_select)]

        if (
            remessa_select
            and len(remessa_select) < len(remessas_disponiveis)
            and "remessa_logistica" in df_plan.columns
        ):
            remessas_plan = [
                str(int(r)) if str(r).isdigit() else str(r) for r in remessa_select
            ]
            remessa_base = (
                pd.to_numeric(df_plan["remessa_logistica"], errors="coerce")
                .astype("Int64")
                .astype(str)
            )
            df_plan = df_plan[remessa_base.isin(remessas_plan)]

        if (
            unidade_select
            and len(unidade_select) < len(unidades_disponiveis)
            and "unidade" in df_plan.columns
        ):
            unidades_plan = [str(u).strip() for u in unidade_select]
            df_plan = df_plan[
                df_plan["unidade"].astype(str).str.strip().isin(unidades_plan)
            ]

        if "status_geral" in df_plan.columns:
            mask_cancelado = (
                df_plan["status_geral"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.casefold()
                .eq("cancelado")
            )
            df_plan = df_plan[~mask_cancelado].copy()

        if "area_ha" not in df_plan.columns:
            st.warning(
                "A coluna de área ('area_ha') não foi encontrada nas solicitações."
            )
        else:
            df_plan["area_ha"] = pd.to_numeric(
                df_plan["area_ha"], errors="coerce"
            )

            colunas_datas_plan = [
                "data_solicitacao",
                "data_conclusao_amostragem",
                "data_conclusao_logistica",
                "data_conclusao_analise",
                "data_conclusao_laudo",
            ]
            for coluna in colunas_datas_plan:
                if coluna not in df_plan.columns:
                    df_plan[coluna] = pd.NaT
                else:
                    df_plan[coluna] = pd.to_datetime(
                        df_plan[coluna], errors="coerce"
                    )

            # A data preenchida é a fonte de verdade para a conclusão da etapa.
            df_plan["etapa_planejamento"] = "Concluído"
            df_plan.loc[
                df_plan["data_conclusao_laudo"].isna(), "etapa_planejamento"
            ] = "Aguardando laudo"
            df_plan.loc[
                df_plan["data_conclusao_analise"].isna(), "etapa_planejamento"
            ] = "Aguardando análise"
            df_plan.loc[
                df_plan["data_conclusao_logistica"].isna(), "etapa_planejamento"
            ] = "Aguardando logística"
            df_plan.loc[
                df_plan["data_conclusao_amostragem"].isna(),
                "etapa_planejamento",
            ] = "Aguardando amostragem"

            df_backlog = df_plan[
                df_plan["etapa_planejamento"] != "Concluído"
            ].copy()

            hoje = pd.Timestamp.now(
                tz="America/Sao_Paulo"
            ).tz_localize(None).normalize()

            df_backlog["idade_dias"] = (
                hoje - df_backlog["data_solicitacao"]
            ).dt.days

            df_backlog["idade_dias"] = df_backlog["idade_dias"].clip(lower=0)
            df_backlog["faixa_idade"] = pd.cut(
                df_backlog["idade_dias"],
                bins=[-1, 15, 30, 60, float("inf")],
                labels=["Até 15 dias", "16 a 30 dias", "31 a 60 dias", "Acima de 60 dias"],
            ).astype("string")
            df_backlog["faixa_idade"] = df_backlog["faixa_idade"].fillna(
                "Sem data"
            )

            # Área total em backlog
            area_backlog = df_backlog["area_ha"].sum()

            # Área aguardando amostragem
            area_amos_pendente = df_backlog.loc[
                df_backlog["etapa_planejamento"] == "Aguardando amostragem",
                "area_ha"
            ].sum()

            # Área aguardando logística
            area_log_pendente = df_backlog.loc[
                df_backlog["etapa_planejamento"] == "Aguardando logística",
                "area_ha"
            ].sum()

            # Área aguardando análise
            area_ana_pendente = df_backlog.loc[
                df_backlog["etapa_planejamento"] == "Aguardando análise",
                "area_ha"
            ].sum()

            # Área de prioridade
            area_urgente = df_backlog.loc[
                df_backlog.get(
                    "prioridade_amostragem",
                    pd.Series(index=df_backlog.index, dtype="object")
                )
                .fillna("")
                .astype(str)
                .str.strip()
                .str.casefold()
                .eq("urgente"),
                "area_ha"
            ].sum()

            c_plan1, c_plan2, c_plan3, c_plan4, c_plan5 = st.columns(5)
            with c_plan1:
                card_kpi(
                    "Backlog ativo",
                    f"{format_num(area_backlog)} ha",
                    f"{len(df_backlog):,.0f}".replace(",", ".")
                    + " registros pendentes"
                )
            with c_plan2:
                card_kpi(
                    "Aguardando amostragem",
                    f"{format_num(area_amos_pendente)} ha",
                    "Área ainda sem conclusão de campo"
                )
            with c_plan3:
                card_kpi(
                    "Aguardando logística",
                    f"{format_num(area_log_pendente)} ha",
                    "Coletada e ainda não transportada",
                )
            with c_plan4:
                card_kpi(
                    "Aguardando análise",
                    f"{format_num(area_ana_pendente)} ha",
                    "Logística concluída e análise pendente",
                )
            with c_plan5:
                card_kpi(
                    "Prioridade urgente",
                    f"{format_num(area_urgente)} ha",
                    "Área urgente ainda sem laudo",
                )

            st.divider()

            etapa_ordem = [
                "Aguardando amostragem",
                "Aguardando logística",
                "Aguardando análise",
                "Aguardando laudo",
            ]

            col_graf1, col_graf2 = st.columns(2)

            with col_graf1:
                st.markdown("###### Área pendente por unidade e prioridade")

                df_unidade_prioridade = df_backlog.copy()
                df_unidade_prioridade["unidade_planejamento"] = (
                    df_unidade_prioridade.get(
                        "unidade",
                        pd.Series(
                            index=df_unidade_prioridade.index,
                            dtype="object",
                        ),
                    )
                    .fillna("Sem unidade")
                    .astype(str)
                    .str.strip()
                    .replace("", "Sem unidade")
                )
                df_unidade_prioridade["prioridade_planejamento"] = (
                    df_unidade_prioridade.get(
                        "prioridade_amostragem",
                        pd.Series(
                            index=df_unidade_prioridade.index,
                            dtype="object",
                        ),
                    )
                    .fillna("Sem prioridade")
                    .astype(str)
                    .str.strip()
                    .replace("", "Sem prioridade")
                )

                unidade_prioridade_resumo = (
                    df_unidade_prioridade.groupby(
                        ["unidade_planejamento", "prioridade_planejamento"],
                        as_index=False,
                    )
                    .agg(area_ha=("area_ha", "sum"), registros=("area_ha", "size"))
                )
                unidade_ordem = (
                    unidade_prioridade_resumo.groupby("unidade_planejamento")[
                        "area_ha"
                    ]
                    .sum()
                    .sort_values(ascending=False)
                    .index.tolist()
                )
                prioridades_base = ["Urgente", "Alta", "Média", "Sem prioridade"]
                prioridades_extras = sorted(
                    set(
                        unidade_prioridade_resumo[
                            "prioridade_planejamento"
                        ].tolist()
                    )
                    - set(prioridades_base)
                )
                prioridade_ordem_grafico = prioridades_base + prioridades_extras

                fig_unidade_prioridade = px.bar(
                    unidade_prioridade_resumo,
                    x="unidade_planejamento",
                    y="area_ha",
                    color="prioridade_planejamento",
                    color_discrete_map={
                        "Urgente": CORES["vermelho"],
                        "Alta": CORES["alerta"],
                        "Média": CORES["verde"],
                        "Sem prioridade": CORES["cinza"],
                    },
                    category_orders={
                        "unidade_planejamento": unidade_ordem,
                        "prioridade_planejamento": prioridade_ordem_grafico,
                    },
                    custom_data=["registros"],
                )
                fig_unidade_prioridade.update_traces(
                    hovertemplate=(
                        "<b>%{x}</b><br>%{y:,.0f} ha"
                        "<br>%{customdata[0]} registros<extra></extra>"
                    ),
                )
                fig_unidade_prioridade.update_layout(
                    barmode="stack",
                    xaxis_title="Unidade",
                    yaxis_title="Área pendente (ha)",
                    legend_title_text="Prioridade",
                    separators=".,",
                )
                st.plotly_chart(
                    aplicar_layout_grafico(fig_unidade_prioridade, 360),
                    use_container_width=True,
                )

            with col_graf2:
                st.markdown("###### Envelhecimento do backlog")
                faixa_ordem = [
                    "Até 15 dias",
                    "16 a 30 dias",
                    "31 a 60 dias",
                    "Acima de 60 dias",
                    "Sem data",
                ]
                faixa_resumo = (
                    df_backlog.groupby("faixa_idade", as_index=False)
                    .agg(area_ha=("area_ha", "sum"), registros=("area_ha", "size"))
                    .set_index("faixa_idade")
                    .reindex(faixa_ordem, fill_value=0)
                    .reset_index()
                )
                faixa_resumo["rotulo"] = faixa_resumo["area_ha"].map(
                    lambda valor: f"{format_num(valor)} ha"
                )

                fig_idade = px.bar(
                    faixa_resumo,
                    x="faixa_idade",
                    y="area_ha",
                    color="faixa_idade",
                    color_discrete_map={
                        "Até 15 dias": CORES["verde_claro"],
                        "16 a 30 dias": CORES["verde"],
                        "31 a 60 dias": CORES["alerta"],
                        "Acima de 60 dias": CORES["vermelho"],
                        "Sem data": CORES["cinza"],
                    },
                    text="rotulo",
                    custom_data=["registros"],
                )
                fig_idade.update_traces(
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{x}</b><br>%{y:,.0f} ha"
                        "<br>%{customdata[0]} registros<extra></extra>"
                    ),
                )
                fig_idade.update_layout(
                    showlegend=False,
                    xaxis_title="Idade desde a solicitação",
                    yaxis_title="Área pendente (ha)",
                    separators=".,",
                )
                st.plotly_chart(
                    aplicar_layout_grafico(fig_idade, 360),
                    use_container_width=True,
                )

            st.divider()
            st.markdown("##### Fila operacional priorizada")
            st.caption(
                "Ordenação por prioridade, tempo desde a solicitação e maior área."
            )

            col_filtro1, col_filtro2 = st.columns([1, 3])
            prioridades_plan = [
                prioridade
                for prioridade in ["Urgente", "Alta", "Média"]
                if prioridade
                in df_backlog.get(
                    "prioridade_amostragem",
                    pd.Series(dtype="object"),
                ).values
            ]
            with col_filtro1:
                prioridade_filtro = st.multiselect(
                    "Prioridade",
                    options=prioridades_plan,
                    default=prioridades_plan,
                    key="planejamento_prioridade",
                )
            with col_filtro2:
                etapa_filtro = st.multiselect(
                    "Etapa atual",
                    options=etapa_ordem,
                    default=etapa_ordem,
                    key="planejamento_etapa",
                )

            df_fila = df_backlog.copy()
            if prioridade_filtro and "prioridade_amostragem" in df_fila.columns:
                df_fila = df_fila[
                    df_fila["prioridade_amostragem"].isin(prioridade_filtro)
                ]
            if etapa_filtro:
                df_fila = df_fila[
                    df_fila["etapa_planejamento"].isin(etapa_filtro)
                ]

            prioridade_ordem = {"Urgente": 0, "Alta": 1, "Média": 2}
            df_fila["ordem_prioridade"] = (
                df_fila.get(
                    "prioridade_amostragem",
                    pd.Series(index=df_fila.index, dtype="object"),
                )
                .map(prioridade_ordem)
                .fillna(99)
            )
            df_fila = df_fila.sort_values(
                ["ordem_prioridade", "idade_dias", "area_ha"],
                ascending=[True, False, False],
            )

            colunas_fila = [
                "prioridade_amostragem",
                "idade_dias",
                "unidade",
                "cod_fazenda",
                "descricao_fazenda",
                "setor",
                "talhao",
                "area_ha",
                "tipo_amostra",
                "classificacao_fazenda",
                "etapa_planejamento",
                "remessa_logistica",
                "data_solicitacao",
            ]
            colunas_fila = [
                coluna for coluna in colunas_fila if coluna in df_fila.columns
            ]
            df_fila_exibicao = df_fila[colunas_fila].rename(
                columns={
                    "prioridade_amostragem": "Prioridade",
                    "idade_dias": "Idade (dias)",
                    "unidade": "Unidade",
                    "cod_fazenda": "Cód. Fazenda",
                    "descricao_fazenda": "Fazenda",
                    "setor": "Setor",
                    "talhao": "Talhão",
                    "area_ha": "Área (ha)",
                    "tipo_amostra": "Tipo",
                    "classificacao_fazenda": "Classificação Fazenda",
                    "etapa_planejamento": "Etapa atual",
                    "remessa_logistica": "Remessa",
                    "data_solicitacao": "Data da solicitação",
                }
            )

            st.dataframe(
                df_fila_exibicao,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Área (ha)": st.column_config.NumberColumn(format="%.2f"),
                    "Idade (dias)": st.column_config.NumberColumn(format="%d"),
                    "Data da solicitação": st.column_config.DateColumn(
                        format="DD/MM/YYYY"
                    ),
                },
            )

            st.caption(
                "Critério: cancelados são excluídos e uma etapa só é considerada "
                "concluída quando sua data de conclusão está preenchida."
            )
# ============================================================
# RODAPÉ
# ============================================================
st.divider()

st.markdown(
    """
    <div style="text-align: center; color: #6B7280; font-size: 14px;">
        © 2026 Agrorobótica - Monitoramento de Entregas ATVOS
    </div>
    """,
    unsafe_allow_html=True,
)
