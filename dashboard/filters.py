from dataclasses import dataclass
import re

import pandas as pd
import streamlit as st

from dashboard.config import ARQUIVO_LOGO


@dataclass(frozen=True)
class FiltrosDashboard:
    df_filtrado: pd.DataFrame
    busca_fazenda: str
    anos_disponiveis: list
    ano_select: list
    tipos_disponiveis: list
    tipo_select: list
    remessas_disponiveis: list
    remessa_select: list
    unidades_disponiveis: list
    unidade_select: list


def _opcoes_ordenadas(df: pd.DataFrame, coluna: str) -> list:
    if coluna not in df.columns:
        return []
    return sorted(df[coluna].dropna().unique())


def renderizar_sidebar(df_bruto: pd.DataFrame) -> FiltrosDashboard:
    with st.sidebar:
        if ARQUIVO_LOGO.exists():
            st.image(str(ARQUIVO_LOGO), width=250)

        st.caption("Filtros gerais")

        if st.button("🔄 Atualizar Dados", width="stretch"):
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
                re.escape(termo.strip().lower())
                for termo in re.split(r"[,;\s]+", busca_fazenda)
                if termo.strip()
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

        anos_disponiveis = _opcoes_ordenadas(df_filtrado, "Ano")
        ano_select = st.multiselect(
            "Ano",
            options=anos_disponiveis,
            default=anos_disponiveis,
        )
        if ano_select:
            df_filtrado = df_filtrado[df_filtrado["Ano"].isin(ano_select)]

        tipos_disponiveis = _opcoes_ordenadas(df_filtrado, "Tipo") or ["Geral"]
        tipo_select = st.multiselect(
            "Tipo de Análise",
            options=tipos_disponiveis,
            default=tipos_disponiveis,
        )
        if tipo_select:
            df_filtrado = df_filtrado[df_filtrado["Tipo"].isin(tipo_select)]

        remessas_disponiveis = _opcoes_ordenadas(df_filtrado, "Remessa")
        remessa_select = st.multiselect(
            "Remessas",
            options=remessas_disponiveis,
            default=remessas_disponiveis,
        )
        if remessa_select:
            df_filtrado = df_filtrado[df_filtrado["Remessa"].isin(remessa_select)]

        unidades_disponiveis = _opcoes_ordenadas(df_filtrado, "Unidade")
        unidade_select = st.multiselect(
            "Unidades",
            options=unidades_disponiveis,
            default=unidades_disponiveis,
        )
        if unidade_select:
            df_filtrado = df_filtrado[df_filtrado["Unidade"].isin(unidade_select)]

    return FiltrosDashboard(
        df_filtrado=df_filtrado,
        busca_fazenda=busca_fazenda,
        anos_disponiveis=anos_disponiveis,
        ano_select=ano_select,
        tipos_disponiveis=tipos_disponiveis,
        tipo_select=tipo_select,
        remessas_disponiveis=remessas_disponiveis,
        remessa_select=remessa_select,
        unidades_disponiveis=unidades_disponiveis,
        unidade_select=unidade_select,
    )
