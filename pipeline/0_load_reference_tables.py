"""
Etapa 0 — Carga das tabelas de referência (CNAEs, Municípios, Natureza Jurídica).

Deve ser executada UMA VEZ antes da primeira carga de empresas/estabelecimentos,
pois essas tabelas são o destino das foreign keys `cnae_principal`,
`codigo_municipio` e `natureza_juridica`. Rodar de novo é seguro (idempotente
via UPSERT) caso a Receita publique atualizações nessas tabelas de domínio.

Uso:
    python 0_load_reference_tables.py --lote 2026-06
"""
from __future__ import annotations

import argparse
import unicodedata
import zipfile
from pathlib import Path

import polars as pl

from config import MUNICIPIOS_RMPA, RAW_DIR, STAGING_DIR
from utils.db import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def normalizar_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.strip().upper()


def extrair(caminho_zip: Path) -> Path:
    with zipfile.ZipFile(caminho_zip) as zf:
        nome = zf.namelist()[0]
        zf.extract(nome, STAGING_DIR)
    return STAGING_DIR / nome


def upsert(cur, tabela: str, colunas: list[str], registros: list[tuple], chave: str) -> None:
    placeholders = ", ".join(["%s"] * len(colunas))
    atualizacoes = ", ".join(f"{c} = EXCLUDED.{c}" for c in colunas if c != chave)
    sql = (
        f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({chave}) DO UPDATE SET {atualizacoes}"
    )
    cur.executemany(sql, registros)
    logger.info("  Upsert em %s: %d registros", tabela, len(registros))


def main(lote: str) -> None:
    lote_dir = RAW_DIR / lote

    # Natureza jurídica
    natureza_csv = extrair(lote_dir / "Naturezas.zip")
    natureza_df = pl.read_csv(
        natureza_csv, separator=";", encoding="latin-1", has_header=False,
        new_columns=["codigo", "descricao"], infer_schema_length=0,
    )

    # CNAEs
    cnae_csv = extrair(lote_dir / "Cnaes.zip")
    cnae_df = pl.read_csv(
        cnae_csv, separator=";", encoding="latin-1", has_header=False,
        new_columns=["codigo", "descricao"], infer_schema_length=0,
    )

    # Municípios — filtra já aqui para não poluir a tabela com o Brasil inteiro
    municipio_csv = extrair(lote_dir / "Municipios.zip")
    municipio_df = pl.read_csv(
        municipio_csv, separator=";", encoding="latin-1", has_header=False,
        new_columns=["codigo_municipio", "nome"], infer_schema_length=0,
    ).with_columns(
        pl.col("nome").map_elements(normalizar_nome, return_dtype=pl.Utf8).alias("nome_normalizado")
    ).filter(pl.col("nome_normalizado").is_in(MUNICIPIOS_RMPA))

    with get_connection() as conn:
        with conn.cursor() as cur:
            upsert(cur, "natureza_juridica", ["codigo", "descricao"], natureza_df.rows(), "codigo")
            upsert(cur, "cnaes", ["codigo", "descricao"], cnae_df.rows(), "codigo")
            upsert(
                cur, "municipios", ["codigo_municipio", "nome"],
                municipio_df.select(["codigo_municipio", "nome"]).rows(), "codigo_municipio",
            )

    for p in (natureza_csv, cnae_csv, municipio_csv):
        p.unlink()

    logger.info("Tabelas de referência carregadas: %d municípios da RMPA.", municipio_df.height)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lote", required=True)
    args = parser.parse_args()
    main(args.lote)
