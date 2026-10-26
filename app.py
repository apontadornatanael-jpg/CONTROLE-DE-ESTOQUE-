"""Controle de Estoque — ponto de entrada.

Execute com:  streamlit run app.py
"""
from __future__ import annotations

import hmac

import streamlit as st

st.set_page_config(
    page_title="Controle de Estoque", page_icon="📦", layout="wide",
    initial_sidebar_state="expanded",
)

from core import db  # noqa: E402
from core.config import segredo  # noqa: E402
from ui import styles  # noqa: E402
from views import cadastros, consultas, dashboard, movimentacao  # noqa: E402

styles.aplicar()

# ---------------------------------------------------------------- configuração
if not db.configurado():
    st.error("Supabase não configurado.")
    st.info(
        "Defina SUPABASE_URL e SUPABASE_KEY como variáveis de ambiente "
        "(ex.: `os.environ[...]` no Colab) ou em `.streamlit/secrets.toml`."
    )
    st.stop()


# ---------------------------------------------------------------- acesso
def _porta_de_acesso() -> None:
    """Senha única opcional. Defina APP_PASSWORD para ativar.

    Protege o app de acesso casual pelo link. Não substitui autenticação
    por usuário (veja a seção de segurança do README).
    """
    senha = segredo("APP_PASSWORD")
    if not senha or st.session_state.get("autenticado"):
        return
    st.markdown('<div class="page-title">🔒 Acesso restrito</div>', unsafe_allow_html=True)
    with st.form("login"):
        digitada = st.text_input("Senha de acesso", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")
    if entrar:
        if hmac.compare_digest(digitada.encode(), str(senha).encode()):
            st.session_state["autenticado"] = True
            st.rerun()
        st.error("Senha incorreta.")
    st.stop()


_porta_de_acesso()

# ---------------------------------------------------------------- navegação
PAGINAS = {
    "📊 Dashboard": lambda nav: dashboard.render(nav),
    "📤 Nova Retirada": lambda nav: movimentacao.render("RETIRADA"),
    "📥 Nova Entrada": lambda nav: movimentacao.render("ENTRADA"),
    "📋 Estoque Atual": lambda nav: consultas.estoque_atual(),
    "🔄 Movimentações": lambda nav: consultas.movimentacoes(),
    "📦 Cadastro de Materiais": lambda nav: cadastros.materiais(),
    "🏗️ Destinos / Sondas": lambda nav: cadastros.destinos(),
    "👥 Usuários": lambda nav: cadastros.usuarios(),
}

st.session_state.setdefault("nav_radio", "📊 Dashboard")


def navegar(destino: str) -> None:
    # roda como callback (antes do próximo render), por isso pode alterar o radio
    st.session_state["nav_radio"] = destino


with st.sidebar:
    st.markdown(
        '<div class="brand"><div style="font-size:34px;line-height:1">📦</div>'
        '<div class="t">CONTROLE DE ESTOQUE</div>'
        '<div class="s">Gestão e rastreabilidade de materiais</div></div>',
        unsafe_allow_html=True,
    )
    pagina = st.radio("NAVEGAÇÃO", list(PAGINAS), key="nav_radio")
    st.divider()
    if st.button("🔄 Recarregar dados", key="side_refresh", help="Limpa o cache e consulta o banco novamente"):
        db.limpar_cache()
        st.rerun()
    st.caption("Sistema independente do DDH")

PAGINAS[pagina](navegar)

st.markdown(
    '<div style="margin-top:35px;padding:15px 4px;border-top:1px solid #e5e7eb;color:#8a94a0;'
    'font-size:11px;text-align:center;">Controle de Estoque • Gestão de materiais e rastreabilidade</div>',
    unsafe_allow_html=True,
)
