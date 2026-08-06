"""
Etapa 2 — Filtro regional (o passo mais importante do pipeline em termos de
performance).

Os arquivos de Estabelecimentos vêm em CSV (separador ';', sem cabeçalho,
encoding latin-1) e não têm o nome do município — apenas o código. Por isso,
a estratégia é:

  1. Ler o arquivo de Municípios (pequeno) e resolver quais códigos
     correspondem aos nomes da whitelist RMPA (config.MUNICIPIOS_RMPA).
  2. Usar Polars em modo LAZY (`scan_csv`) para ler os arquivos gigantes de
     Estabelecimentos SEM materializá-los inteiros em memória, aplicando o
     filtro de município ainda no plano de execução (predicate pushdown).
  3. Persistir apenas o subconjunto regional em Parquet (formato colunar,
     muito mais rápido para as etapas seguintes do que reabrir CSV).

Por que isso importa: o arquivo nacional de Estabelecimentos tem centenas de
milhões de linhas. Ler tudo com pandas.read_csv() tentaria alocar todas as
colunas de todas as linhas em RAM antes de filtrar — inviável em uma máquina
comum. O `scan_csv` do Polars monta um plano de execução e só materializa o
que sobra depois do filtro.

Uso:
    python 2_filter_region.py --lote 2026-06
"""
from __future__ import annotations

import argparse
import unicodedata
import zipfile
from pathlib import Path

import polars as pl

from config import MUNICIPIOS_RMPA, RAW_DIR, STAGING_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

# Layout oficial do arquivo de Estabelecimentos da Receita Federal (posicional,
# sem cabeçalho). Ver leiaute em: https://www.gov.br/receitafederal (Dados Abertos CNPJ).
COLUNAS_ESTABELECIMENTOS = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
    "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
    "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
    "data_inicio_atividade", "cnae_principal", "cnae_secundario",
    "tipo_logradouro", "logradouro", "numero", "complemento", "bairro",
    "cep", "uf", "codigo_municipio", "ddd_1", "telefone_1", "ddd_2",
    "telefone_2", "ddd_fax", "fax", "email", "situacao_especial",
    "data_situacao_especial",
]

COLUNAS_MUNICIPIOS = ["codigo_municipio", "nome"]


def normalizar_nome(nome: str) -> str:
    """Remove acentos e uppercase, para casar com a whitelist em config.py."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.strip().upper()


def extrair_zip(caminho_zip: Path, destino_dir: Path) -> Path:
    with zipfile.ZipFile(caminho_zip) as zf:
        nome_interno = zf.namelist()[0]
        zf.extract(nome_interno, destino_dir)
    return destino_dir / nome_interno


def transcodificar_para_utf8(caminho_latin1: Path) -> Path:
    """polars.scan_csv (leitor lazy/streaming) só aceita utf8/utf8-lossy —
    diferente de read_csv (eager), que transcodifica internamente. Como os
    arquivos da Receita vêm em latin-1, convertemos em streaming antes do scan."""
    caminho_utf8 = caminho_latin1.with_suffix(".utf8.csv")
    with (
        open(caminho_latin1, "r", encoding="latin-1", errors="replace") as origem,
        open(caminho_utf8, "w", encoding="utf-8") as destino,
    ):
        for linha in origem:
            destino.write(linha)
    caminho_latin1.unlink()
    return caminho_utf8


def resolver_codigos_municipios_rmpa(lote_dir: Path) -> set[str]:
    """Lê o arquivo oficial de Municípios e resolve os códigos da RMPA por nome."""
    csv_path = extrair_zip(lote_dir / "Municipios.zip", STAGING_DIR)
    df = pl.read_csv(
        csv_path,
        separator=";",
        encoding="latin-1",
        has_header=False,
        new_columns=COLUNAS_MUNICIPIOS,
        infer_schema_length=0,  # tudo como string — arquivo tem códigos com zero à esquerda
    )
    df = df.with_columns(pl.col("nome").map_elements(normalizar_nome, return_dtype=pl.Utf8).alias("nome_normalizado"))
    codigos = df.filter(pl.col("nome_normalizado").is_in(MUNICIPIOS_RMPA))["codigo_municipio"].to_list()

    encontrados = set(df.filter(pl.col("codigo_municipio").is_in(codigos))["nome_normalizado"].to_list())
    faltantes = MUNICIPIOS_RMPA - encontrados
    if faltantes:
        logger.warning(
            "%d município(s) da whitelist não foram encontrados no arquivo oficial: %s",
            len(faltantes), sorted(faltantes),
        )
    logger.info("Resolvidos %d códigos de município da RMPA.", len(codigos))
    return set(codigos)


def filtrar_arquivo_estabelecimentos(
    caminho_zip: Path, codigos_rmpa: set[str], saida_parquet: Path
) -> int:
    csv_path = transcodificar_para_utf8(extrair_zip(caminho_zip, STAGING_DIR))

    lazy_df = pl.scan_csv(
        csv_path,
        separator=";",
        encoding="utf8",
        has_header=False,
        new_columns=COLUNAS_ESTABELECIMENTOS,
        infer_schema_length=0,
    ).filter(pl.col("codigo_municipio").is_in(codigos_rmpa))

    resultado = lazy_df.collect(streaming=True)  # streaming: processa em batches, não tudo de uma vez
    resultado.write_parquet(saida_parquet)

    csv_path.unlink()  # libera espaço em disco — já não precisamos do CSV extraído
    return resultado.height


def main(lote: str) -> None:
    lote_dir = RAW_DIR / lote
    codigos_rmpa = resolver_codigos_municipios_rmpa(lote_dir)

    total_linhas = 0
    arquivos_estab = sorted(lote_dir.glob("Estabelecimentos*.zip"))
    if not arquivos_estab:
        raise FileNotFoundError(f"Nenhum arquivo Estabelecimentos*.zip em {lote_dir}")

    for i, caminho_zip in enumerate(arquivos_estab):
        saida = STAGING_DIR / f"estabelecimentos_rmpa_{i}.parquet"
        logger.info("Filtrando %s...", caminho_zip.name)
        linhas = filtrar_arquivo_estabelecimentos(caminho_zip, codigos_rmpa, saida)
        logger.info("  -> %d linhas da RMPA encontradas em %s", linhas, caminho_zip.name)
        total_linhas += linhas

    logger.info("Filtro regional concluído: %d estabelecimentos da RMPA no total.", total_linhas)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lote", required=True)
    args = parser.parse_args()
    main(args.lote)
