"""
Etapa 6 (opcional) — Enriquecimento de leads via Google Places API.

Decisões deliberadas:
  * Só enriquece o TOP-N leads (config.PLACES_ENRICHMENT_LIMIT) dos setores em
    maior crescimento — não o dataset inteiro. Motivo: custo (Places Text
    Search / Place Details são cobrados por chamada) e relevância (o objetivo
    é prospecção, não um catálogo completo).
  * Roda em batch, fora do caminho de request do usuário — nunca chame esta
    API a partir do frontend/dashboard.
  * Rate limiting simples (sleep) para não estourar quota por segundo.
  * Idempotente: usa ON CONFLICT, então pode ser reexecutado sem duplicar.

Uso:
    python 6_enrich_places.py
"""
from __future__ import annotations

import time

import httpx

from config import GOOGLE_PLACES_API_KEY, PLACES_ENRICHMENT_LIMIT
from utils.db import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

SQL_TOP_LEADS = """
SELECT e.cnpj, em.razao_social, m.nome AS municipio
FROM estabelecimentos e
JOIN empresas em    ON em.cnpj_basico = e.cnpj_basico
JOIN municipios m   ON m.codigo_municipio = e.codigo_municipio
JOIN estatisticas_crescimento st
     ON st.cnae_codigo = e.cnae_principal AND st.codigo_municipio = e.codigo_municipio
WHERE e.situacao_cadastral = 2
ORDER BY st.variacao_pct DESC NULLS LAST
LIMIT %(limite)s;
"""

SQL_UPSERT_LEAD = """
INSERT INTO leads_enriquecidos (cnpj, place_id, endereco_formatado, telefone_places, website, rating_google, total_avaliacoes)
VALUES (%(cnpj)s, %(place_id)s, %(endereco)s, %(telefone)s, %(website)s, %(rating)s, %(total_avaliacoes)s)
ON CONFLICT (cnpj) DO UPDATE SET
    place_id = EXCLUDED.place_id,
    endereco_formatado = EXCLUDED.endereco_formatado,
    telefone_places = EXCLUDED.telefone_places,
    website = EXCLUDED.website,
    rating_google = EXCLUDED.rating_google,
    total_avaliacoes = EXCLUDED.total_avaliacoes,
    enriquecido_em = now();
"""


def buscar_place(razao_social: str, municipio: str, client: httpx.Client) -> dict | None:
    resp = client.post(
        PLACES_TEXT_SEARCH_URL,
        headers={
            "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": (
                "places.id,places.formattedAddress,places.internationalPhoneNumber,"
                "places.websiteUri,places.rating,places.userRatingCount"
            ),
        },
        json={"textQuery": f"{razao_social}, {municipio}, RS, Brasil"},
        timeout=15,
    )
    resp.raise_for_status()
    dados = resp.json()
    places = dados.get("places", [])
    return places[0] if places else None


def main() -> None:
    if not GOOGLE_PLACES_API_KEY:
        logger.warning("GOOGLE_PLACES_API_KEY não definida — pulando enriquecimento.")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_TOP_LEADS, {"limite": PLACES_ENRICHMENT_LIMIT})
            leads = cur.fetchall()

        logger.info("Enriquecendo até %d leads via Google Places...", len(leads))
        with httpx.Client() as client, conn.cursor() as cur:
            for cnpj, razao_social, municipio in leads:
                try:
                    place = buscar_place(razao_social, municipio, client)
                except httpx.HTTPStatusError as exc:
                    logger.error("Falha ao consultar Places para %s: %s", razao_social, exc)
                    continue

                if not place:
                    continue

                cur.execute(SQL_UPSERT_LEAD, {
                    "cnpj": cnpj,
                    "place_id": place.get("id"),
                    "endereco": place.get("formattedAddress"),
                    "telefone": place.get("internationalPhoneNumber"),
                    "website": place.get("websiteUri"),
                    "rating": place.get("rating"),
                    "total_avaliacoes": place.get("userRatingCount"),
                })
                time.sleep(0.2)  # rate limiting simples — ajuste conforme sua quota

    logger.info("Enriquecimento concluído.")


if __name__ == "__main__":
    main()
