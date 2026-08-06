"""Logger padronizado para todos os scripts do pipeline.

Formato estruturado o suficiente para diagnosticar falhas em produção,
mas simples o bastante para rodar localmente sem infraestrutura extra.
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # evita handlers duplicados em re-importações

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger
