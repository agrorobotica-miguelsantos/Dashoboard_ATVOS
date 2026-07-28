import re

import pandas as pd
import streamlit as st

from dashboard.config import (
    ARQUIVO_FAZENDAS,
    ARQUIVO_SOLICITACOES,
    CHAVES_INTEGRACAO,
    COLUNA_REFERENCIA_STATUS,
    COLUNAS_DATAS_SOLICITACAO,
    PASTA_PEDIDOS,
)

PADRAO_PEDIDO = re.compile(
    r"^(?P<prefixo>F|PAV)(?P<ano>\d{4})(?P<remessa>\d{3})S$",
    flags=re.IGNORECASE,
)


@st.cache_data(ttl=3600, show_spinner="Carregando planilhas do OneDrive...")
def carregar_dados_locais() -> pd.DataFrame:
    if not PASTA_PEDIDOS.exists():
        return pd.DataFrame()

    lista_combinada = []

    for planilha in sorted(PASTA_PEDIDOS.rglob("*.xlsx")):
        match = PADRAO_PEDIDO.fullmatch(planilha.stem)
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
                f"O arquivo {planilha.name} está aberto ou bloqueado. "
                "Feche o arquivo e atualize os dados"
            )
        except Exception as erro:
            st.error(f"Erro ao ler a planilha {planilha.name}: {erro}")

    if not lista_combinada:
        return pd.DataFrame()

    return pd.concat(lista_combinada, ignore_index=True)


@st.cache_data(ttl=3600, show_spinner="Carregando Dados de Área e Solicitações...")
def carregar_solicitacao() -> pd.DataFrame:
    if not ARQUIVO_SOLICITACOES.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(ARQUIVO_SOLICITACOES, sheet_name="tratado")
        df.columns = df.columns.astype(str).str.strip()

        if "remessa_logistica" in df.columns:
            df["remessa_logistica"] = (
                pd.to_numeric(df["remessa_logistica"], errors="coerce")
                .fillna(-1)
                .astype(int)
                .astype(str)
                .replace("-1", "")
            )

        if "unidade" in df.columns:
            df["unidade"] = df["unidade"].astype(str).str.strip()

        for coluna in COLUNAS_DATAS_SOLICITACAO:
            if coluna in df.columns:
                df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

        return df
    except Exception as erro:
        st.error(f"Erro ao carregar solicitações: {erro}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_fazendas() -> pd.DataFrame:
    df_fazendas = pd.read_excel(ARQUIVO_FAZENDAS)
    df_fazendas.columns = df_fazendas.columns.astype(str).str.strip()
    df_fazendas["Nome_Fazenda"] = df_fazendas["Nome_Fazenda"].astype(str).str.strip()
    df_fazendas["Cod_Fazenda"] = pd.to_numeric(
        df_fazendas["Cod_Fazenda"], errors="coerce"
    ).astype("Int64")
    return df_fazendas.drop_duplicates(subset=["Cod_Fazenda", "Nome_Fazenda"])


def preparar_base_principal(df_bruto: pd.DataFrame) -> pd.DataFrame:
    df_fazendas = carregar_fazendas()
    df_preparado = df_bruto.merge(
        df_fazendas,
        how="inner",
        left_on="Fazenda",
        right_on="Cod_Fazenda",
        validate="many_to_many",
    )
    df_preparado["Nome_Fazenda"] = df_preparado["Nome_Fazenda"].astype(str).str.strip()

    if COLUNA_REFERENCIA_STATUS not in df_preparado.columns:
        raise KeyError(COLUNA_REFERENCIA_STATUS)

    df_preparado["Status"] = df_preparado[COLUNA_REFERENCIA_STATUS].apply(
        lambda valor: "Concluído" if pd.notna(valor) else "Pendente"
    )
    return df_preparado


def _normalizar_inteiro(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


def _normalizar_texto(serie: pd.Series) -> pd.Series:
    normalizada = serie.astype("string").str.strip().str.lower()
    return normalizada.replace("", pd.NA)


def _adicionar_chaves(
    df: pd.DataFrame,
    *,
    coluna_remessa: str,
    coluna_fazenda: str,
    coluna_talhao: str,
    coluna_tipo: str,
) -> pd.DataFrame:
    resultado = df.copy()
    resultado["_chave_remessa"] = _normalizar_inteiro(resultado[coluna_remessa])
    resultado["_chave_fazenda"] = _normalizar_inteiro(resultado[coluna_fazenda])
    resultado["_chave_talhao"] = _normalizar_inteiro(resultado[coluna_talhao])
    resultado["_chave_tipo"] = _normalizar_texto(resultado[coluna_tipo])
    return resultado


def _juntar_valores_unicos(serie: pd.Series):
    valores = serie.dropna().astype(str).str.strip()
    valores = valores[valores.ne("")]
    if valores.empty:
        return pd.NA
    return " | ".join(dict.fromkeys(valores))


def _agregacao_para_coluna(coluna: str, serie: pd.Series):
    if coluna == "area_ha":
        return lambda valores: valores.sum(min_count=1)
    if coluna.startswith("data_inicio"):
        return "min"
    if coluna.startswith("data_conclusao"):
        return "max"
    if pd.api.types.is_numeric_dtype(serie):
        return "first"
    return _juntar_valores_unicos


def consolidar_solicitacoes(df_solicitacao: pd.DataFrame) -> pd.DataFrame:
    if df_solicitacao.empty:
        return pd.DataFrame(columns=CHAVES_INTEGRACAO)

    obrigatorias = {
        "remessa_logistica",
        "cod_fazenda",
        "talhao",
        "tipo_amostra",
    }
    ausentes = obrigatorias.difference(df_solicitacao.columns)
    if ausentes:
        raise KeyError(", ".join(sorted(ausentes)))

    solicitacoes = _adicionar_chaves(
        df_solicitacao,
        coluna_remessa="remessa_logistica",
        coluna_fazenda="cod_fazenda",
        coluna_talhao="talhao",
        coluna_tipo="tipo_amostra",
    ).dropna(subset=CHAVES_INTEGRACAO)

    colunas_dados = [
        coluna for coluna in solicitacoes.columns if coluna not in CHAVES_INTEGRACAO
    ]
    agregacoes = {
        coluna: _agregacao_para_coluna(coluna, solicitacoes[coluna])
        for coluna in colunas_dados
    }

    consolidado = solicitacoes.groupby(CHAVES_INTEGRACAO, as_index=False).agg(
        **{
            f"Solicitacao_{coluna}": pd.NamedAgg(
                column=coluna,
                aggfunc=agregacao,
            )
            for coluna, agregacao in agregacoes.items()
        }
    )

    quantidades = (
        solicitacoes.groupby(CHAVES_INTEGRACAO, as_index=False)
        .size()
        .rename(columns={"size": "Solicitacoes_Qtd"})
    )
    return consolidado.merge(
        quantidades,
        on=CHAVES_INTEGRACAO,
        how="left",
        validate="one_to_one",
    )


def integrar_bases(
    df_bruto: pd.DataFrame,
    df_solicitacao: pd.DataFrame,
) -> pd.DataFrame:
    if df_solicitacao.empty:
        resultado = df_bruto.copy()
        resultado["Solicitacoes_Qtd"] = 0
        resultado["Solicitacao_Encontrada"] = False
        return resultado

    talhao_bruto = next(
        (coluna for coluna in df_bruto.columns if coluna.casefold() == "talhão"),
        None,
    )
    if talhao_bruto is None:
        raise KeyError("Talhão")

    bruto_com_chaves = _adicionar_chaves(
        df_bruto,
        coluna_remessa="Remessa",
        coluna_fazenda="Fazenda",
        coluna_talhao=talhao_bruto,
        coluna_tipo="Tipo",
    )
    solicitacoes_consolidadas = consolidar_solicitacoes(df_solicitacao)

    integrado = bruto_com_chaves.merge(
        solicitacoes_consolidadas,
        on=CHAVES_INTEGRACAO,
        how="left",
        validate="many_to_one",
    )
    integrado["Solicitacoes_Qtd"] = integrado["Solicitacoes_Qtd"].fillna(0).astype(int)
    integrado["Solicitacao_Encontrada"] = integrado["Solicitacoes_Qtd"].gt(0)
    return integrado.drop(columns=CHAVES_INTEGRACAO)
