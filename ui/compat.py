"""Compatibilidade entre versões do Streamlit.

`use_container_width=True` foi descontinuado em favor de `width="stretch"`
(o aviso oficial dizia que seria removido depois de 31/12/2025). Estes
wrappers tentam a API nova e, se a versão instalada não a conhecer, caem
para a antiga. Assim o app roda em versões antigas e recentes.
"""
from __future__ import annotations

import streamlit as st

_usa_width: bool | None = None  # None = ainda não descoberto


def _largura_total(fn, *args, **kwargs):
    global _usa_width
    if _usa_width is not False:
        try:
            resultado = fn(*args, width="stretch", **kwargs)
            _usa_width = True
            return resultado
        except Exception as e:  # versão antiga rejeita width="stretch"
            if _usa_width is True or "width" not in str(e).lower():
                raise
            _usa_width = False
    return fn(*args, use_container_width=True, **kwargs)


def tabela(df, **kw):
    return _largura_total(st.dataframe, df, hide_index=kw.pop("hide_index", True), **kw)


def grafico(fig, **kw):
    kw.setdefault("config", {"displayModeBar": False})
    return _largura_total(st.plotly_chart, fig, **kw)


def botao(rotulo, **kw):
    return _largura_total(st.button, rotulo, **kw)


def botao_form(rotulo, **kw):
    return _largura_total(st.form_submit_button, rotulo, **kw)


def baixar(rotulo, dados, nome, mime, **kw):
    return _largura_total(st.download_button, rotulo, data=dados, file_name=nome, mime=mime, **kw)
