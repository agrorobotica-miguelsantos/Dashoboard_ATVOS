from pathlib import Path

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

PASTA_PEDIDOS = Path("pedidos")
ARQUIVO_SOLICITACOES = Path("atvos_solicitacao2.xlsx")
ARQUIVO_FAZENDAS = Path("fazendas.xlsx")
ARQUIVO_LOGO = Path("logo-agrorobotica-png.png")

COLUNA_REFERENCIA_STATUS = "Ca_(mmolc/dm3)"

COLUNAS_DATAS_SOLICITACAO = [
    "data_inicio_amostragem",
    "data_conclusao_amostragem",
    "data_inicio_logistica",
    "data_conclusao_logistica",
    "data_inicio_analise",
    "data_conclusao_analise",
    "data_inicio_laudo",
    "data_conclusao_laudo",
]

CHAVES_INTEGRACAO = [
    "_chave_remessa",
    "_chave_fazenda",
    "_chave_talhao",
    "_chave_tipo",
]
