# Controle de Estoque (Streamlit + Supabase)

## Como rodar

```bash
pip install -r requirements.txt
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_KEY="sua-chave"        # veja "Segurança" abaixo
streamlit run app.py
```

No Colab, defina as variáveis com `os.environ[...]` antes de iniciar, como no app original.
Também funciona com `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "..."
APP_PASSWORD = "senha-de-acesso"   # opcional: ativa a tela de senha
USE_RPC      = "1"                 # opcional: veja sql/01_registrar_movimentacao.sql
```

## Estrutura

```
app.py                 navegação, tela de senha opcional
core/
  tempo.py             fuso America/Fortaleza
  config.py            segredos e constantes
  db.py                Supabase + cache (st.cache_data) + leituras
  services.py          regras: validação, numeração, gravação, rollback
  analytics.py         KPIs, séries e rankings (pandas puro)
  exports.py           Excel e PDF
ui/
  styles.py components.py charts.py compat.py
views/
  dashboard.py movimentacao.py cadastros.py consultas.py
sql/                   índices, restrições e função de gravação atômica (opcionais)
tests/                 python tests/test_core.py
```

## O que mudou em relação ao app original

**Correções**
- Fuso horário: o app usava `datetime.now()` do servidor (UTC no Colab). "Retiradas hoje" e os horários gravados saíam deslocados em 3 h. Agora tudo usa America/Fortaleza.
- Duas linhas do mesmo material passavam na validação individualmente e estouravam o saldo. Agora as quantidades são somadas por material.
- Saldo validado com leitura nova do banco no momento de gravar (não com o valor em tela).
- Gravação em várias tabelas sem proteção: agora há trava otimista no saldo e desfazer automático se algo falhar no meio. Para garantia total, use a função SQL opcional.
- Número da movimentação era gerado a cada clique e podia repetir entre dois usuários. Agora é gerado ao confirmar, com nova tentativa se o banco recusar duplicado.
- "Movimentações / Histórico total" contava no máximo 500 linhas de item. Agora há paginação e os KPIs contam operações distintas.
- "Quantidade em estoque" somava metros, unidades e kg juntos. Foi substituído por indicadores de situação (OK / Baixo / Zerado / Excesso).
- Os `<div class="panel">` abertos e fechados em chamadas separadas de `st.markdown` não envolviam os widgets. Trocados por `st.container(border=True)`.
- Textos vindos do banco entravam no HTML sem escape. Agora são escapados.
- `use_container_width` foi descontinuado (o aviso oficial dizia que seria removido após 31/12/2025). `ui/compat.py` usa `width="stretch"` e cai para a API antiga se necessário.

**Desempenho:** cliente Supabase criado uma vez; listas em cache (60 s); saldos em lote em vez de 2 consultas por item a cada clique; cache limpo a cada escrita.

**Novo**
- Dashboard com período (7/30/90 dias), filtro por destino, variação % contra o período anterior, gráficos Plotly (movimentações por dia, retiradas por destino, materiais mais retirados, situação do estoque, saldo × mínimo) e abas.
- Página **Nova Entrada** (o dashboard já mostrava "Entradas hoje", mas não havia como registrar).
- Exportação: Excel (estoque, movimentações), PDF da posição de estoque e **PDF de comprovante** de cada retirada/entrada.
- Desativar cadastros, checagem de código/TAG/login duplicado, mensagem de sucesso que não some após o `st.rerun()`.

## Segurança — leia

1. **Chave do Supabase.** Se `SUPABASE_KEY` for a `service_role`, quem tiver acesso ao app (ou ao ambiente) tem controle total do banco. Prefira a chave `anon`/publishable com Row Level Security (ver `sql/02_integridade_e_desempenho.sql`).
2. **`APP_PASSWORD`** é uma senha única compartilhada: barra o acesso casual pelo link, mas não identifica quem fez cada operação. O campo "Retirado por" continua sendo escolhido na tela. Autenticação por usuário é um próximo passo.

## Pontos que dependem do seu banco

- **Entrada** grava `destino_id` e `aprovado_por_id` como nulos. Se essas colunas forem NOT NULL, o registro falha com mensagem de erro e **nada fica gravado** (há desfazer). Nesse caso, torne-as opcionais.
- Datas sem fuso (`timestamp`) são interpretadas como horário local. Registros antigos gravados pelo app original em servidor UTC podem aparecer 3 h adiantados.
