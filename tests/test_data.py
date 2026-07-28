import pandas as pd

from dashboard.data import integrar_bases


def test_integrar_bases_preserva_linhas_e_consolida_duplicidades():
    df_bruto = pd.DataFrame(
        {
            "Remessa": ["001", "001"],
            "Fazenda": [420136, 420136],
            "Talhão": [1, 1],
            "Tipo": ["Fertilidade", "Fertilidade"],
            "Ponto": [1, 2],
        }
    )
    df_solicitacao = pd.DataFrame(
        {
            "remessa_logistica": ["1", "1"],
            "cod_fazenda": [420136, 420136],
            "talhao": [1.0, 1.0],
            "tipo_amostra": ["Fertilidade", "Fertilidade"],
            "area_ha": [5.0, 7.0],
            "status_amostragem": ["Iniciado", "Concluído"],
        }
    )

    integrado = integrar_bases(df_bruto, df_solicitacao)

    assert len(integrado) == len(df_bruto)
    assert integrado["Solicitacao_Encontrada"].all()
    assert integrado["Solicitacoes_Qtd"].eq(2).all()
    assert integrado["Solicitacao_area_ha"].eq(12.0).all()


def test_integrar_bases_vazias_mantem_base_principal():
    df_bruto = pd.DataFrame(
        {
            "Remessa": ["001"],
            "Fazenda": [420136],
            "Talhão": [1],
            "Tipo": ["Fertilidade"],
        }
    )

    integrado = integrar_bases(df_bruto, pd.DataFrame())

    assert len(integrado) == len(df_bruto)
    assert integrado["Solicitacoes_Qtd"].eq(0).all()
    assert not integrado["Solicitacao_Encontrada"].any()
