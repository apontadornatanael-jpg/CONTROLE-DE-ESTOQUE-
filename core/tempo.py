"""Fuso horário e utilitários de data (sem dependência do Streamlit)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

# O servidor (Colab, Streamlit Cloud) normalmente roda em UTC.
# Tudo que o usuário vê ou grava deve usar o horário local.
TZ = ZoneInfo("America/Fortaleza")


def agora() -> datetime:
    """Data/hora atual no fuso local, com timezone."""
    return datetime.now(TZ)
