"""
Etapa 5 — Cálculo dos agregados de crescimento.

Pré-computa, por CNAE + município + mês, o total de aberturas e a variação
percentual vs. a média móvel dos 6 meses anteriores. Isso é o que alimenta o
ranking "setores em crescimento" do dashboard sem exigir GROUP BY pesado a
cada carregamento de página.

Uso:
    python 5_compute_stats.py
"""
from __future__ import annotations

from utils.db import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

SQL_RECALCULA_AGREGADOS = """
WITH aberturas_mensais AS (
    SELECT
        cnae_principal          AS cnae_codigo,
        codigo_municipio,
        date_trunc('month', data_inicio_atividade)::date AS ano_mes,
        count(*)                AS total_aberturas
    FROM estabelecimentos
    WHERE situacao_cadastral = 2  -- apenas empresas ativas
      AND data_inicio_atividade IS NOT NULL
    GROUP BY 1, 2, 3
),
com_media_movel AS (
    SELECT
        *,
        avg(total_aberturas) OVER (
            PARTITION BY cnae_codigo, codigo_municipio
            ORDER BY ano_mes
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
        ) AS media_movel_6m
    FROM aberturas_mensais
)
SELECT
    cnae_codigo,
    codigo_municipio,
    ano_mes,
    total_aberturas,
    CASE
        WHEN media_movel_6m IS NULL OR media_movel_6m = 0 THEN NULL
        ELSE round(((total_aberturas - media_movel_6m) / media_movel_6m * 100)::numeric, 2)
    END AS variacao_pct
FROM com_media_movel;
"""


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            logger.info("Recalculando estatisticas_crescimento...")
            cur.execute("TRUNCATE TABLE estatisticas_crescimento")
            cur.execute(
                f"""
                INSERT INTO estatisticas_crescimento
                    (cnae_codigo, codigo_municipio, ano_mes, total_aberturas, variacao_pct)
                {SQL_RECALCULA_AGREGADOS}
                """
            )
            cur.execute("SELECT count(*) FROM estatisticas_crescimento")
            total = cur.fetchone()[0]

    logger.info("Agregados recalculados: %d linhas em estatisticas_crescimento.", total)


if __name__ == "__main__":
    main()
