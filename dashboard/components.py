import streamlit as st

from dashboard.config import CORES


def aplicar_estilos() -> None:
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


def format_num(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def card_kpi(titulo, valor, detalhe) -> None:
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


def card_kpi_ociosidade(titulo, valor, detalhe) -> None:
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


def renderizar_cabecalho(data_atualizacao) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">Monitoramento de Entregas — ATVOS</div>
            <div class="hero-subtitle">
                Acompanhamento do quantitativo de amostras, status de conclusão e áreas mapeadas |
                Atualizado em {data_atualizacao.strftime("%d/%m/%Y %H:%M")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_rodape() -> None:
    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #6B7280; font-size: 14px;">
            © 2026 Agrorobótica - Monitoramento de Entregas ATVOS
        </div>
        """,
        unsafe_allow_html=True,
    )
