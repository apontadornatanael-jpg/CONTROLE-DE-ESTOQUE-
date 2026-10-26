"""Regras de negócio para registrar entradas e retiradas.

Não importa o Streamlit: recebe o cliente Supabase por parâmetro, o que
permite testar com um cliente simulado.

Dois caminhos de gravação:
1. RPC atômica (função SQL `fn_registrar_movimentacao`) - tudo ou nada.
   Ativada com USE_RPC=1 depois de executar sql/01_registrar_movimentacao.sql.
2. Sequencial com desfazer (padrão) - mesmo comportamento do app original,
   porém com trava otimista no saldo e rollback best-effort em caso de falha.
"""
from __future__ import annotations

from datetime import date, datetime

from core.tempo import agora


class ErroNegocio(Exception):
    """Erro com mensagem apropriada para mostrar ao usuário."""


# ----------------------------------------------------------------------
# Validação
# ----------------------------------------------------------------------
def validar_movimentacao(tipo: str, itens: list[dict], saldos: dict) -> list[str]:
    """Valida a movimentação. `saldos` deve ser lido NO MOMENTO do registro.

    Soma as quantidades por material: duas linhas do mesmo material não
    podem, juntas, passar do saldo (falha do app original).
    """
    erros: list[str] = []
    if not itens:
        return ["Adicione pelo menos um item."]

    totais: dict = {}
    for i, it in enumerate(itens, start=1):
        m = it["material"]
        nome = m.get("descricao", "material")
        if it["quantidade"] <= 0:
            erros.append(f"Item {i} ({nome}): informe uma quantidade maior que zero.")
        if m.get("controla_numero_serie") and not it.get("numero_serie"):
            erros.append(f"Item {i} ({nome}): informe o número de série.")
        if tipo == "RETIRADA" and m.get("exige_foto") and not it.get("foto"):
            erros.append(f"Item {i} ({nome}): a fotografia é obrigatória.")
        entrada = totais.setdefault(m["id"], [m, 0.0])
        entrada[1] += it["quantidade"]

    if tipo == "RETIRADA":
        for mid, (m, total) in totais.items():
            saldo = float(saldos.get(mid, 0.0))
            if total > saldo + 1e-9:
                erros.append(
                    f"Estoque insuficiente para {m.get('descricao')}: "
                    f"solicitado {total:g}, disponível {saldo:g}."
                )
    return erros


# ----------------------------------------------------------------------
# Numeração
# ----------------------------------------------------------------------
def proximo_numero(client, dia: date) -> str:
    prefixo = f"MOV-{dia.strftime('%Y%m%d')}"
    r = (
        client.table("estoque_movimentacoes")
        .select("numero_movimentacao")
        .like("numero_movimentacao", f"{prefixo}-%")
        .order("numero_movimentacao", desc=True)
        .limit(1)
        .execute()
    )
    ultimo = 0
    if r.data:
        try:
            ultimo = int(str(r.data[0]["numero_movimentacao"]).split("-")[-1])
        except ValueError:
            ultimo = 0
    return f"{prefixo}-{ultimo + 1:03d}"


def _eh_duplicado(e: Exception) -> bool:
    t = str(e).lower()
    return "23505" in t or "duplicate" in t or "unique" in t


# ----------------------------------------------------------------------
# Saldos
# ----------------------------------------------------------------------
def ler_saldos(client, material_ids) -> dict:
    ids = list({i for i in material_ids if i is not None})
    if not ids:
        return {}
    r = (
        client.table("estoque_saldos")
        .select("material_id, quantidade")
        .in_("material_id", ids)
        .execute()
    )
    return {row["material_id"]: float(row["quantidade"] or 0) for row in (r.data or [])}


def _aplicar_saldo(client, material_id, delta: float, tentativas: int = 3):
    """Soma `delta` ao saldo com trava otimista (compare-and-set).

    Retorna (saldo_anterior, saldo_posterior).
    """
    for _ in range(tentativas):
        r = (
            client.table("estoque_saldos")
            .select("quantidade")
            .eq("material_id", material_id)
            .limit(1)
            .execute()
        )
        if not r.data:
            if delta < 0:
                raise ErroNegocio("Estoque insuficiente: material sem saldo registrado.")
            client.table("estoque_saldos").insert(
                {"material_id": material_id, "quantidade": delta}
            ).execute()
            return 0.0, float(delta)

        bruto = r.data[0]["quantidade"]
        atual = float(bruto or 0)
        novo = atual + delta
        if novo < -1e-9:
            raise ErroNegocio(f"Estoque insuficiente. Saldo atual: {atual:g}.")
        up = (
            client.table("estoque_saldos")
            .update({"quantidade": novo, "atualizado_em": agora().isoformat()})
            .eq("material_id", material_id)
            .eq("quantidade", bruto)
            .execute()
        )
        if up.data:
            return atual, novo
    raise ErroNegocio(
        "O saldo foi alterado por outra pessoa durante o registro. Tente novamente."
    )


# ----------------------------------------------------------------------
# Gravação sequencial (padrão)
# ----------------------------------------------------------------------
def _inserir_cabecalho(client, cabecalho: dict, tentativas: int = 5):
    ultimo_erro = None
    for _ in range(tentativas):
        numero = proximo_numero(client, cabecalho["_dia"])
        dados = {k: v for k, v in cabecalho.items() if not k.startswith("_")}
        dados["numero_movimentacao"] = numero
        try:
            r = client.table("estoque_movimentacoes").insert(dados).execute()
        except Exception as e:  # numeração concorrente
            if _eh_duplicado(e):
                ultimo_erro = e
                continue
            raise
        if not r.data:
            raise ErroNegocio("Não foi possível criar a movimentação.")
        return numero, r.data[0]["id"]
    raise ErroNegocio(f"Não foi possível gerar um número único de movimentação: {ultimo_erro}")


def _desfazer(client, movimentacao_id, aplicados: list) -> int:
    """Rollback best-effort. Retorna a quantidade de passos que falharam."""
    falhas = 0
    for material_id, delta in reversed(aplicados):
        try:
            _aplicar_saldo(client, material_id, -delta)
        except Exception:
            falhas += 1
    if movimentacao_id is not None:
        for tabela, coluna in (
            ("estoque_historico", "movimentacao_id"),
            ("estoque_divergencias", "movimentacao_id"),
            ("estoque_movimentacao_itens", "movimentacao_id"),
            ("estoque_movimentacoes", "id"),
        ):
            try:
                client.table(tabela).delete().eq(coluna, movimentacao_id).execute()
            except Exception:
                falhas += 1
    return falhas


def _registrar_sequencial(client, tipo, cabecalho, itens, divergencia_txt, usuario_id):
    movimentacao_id = None
    aplicados: list = []
    item_ids: list = []
    try:
        numero, movimentacao_id = _inserir_cabecalho(client, cabecalho)
        registrado_em = agora().isoformat()
        for it in itens:
            m = it["material"]
            r = (
                client.table("estoque_movimentacao_itens")
                .insert(
                    {
                        "movimentacao_id": movimentacao_id,
                        "material_id": m["id"],
                        "quantidade": it["quantidade"],
                        "unidade_id": m.get("unidade_id"),
                        "numero_serie": it.get("numero_serie") or None,
                        "observacao": it.get("observacao") or None,
                    }
                )
                .execute()
            )
            if not r.data:
                raise ErroNegocio(f"Erro ao gravar o item {m.get('descricao')}.")
            item_ids.append(r.data[0]["id"])

            delta = it["quantidade"] if tipo == "ENTRADA" else -it["quantidade"]
            anterior, posterior = _aplicar_saldo(client, m["id"], delta)
            aplicados.append((m["id"], delta))

            client.table("estoque_historico").insert(
                {
                    "material_id": m["id"],
                    "movimentacao_id": movimentacao_id,
                    "tipo_movimentacao": tipo,
                    "quantidade_anterior": anterior,
                    "quantidade_movimentada": it["quantidade"],
                    "quantidade_posterior": posterior,
                    "registrado_em": registrado_em,
                    "registrado_por_id": usuario_id,
                }
            ).execute()

        if divergencia_txt:
            client.table("estoque_divergencias").insert(
                {
                    "movimentacao_id": movimentacao_id,
                    "descricao": divergencia_txt,
                    "registrada_por_id": usuario_id,
                    "registrada_em": registrado_em,
                    "resolvida": False,
                }
            ).execute()
    except Exception as e:
        falhas = _desfazer(client, movimentacao_id, aplicados)
        msg = str(e) if isinstance(e, ErroNegocio) else f"Falha ao registrar: {e}"
        if falhas:
            msg += (
                f" ATENÇÃO: {falhas} passo(s) da reversão falharam; "
                "confira o saldo e o histórico dos materiais envolvidos."
            )
        else:
            msg += " Nada foi gravado."
        raise ErroNegocio(msg) from e

    return {"id": movimentacao_id, "numero": numero, "item_ids": item_ids}


# ----------------------------------------------------------------------
# RPC atômica (opcional)
# ----------------------------------------------------------------------
def _registrar_rpc(client, tipo, cabecalho, itens, divergencia_txt):
    payload = {
        "tipo": tipo,
        "cabecalho": {k: v for k, v in cabecalho.items() if not k.startswith("_")},
        "itens": [
            {
                "material_id": it["material"]["id"],
                "quantidade": it["quantidade"],
                "unidade_id": it["material"].get("unidade_id"),
                "numero_serie": it.get("numero_serie") or None,
                "observacao": it.get("observacao") or None,
            }
            for it in itens
        ],
        "divergencia": divergencia_txt or "",
    }
    try:
        r = client.rpc("fn_registrar_movimentacao", {"p": payload}).execute()
    except Exception as e:
        texto = str(e)
        if "ESTOQUE_INSUFICIENTE" in texto:
            raise ErroNegocio("Estoque insuficiente para concluir a operação.") from e
        raise ErroNegocio(f"Falha ao registrar (RPC): {texto}") from e
    dados = r.data or {}
    if isinstance(dados, list):
        dados = dados[0] if dados else {}
    if not dados.get("id"):
        raise ErroNegocio("A função de registro não retornou a movimentação criada.")
    return {"id": dados["id"], "numero": dados["numero"], "item_ids": dados.get("item_ids", [])}


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------
def registrar_movimentacao(
    client,
    *,
    tipo: str,
    cabecalho: dict,
    itens: list[dict],
    divergencia_txt: str | None = None,
    usuario_id=None,
    usar_rpc: bool = False,
) -> dict:
    """Registra uma movimentação completa.

    `cabecalho` não deve conter numero_movimentacao (é gerado aqui) e deve
    ter a chave auxiliar `_dia` (date). Retorna {id, numero, item_ids}.
    """
    if tipo not in ("RETIRADA", "ENTRADA"):
        raise ErroNegocio(f"Tipo de movimentação inválido: {tipo}")
    cabecalho = {**cabecalho, "tipo": tipo}
    cabecalho.setdefault("_dia", agora().date())
    if isinstance(cabecalho.get("data_hora"), datetime):
        cabecalho["data_hora"] = cabecalho["data_hora"].isoformat()

    if usar_rpc:
        return _registrar_rpc(client, tipo, cabecalho, itens, divergencia_txt)
    return _registrar_sequencial(client, tipo, cabecalho, itens, divergencia_txt, usuario_id)


def enviar_anexos(client, movimentacao_id, anexos: list[dict], usuario_id) -> list[str]:
    """Envia fotos ao Storage. Falhas viram avisos (a movimentação já existe).

    Cada anexo: {item_id, nome, conteudo(bytes), tipo}.
    """
    avisos: list[str] = []
    for a in anexos:
        caminho = f"{movimentacao_id}/{a['item_id']}_{a['nome']}"
        try:
            client.storage.from_("estoque-anexos").upload(
                caminho, a["conteudo"], {"content-type": a["tipo"]}
            )
            client.table("estoque_anexos").insert(
                {
                    "movimentacao_id": movimentacao_id,
                    "movimentacao_item_id": a["item_id"],
                    "nome_arquivo": a["nome"],
                    "caminho_arquivo": caminho,
                    "tipo_arquivo": a["tipo"],
                    "tamanho_bytes": len(a["conteudo"]),
                    "enviado_por_id": usuario_id,
                }
            ).execute()
        except Exception as e:
            avisos.append(f"Anexo '{a['nome']}' não pôde ser enviado: {e}")
    return avisos


def mensagem_whatsapp(
    *, numero, data_hora, tipo, destino, itens, finalidade,
    responsavel, aprovador=None, emergencial=False,
) -> str:
    titulo = "📤 RETIRADA DE MATERIAL" if tipo == "RETIRADA" else "📥 ENTRADA DE MATERIAL"
    linhas = [
        titulo, "",
        f"Movimentação: {numero}",
        f"Data e hora: {data_hora.strftime('%d/%m/%Y %H:%M')}",
        "",
    ]
    if destino:
        linhas.append(f"Destino: {destino}")
    if emergencial:
        linhas.append("⚠️ RETIRADA EMERGENCIAL")
    linhas += ["", "Item(ns) e quantidade(s):"]
    for i, it in enumerate(itens, start=1):
        linhas.append(f"{i}. {it['descricao']} – {it['quantidade']:g} – {it['unidade']}")
    rotulo_fin = "Finalidade da aplicação" if tipo == "RETIRADA" else "Origem / observação"
    rotulo_resp = "Retirado por" if tipo == "RETIRADA" else "Recebido por"
    linhas += ["", f"{rotulo_fin}: {finalidade}", f"{rotulo_resp}: {responsavel}"]
    if aprovador:
        linhas.append(f"Aprovado por: {aprovador}")
    return "\n".join(linhas)
