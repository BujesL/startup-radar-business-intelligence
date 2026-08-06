"""
Etapa 7 — Geração de insight via IA (Claude API).

Princípio de design não-negociável: a IA NUNCA recebe uma pergunta aberta
sobre o dataset. Ela recebe um JSON fechado com os números já agregados pelo
Postgres (top CNAEs por variação percentual na RMPA) e sua única tarefa é
transformar esse JSON em 2-3 frases em português natural. O mesmo JSON é
salvo em `insights_ia.baseado_em`, então qualquer afirmação do texto pode ser
auditada contra o número exato que a originou — elimina o risco de
alucinação numérica.

Roda em batch (cron/manual), nunca de forma síncrona a uma requisição do
dashboard — a latência de uma chamada de LLM não deve bloquear a experiência
do usuário.

Uso:
    python 7_generate_insight.py
"""
from __future__ import annotations

import json

import anthropic

from config import ANTHROPIC_API_KEY
from utils.db import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

SQL_TOP_CRESCIMENTO = """
SELECT
    c.descricao AS setor,
    m.nome AS municipio,
    st.total_aberturas,
    st.variacao_pct
FROM estatisticas_crescimento st
JOIN cnaes c      ON c.codigo = st.cnae_codigo
JOIN municipios m ON m.codigo_municipio = st.codigo_municipio
WHERE st.ano_mes = (SELECT max(ano_mes) FROM estatisticas_crescimento)
  AND st.variacao_pct IS NOT NULL
ORDER BY st.variacao_pct DESC
LIMIT 5;
"""

PROMPT_SISTEMA = (
    "Você resume dados de crescimento empresarial regional para um dashboard. "
    "Use exclusivamente os números fornecidos no JSON abaixo. "
    "Nunca invente números, setores ou municípios que não estejam no JSON. "
    "Responda em português, no máximo 3 frases, tom direto e analítico."
)


def main() -> None:
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY não definida — pulando geração de insight.")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_TOP_CRESCIMENTO)
            colunas = [desc[0] for desc in cur.description]
            linhas = [dict(zip(colunas, row)) for row in cur.fetchall()]

        if not linhas:
            logger.warning("Sem agregados suficientes para gerar insight ainda.")
            return

        snapshot = {"top_setores_crescimento_rmpa": linhas}

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resposta = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            system=PROMPT_SISTEMA,
            messages=[{"role": "user", "content": json.dumps(snapshot, default=str)}],
        )
        texto_insight = resposta.content[0].text

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO insights_ia (titulo, conteudo, baseado_em, modelo)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    "Panorama de crescimento setorial — RMPA",
                    texto_insight,
                    json.dumps(snapshot, default=str),
                    "claude-sonnet-5",
                ),
            )

    logger.info("Insight gerado e salvo: %s", texto_insight[:120])


if __name__ == "__main__":
    main()
