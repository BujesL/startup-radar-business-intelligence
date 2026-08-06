"""
Etapa 3 — Normalização e transformação.

Recebe os Parquets regionais gerados pela etapa 2 e produz DataFrames já no
formato de destino das tabelas do Postgres: tipos corretos, datas parseadas,
CNAE principal separado do secundário, e um join com Empresas para trazer
razão social / porte / capital social.

Uso:
    python 3_transform.py --lote 2026-06
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import polars as pl

from config import RAW_DIR, SITUACAO_ATIVA, STAGING_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

COLUNAS_EMPRESAS = [
    "cnpj_basico", "razao_social", "natureza_juridica",
    "qualificacao_responsavel", "capital_social", "porte", "ente_federativo",
]


def parse_data_receita(coluna: pl.Expr) -> pl.Expr:
    """Datas da Receita vêm como string 'YYYYMMDD' (ou '0' quando ausente)."""
    return (
        pl.when(coluna.str.len_chars() == 8)
        .then(coluna.str.strptime(pl.Date, "%Y%m%d", strict=False))
        .otherwise(None)
    )


def carregar_empresas(lote_dir: Path) -> pl.DataFrame:
    frames = []
    for caminho_zip in sorted(lote_dir.glob("Empresas*.zip")):
        with zipfile.ZipFile(caminho_zip) as zf:
            nome_interno = zf.namelist()[0]
            zf.extract(nome_interno, STAGING_DIR)
        csv_path = STAGING_DIR / nome_interno
        df = pl.read_csv(
            csv_path,
            separator=";",
            encoding="latin-1",
            has_header=False,
            new_columns=COLUNAS_EMPRESAS,
            infer_schema_length=0,
        )
        frames.append(df)
        csv_path.unlink()
    return pl.concat(frames)


def main(lote: str) -> None:
    lote_dir = RAW_DIR / lote

    logger.info("Carregando estabelecimentos filtrados (Parquet)...")
    estab = pl.concat(
        [pl.read_parquet(p) for p in sorted(STAGING_DIR.glob("estabelecimentos_rmpa_*.parquet"))]
    )
    logger.info("  %d linhas carregadas.", estab.height)

    logger.info("Carregando empresas (razão social, porte, capital social)...")
    empresas = carregar_empresas(lote_dir)

    estab_transformado = estab.with_columns([
        (pl.col("cnpj_basico") + pl.col("cnpj_ordem") + pl.col("cnpj_dv")).alias("cnpj"),
        parse_data_receita(pl.col("data_inicio_atividade")).alias("data_inicio_atividade"),
        parse_data_receita(pl.col("data_situacao_cadastral")).alias("data_situacao"),
        pl.col("situacao_cadastral").cast(pl.Int16, strict=False),
    ]).filter(
        # Só empresas ativas: é o único universo que interessa para "setores em
        # crescimento" (etapa 5 já filtra por isso) e mantém o volume de dados
        # dentro do limite de armazenamento do plano Supabase usado no estudo.
        pl.col("situacao_cadastral") == SITUACAO_ATIVA
    ).select([
        "cnpj", "cnpj_basico", "nome_fantasia", "situacao_cadastral",
        "data_situacao", "data_inicio_atividade", "cnae_principal",
        "codigo_municipio", "logradouro", "numero", "bairro", "cep",
        "telefone_1", "email",
    ]).rename({"telefone_1": "telefone"})

    empresas_transformado = empresas.with_columns([
        pl.col("capital_social").str.replace(",", ".").cast(pl.Float64, strict=False),
        pl.col("porte").cast(pl.Int16, strict=False),
    ]).select(["cnpj_basico", "razao_social", "natureza_juridica", "porte", "capital_social"])

    # Remove duplicatas de empresas (o mesmo cnpj_basico pode aparecer em mais
    # de um estabelecimento — matriz + filiais — mas a tabela `empresas` é 1:1)
    empresas_transformado = empresas_transformado.unique(subset=["cnpj_basico"], keep="first")

    # Empresas.zip traz o cadastro nacional inteiro (~66M linhas); mantemos só
    # as que têm ao menos um estabelecimento na RMPA (semi-join), senão a
    # etapa 4 tentaria carregar o Brasil inteiro na tabela `empresas`.
    empresas_transformado = empresas_transformado.filter(
        pl.col("cnpj_basico").is_in(estab_transformado["cnpj_basico"].unique())
    )

    saida_estab = STAGING_DIR / "estabelecimentos_final.parquet"
    saida_emp = STAGING_DIR / "empresas_final.parquet"
    estab_transformado.write_parquet(saida_estab)
    empresas_transformado.write_parquet(saida_emp)

    logger.info(
        "Transformação concluída: %d estabelecimentos, %d empresas -> %s / %s",
        estab_transformado.height, empresas_transformado.height, saida_estab.name, saida_emp.name,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lote", required=True)
    args = parser.parse_args()
    main(args.lote)
