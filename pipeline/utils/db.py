"""Conexão centralizada com o Postgres (Supabase).

Usa psycopg 3 com autocommit desabilitado por padrão — cada script decide
explicitamente quando commitar, evitando escritas parciais em caso de erro
no meio de uma carga em lote.
"""
from __future__ import annotations

import contextlib
from typing import Iterator

import psycopg

from config import SUPABASE_DB_URL


@contextlib.contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(SUPABASE_DB_URL, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
