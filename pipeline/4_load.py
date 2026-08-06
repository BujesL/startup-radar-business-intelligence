"""
Etapa 4 — Carga no Postgres (Supabase).

Usa COPY (via psycopg `copy()`), não INSERT linha a linha — para centenas de
milhares de linhas, COPY é ordens de magnitude mais rápido e é o padrão
recomendado do próprio Postgres para cargas em lote.

Estratégia de idempotência: cada execução trunca e recarrega as tabelas de
fato (TRUNCATE + COPY dentro da mesma transação). Como este é um pipeline de
estudo, não incremental, recarregar do zero é mais simples e mais seguro do
que reconciliar deltas — e o custo de reprocessar o dataset regional (não o
nacional) é baixo.

Uso:
    python 4_load.py
"""
from __future__ import annotations

import polars as pl

from config import STAGING_DIR
from utils.db import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def copiar_dataframe(cur, df: pl.DataFrame, tabela: str, colunas: list[str]) -> None:
    registros = df.select(colunas).rows()
    with cur.copy(f"COPY {tabela} ({', '.join(colunas)}) FROM STDIN") as copy:
        for linha in registros:
            copy.write_row(linha)
    logger.info("  COPY em %s: %d linhas", tabela, len(registros))


def main() -> None:
    empresas = pl.read_parquet(STAGING_DIR / "empresas_final.parquet")
    estabelecimentos = pl.read_parquet(STAGING_DIR / "estabelecimentos_final.parquet")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # O pooler do Supabase aplica um statement_timeout padrão (~2min),
            # curto demais para o COPY de ~2M linhas de estabelecimentos.
            cur.execute("SET statement_timeout = '20min'")
            logger.info("Truncando tabelas de fato (CASCADE) antes da recarga...")
            cur.execute("TRUNCATE TABLE estabelecimentos, empresas CASCADE")

            copiar_dataframe(
                cur, empresas, "empresas",
                ["cnpj_basico", "razao_social", "natureza_juridica", "porte", "capital_social"],
            )
            copiar_dataframe(
                cur, estabelecimentos, "estabelecimentos",
                [
                    "cnpj", "cnpj_basico", "nome_fantasia", "situacao_cadastral",
                    "data_situacao", "data_inicio_atividade", "cnae_principal",
                    "codigo_municipio", "logradouro", "numero", "bairro", "cep",
                    "telefone", "email",
                ],
            )
        # commit acontece automaticamente ao saída do context manager get_connection

    logger.info("Carga concluída com sucesso.")


if __name__ == "__main__":
    main()
