"""
Etapa 1 — Download dos arquivos públicos de CNPJ.

A Receita Federal publica o dataset em múltiplos arquivos .zip por tipo
(Empresas, Estabelecimentos, CNAEs, Municípios, Naturezas Jurídicas...).
Para o MVP regional, baixamos apenas os arquivos estritamente necessários:

  - Estabelecimentos*.zip   (maior volume — contém município e CNAE)
  - Empresas*.zip           (razão social, porte, capital social)
  - Cnaes.zip               (tabela de domínio)
  - Municipios.zip          (tabela de domínio — usada para resolver códigos da RMPA)
  - Naturezas.zip           (tabela de domínio)

Uso:
    python 1_download.py --lote 2026-06
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from config import RAW_DIR, RECEITA_BASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)

ARQUIVOS_NECESSARIOS = [
    "Estabelecimentos0.zip",
    "Estabelecimentos1.zip",
    "Estabelecimentos2.zip",
    "Estabelecimentos3.zip",
    "Estabelecimentos4.zip",
    "Estabelecimentos5.zip",
    "Estabelecimentos6.zip",
    "Estabelecimentos7.zip",
    "Estabelecimentos8.zip",
    "Estabelecimentos9.zip",
    "Empresas0.zip",
    "Empresas1.zip",
    "Empresas2.zip",
    "Empresas3.zip",
    "Empresas4.zip",
    "Empresas5.zip",
    "Empresas6.zip",
    "Empresas7.zip",
    "Empresas8.zip",
    "Empresas9.zip",
    "Cnaes.zip",
    "Municipios.zip",
    "Naturezas.zip",
]


def baixar_arquivo(url: str, destino: Path) -> None:
    if destino.exists():
        logger.info("Já existe, pulando: %s", destino.name)
        return

    logger.info("Baixando %s", url)
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as resp:
        resp.raise_for_status()
        tamanho_total = int(resp.headers.get("content-length", 0))
        baixado = 0
        with open(destino, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                baixado += len(chunk)
                if tamanho_total:
                    pct = baixado / tamanho_total * 100
                    print(f"\r  {destino.name}: {pct:5.1f}%", end="", flush=True)
        print()
    logger.info("Concluído: %s (%.1f MB)", destino.name, destino.stat().st_size / 1e6)


def main(lote: str) -> None:
    base_url = f"{RECEITA_BASE_URL}{lote}/"
    lote_dir = RAW_DIR / lote
    lote_dir.mkdir(parents=True, exist_ok=True)

    falhas = []
    for nome_arquivo in ARQUIVOS_NECESSARIOS:
        url = base_url + nome_arquivo
        destino = lote_dir / nome_arquivo
        try:
            baixar_arquivo(url, destino)
        except httpx.HTTPStatusError as exc:
            logger.error("Falha ao baixar %s: %s", nome_arquivo, exc)
            falhas.append(nome_arquivo)

    if falhas:
        logger.warning(
            "%d arquivo(s) falharam. Confirme o nome exato do lote em %s",
            len(falhas),
            base_url,
        )
        sys.exit(1)

    logger.info("Download completo do lote %s em %s", lote, lote_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lote",
        required=True,
        help="Identificador do lote mensal publicado pela Receita, ex.: 2026-06",
    )
    args = parser.parse_args()
    main(args.lote)
