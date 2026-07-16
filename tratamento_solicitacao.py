# %%

import pandas as pd
import numpy as np

# %%

atvos = pd.read_excel("atvos_solicitacao.xlsx")
atvos

# %%

colunas = [
    "data_solicitacao",
    "unidade",
    "status",
    "situacao",
    "data_fechamento",
    "data_plantio",
    "classificacao_fazenda",
    "tipo_amostra",
    "modulo_pav",
    "cod_unificado",
    "cod_fazenda",
    "descricao_fazenda",
    "setor",
    "talhao",
    "area_ha",
    "solicitante",
    "prioridade_amostragem",
    "anexos",
    "status_geral",
    "observacao",
    "status_amostragem",
    "data_inicio_amostragem",
    "data_conclusao_amostragem",
    "restricao_amostragem",
    "data_inicio_logistica",
    "data_conclusao_logistica",
    "remessa_logistica",
    "status_analise",
    "data_inicio_analise",
    "data_conclusao_analise",
    "plataforma_cliente",
    "acesso_resultados",
    "coletor",
    "fechamento",
    "observacao_unidade",
    "pontos"
]

atvos.columns = colunas