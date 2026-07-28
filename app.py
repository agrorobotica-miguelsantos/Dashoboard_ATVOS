# %%
# ============================================================
# PAINEL - ACOMPANHAMENTO DE AMOSTRAGENS | ATVOS
# ============================================================

import datetime as dt
import re
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components import (
    aplicar_estilos,
    aplicar_layout_grafico,
    card_kpi,
    card_kpi_ociosidade,
    format_num,
    renderizar_cabecalho,
    renderizar_rodape,
)
from dashboard.config import COLUNA_REFERENCIA_STATUS, CORES
from dashboard.data import (
    carregar_dados_locais,
    carregar_solicitacao,
    integrar_bases,
    preparar_base_principal,
)
from dashboard.filters import renderizar_sidebar

# ============================================================
# CONFIGURAÇÕES GERAIS E PALETA DE CORES
# ============================================================

st.set_page_config(
    page_title="Monitoramento de Entregas - ATVOS",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ============================================================

aplicar_estilos()

# ============================================================
# PROCESSAMENTO E TRATAMENTO DA BASE PRINCIPAL
# ============================================================

df_bruto = carregar_dados_locais()
df_solicitacao = carregar_solicitacao()

if df_bruto.empty:
    st.error("Nenhum dado bruto pôde ser carregado da pasta `pedidos`.")
    st.stop()

if COLUNA_REFERENCIA_STATUS not in df_bruto.columns:
    st.error(
        f"A coluna de referência '{COLUNA_REFERENCIA_STATUS}' não foi encontrada "
        "nos dados carregados."
    )
    st.stop()

try:
    df_bruto = preparar_base_principal(df_bruto)
    df_bruto = integrar_bases(df_bruto, df_solicitacao)
except KeyError as erro:
    st.error(f"Não foi possível integrar as bases. Coluna ausente: {erro.args[0]}")
    st.stop()


# ============================================================
# SIDEBAR (FILTROS GLOBAIS)
# ============================================================

filtros = renderizar_sidebar(df_bruto)
df_filtrado = filtros.df_filtrado
busca_fazenda = filtros.busca_fazenda
tipos_disponiveis = filtros.tipos_disponiveis
tipo_select = filtros.tipo_select
remessas_disponiveis = filtros.remessas_disponiveis
remessa_select = filtros.remessa_select
unidades_disponiveis = filtros.unidades_disponiveis
unidade_select = filtros.unidade_select


# ============================================================
# HEADER PRINCIPAL (HERO BANNER)
# ============================================================

hora_brasilia = dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
renderizar_cabecalho(hora_brasilia)


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

            fig_remessa = px.bar(
                df_graf_remessa,
                x="Remessa",
                y="Quantidade",
                color="Status",
                facet_row="Tipo",
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

            st.plotly_chart(aplicar_layout_grafico(fig_remessa, 420), width="stretch")

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
            st.plotly_chart(aplicar_layout_grafico(fig_unidade, 420), width="stretch")

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
                            width="stretch",
                        )

        # ============================================================
        # DRILL-DOWN Fazenda-Talhão
        # ============================================================
        st.divider()
        st.markdown("### Detalhamento por Talhão")
        st.caption(
            "Insira o código de uma fazenda para investigar o status e os dados de área ao nível de talhão."
        )

        codigo_padrao = ""
        if busca_fazenda:
            termos_busca = [
                t.strip() for t in re.split(r"[,;\s]+", busca_fazenda) if t.strip()
            ]
            if termos_busca:
                codigo_padrao = termos_busca[0]

        fzd_codigo_input = st.text_input(
            "Digite o Código da Fazenda:",
            value=codigo_padrao,
            placeholder="Ex: 420136",
            help="Digite o código numérico da fazenda para listar seus talhões",
            key="txt_talhao_drilldown",
        )

        if fzd_codigo_input:
            df_talhao_fzd = df_filtrado[
                df_filtrado[col_cod_fazenda].astype(str) == fzd_codigo_input.strip()
            ]

            if not df_talhao_fzd.empty:
                nome_fzd_encontrado = df_talhao_fzd[col_nome_fazenda].iloc[0]
                unidade_fzd = df_talhao_fzd["Unidade"].iloc[0]

                st.markdown(
                    f"**Fazenda Localizada:** `{fzd_codigo_input}` - **{nome_fzd_encontrado}** (Unidade: **{unidade_fzd}**)"
                )

                cols_agrup_talhao = []
                cols_config = {}

                if "Talhão" in df_talhao_fzd.columns:
                    cols_agrup_talhao.append("Talhão")
                    cols_config["Talhão"] = st.column_config.TextColumn("Talhão")
                if "Tipo" in df_talhao_fzd.columns:
                    cols_agrup_talhao.append("Tipo")
                    cols_config["Tipo"] = st.column_config.TextColumn("Tipo")
                if "Status" in df_talhao_fzd.columns:
                    cols_agrup_talhao.append("Status")
                    cols_config["Status"] = st.column_config.TextColumn("Status")

                if "Talhão" in df_talhao_fzd.columns:
                    df_detalhe_talhao = (
                        df_talhao_fzd[cols_agrup_talhao]
                        .drop_duplicates()
                        .sort_values(by="Talhão")
                    )
                    st.dataframe(
                        df_detalhe_talhao,
                        column_config=cols_config,
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.warning(
                        "A coluna de detalhe 'Talhão' não foi encontrada no arquivo carregado."
                    )
            else:
                st.error(
                    f"Nenhuma fazenda encontrada com o código `{fzd_codigo_input}` nos filtros atuais."
                )
        else:
            st.info(
                "Digite o código de uma fazenda acima (ou utilize o filtro da barra lateral) para carregar os talhões."
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

                st.plotly_chart(aplicar_layout_grafico(fig_evo, 450), width="stretch")

        else:
            st.warning(
                "A coluna de área ('area_ha') não foi encontrada no arquivo de solicitações."
            )

with tab_planejamento:
    st.title("Página em construção")
# ============================================================
# RODAPÉ
# ============================================================
renderizar_rodape()
