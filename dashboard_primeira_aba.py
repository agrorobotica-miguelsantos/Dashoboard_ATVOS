# %%
# ============================================================
# PAINEL - QUANTITATIVO E STATUS | ATVOS
# ============================================================

#
# Versão independente contendo somente a primeira aba do dashboard original.
import datetime as dt
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
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
    r"^(?P<prefixo>F|PAV)(?P<ano>\d{4})(?P<remessa>\d{3})S$", flags=re.IGNORECASE
)


@st.cache_data(ttl=3600, show_spinner="Carregando planilhas do OneDrive...")
def carregar_dados_locais():
    entrada = Path("pedidos")

    if not entrada.exists():
        return pd.DataFrame()

    planilhas = sorted(entrada.rglob("*.xlsx"))
    lista_combinada = []

    for planilha in planilhas:
        match = padrao_pedido.fullmatch(planilha.stem)

        if not match:
            continue

        prefixo = match.group("prefixo").upper()
        ano = match.group("ano")
        remessa = match.group("remessa")
        tipo = "Fertilidade" if prefixo == "F" else "PAV"

        try:
            df_temp = pd.read_excel(planilha)
            df_temp.columns = df_temp.columns.astype(str).str.strip()

            df_temp.insert(0, "Remessa", remessa)
            df_temp.insert(1, "Ano", ano)
            df_temp.insert(2, "Tipo", tipo)
            df_temp.insert(3, "Arquivo_Origem", planilha.name)

            lista_combinada.append(df_temp)

        except PermissionError:
            st.error(
                f"O arquivo {planilha.name} está aberto ou bloqueado. Feche o arquivo e atualize os dados"
            )

        except Exception as e:
            st.error(f"Erro ao ler a planilha {planilha.name}: {e}")

    if not lista_combinada:
        return pd.DataFrame()

    return pd.concat(lista_combinada, ignore_index=True)




# ============================================================
# PROCESSAMENTO E TRATAMENTO DA BASE PRINCIPAL
# ============================================================

df_bruto = carregar_dados_locais()

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

        fig_remessa = px.bar(
            df_graf_remessa,
            x="Remessa",
            y="Quantidade",
            color="Status",
            facet_row="Tipo",
            category_orders={"Tipo": ["Fertilidade", "PAV"]},
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

        tipos_ativos = df_graf_remessa["Tipo"].unique()
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
