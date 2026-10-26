"""Acesso ao Supabase com cache.

Cada interação do usuário reexecuta o script inteiro no Streamlit. Sem
cache, o app original fazia dezenas de consultas por clique. Aqui:
- o cliente é criado uma única vez (cache_resource);
- listas e consultas pesadas usam cache_data com TTL curto;
- qualquer escrita chama limpar_cache();
- a validação de saldo no momento de gravar usa leitura FRESCA (sem cache).
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from core import analytics
from core.config import TTL_PADRAO, segredo
from core.services import ler_saldos
from core.tempo import agora

LIMITE_LINHAS = 20000
BLOCO_IDS = 100


def configurado() -> bool:
    return bool(segredo("SUPABASE_URL") and segredo("SUPABASE_KEY"))


@st.cache_resource(show_spinner=False)
def get_client():
    from supabase import create_client

    return create_client(segredo("SUPABASE_URL"), segredo("SUPABASE_KEY"))


def limpar_cache() -> None:
    st.cache_data.clear()


def _seguro(fn, rotulo: str, vazio):
    """Executa a consulta; em erro mostra aviso e devolve `vazio`.

    O erro acontece fora da função cacheada, então um problema temporário
    não fica 'preso' no cache.
    """
    try:
        return fn()
    except Exception as e:
        st.error(f"Erro ao carregar {rotulo}: {e}")
        return vazio


def _paginar(consulta, tamanho: int = 1000) -> list[dict]:
    """O Supabase devolve no máximo 1000 linhas por chamada."""
    linhas: list[dict] = []
    inicio = 0
    while inicio < LIMITE_LINHAS:
        bloco = consulta(inicio, inicio + tamanho - 1).data or []
        linhas.extend(bloco)
        if len(bloco) < tamanho:
            break
        inicio += tamanho
    return linhas


# ----------------------------------------------------------------------
# Consultas em cache (levantam exceção em caso de erro)
# ----------------------------------------------------------------------
@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def _destinos(somente_ativos: bool = True):
    q = get_client().table("estoque_destinos").select("*")
    if somente_ativos:
        q = q.eq("ativo", True)
    return q.order("tag").execute().data or []


@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def _unidades():
    return (
        get_client().table("estoque_unidades").select("*")
        .eq("ativo", True).order("sigla").execute().data or []
    )


@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def _materiais(somente_ativos: bool = True):
    q = get_client().table("estoque_materiais").select(
        "*, estoque_unidades (id, sigla, descricao)"
    )
    if somente_ativos:
        q = q.eq("ativo", True)
    return q.order("descricao").execute().data or []


@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def _usuarios():
    return (
        get_client().table("estoque_usuarios").select("*")
        .eq("ativo", True).order("nome").execute().data or []
    )


@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def _estoque():
    return get_client().table("v_estoque_atual").select("*").order("descricao").execute().data or []


@st.cache_data(ttl=30, show_spinner=False)
def _saldos():
    linhas = _paginar(
        lambda a, b: get_client().table("estoque_saldos")
        .select("material_id, quantidade").range(a, b).execute()
    )
    return {r["material_id"]: float(r["quantidade"] or 0) for r in linhas}


@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def _movimentos_brutos(dias: int):
    client = get_client()
    inicio = (agora() - timedelta(days=dias)).replace(hour=0, minute=0, second=0, microsecond=0)
    cabecalhos = _paginar(
        lambda a, b: client.table("estoque_movimentacoes").select("*")
        .gte("data_hora", inicio.isoformat())
        .order("data_hora", desc=True).range(a, b).execute()
    )
    ids = [c["id"] for c in cabecalhos]
    itens: list[dict] = []
    for i in range(0, len(ids), BLOCO_IDS):
        parte = ids[i : i + BLOCO_IDS]
        itens.extend(
            _paginar(
                lambda a, b, parte=parte: client.table("estoque_movimentacao_itens")
                .select("movimentacao_id, material_id, quantidade, numero_serie")
                .in_("movimentacao_id", parte).range(a, b).execute()
            )
        )
    return cabecalhos, itens


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------
def listar_destinos():
    return _seguro(_destinos, "destinos", [])


def listar_unidades():
    return _seguro(_unidades, "unidades", [])


def listar_materiais():
    return _seguro(_materiais, "materiais", [])


def listar_usuarios():
    return _seguro(_usuarios, "usuários", [])


def listar_estoque():
    return _seguro(_estoque, "estoque", [])


def listar_saldos() -> dict:
    return _seguro(_saldos, "saldos", {})


def carregar_movimentos(dias: int) -> pd.DataFrame:
    """Movimentos dos últimos `dias` dias, um registro por item."""

    def _carregar():
        cabecalhos, itens = _movimentos_brutos(dias)
        # histórico usa catálogo completo (inclui materiais/destinos inativos)
        return analytics.montar_movimentos(
            cabecalhos, itens, _materiais(False), _destinos(False)
        )

    return _seguro(_carregar, "movimentações", analytics.montar_movimentos([], [], [], []))


def saldos_frescos(material_ids) -> dict:
    """Saldos sem cache, para validar no momento de gravar."""
    return ler_saldos(get_client(), material_ids)


# ----------------------------------------------------------------------
# Escrita simples (cadastros)
# ----------------------------------------------------------------------
def inserir(tabela: str, dados: dict) -> list[dict]:
    r = get_client().table(tabela).insert(dados).execute()
    limpar_cache()
    return r.data or []


def desativar(tabela: str, registro_id) -> None:
    get_client().table(tabela).update({"ativo": False}).eq("id", registro_id).execute()
    limpar_cache()
