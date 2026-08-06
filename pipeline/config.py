"""
Configuração central do pipeline Startup Radar POA.

Todas as credenciais vêm de variáveis de ambiente — nunca hardcoded.
Use um arquivo `.env` local (nunca commitado) carregado via python-dotenv.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Diretórios
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"          # arquivos .zip baixados da Receita
STAGING_DIR = BASE_DIR / "data" / "staging"  # arquivos descompactados/filtrados
RAW_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Fonte de dados — Dados Abertos do CNPJ (Receita Federal)
# ---------------------------------------------------------------------------
# A Receita publica lotes mensais. Confirme a URL vigente em:
# https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj
RECEITA_BASE_URL = os.getenv(
    "RECEITA_BASE_URL",
    "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/",
)

# ---------------------------------------------------------------------------
# Whitelist regional — Região Metropolitana de Porto Alegre (34 municípios)
# Filtrar por NOME normalizado; o código oficial é resolvido a partir do
# arquivo de referência de municípios que vem no próprio lote da Receita.
# Ver database/municipios_rmpa_referencia.md para a fonte e ressalvas.
# ---------------------------------------------------------------------------
MUNICIPIOS_RMPA = {
    "PORTO ALEGRE", "ALVORADA", "ARARICA", "ARROIO DOS RATOS", "CACHOEIRINHA",
    "CAMPO BOM", "CANOAS", "CAPELA DE SANTANA", "CHARQUEADAS", "DOIS IRMAOS",
    "ELDORADO DO SUL", "ESTANCIA VELHA", "ESTEIO", "GLORINHA", "GRAVATAI",
    "GUAIBA", "IGREJINHA", "IVOTI", "MONTENEGRO", "NOVA HARTZ",
    "NOVA SANTA RITA", "NOVO HAMBURGO", "PAROBE", "PORTAO", "ROLANTE",
    "SANTO ANTONIO DA PATRULHA", "SAPIRANGA", "SAPUCAIA DO SUL",
    "SAO JERONIMO", "SAO LEOPOLDO", "SAO SEBASTIAO DO CAI", "TAQUARA",
    "TRIUNFO", "VIAMAO",
}

# Situação cadastral (tabela de domínio da Receita Federal)
SITUACAO_ATIVA = 2

# Janela de "empresa aberta recentemente" usada nos agregados de crescimento
MESES_JANELA_CRESCIMENTO = 24

# ---------------------------------------------------------------------------
# Supabase / Postgres
# ---------------------------------------------------------------------------
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")  # connection string completa (modo "session pooler")
if not SUPABASE_DB_URL:
    raise RuntimeError(
        "SUPABASE_DB_URL não definida. Copie .env.example para .env e preencha."
    )

# ---------------------------------------------------------------------------
# APIs externas (uso opcional, batch, nunca no caminho síncrono do usuário)
# ---------------------------------------------------------------------------
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Limite explícito de custo: nº máximo de leads enriquecidos por execução
PLACES_ENRICHMENT_LIMIT = int(os.getenv("PLACES_ENRICHMENT_LIMIT", "50"))
