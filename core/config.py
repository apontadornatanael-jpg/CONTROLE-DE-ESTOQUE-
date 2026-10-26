"""Configuração: segredos e constantes."""
from __future__ import annotations

import os

import streamlit as st

from core.tempo import TZ, agora  # noqa: F401  (reexportado)

TTL_PADRAO = 60  # segundos de cache para listas/consultas

TIPOS_MOVIMENTACAO = ("RETIRADA", "ENTRADA")
PERFIS_APROVADORES = ("ADMIN", "GESTOR", "APROVADOR")


def segredo(nome: str, padrao=None):
    """Lê de variável de ambiente ou de st.secrets (secrets.toml)."""
    valor = os.getenv(nome)
    if valor:
        return valor
    try:
        return st.secrets.get(nome, padrao)
    except Exception:
        return padrao
