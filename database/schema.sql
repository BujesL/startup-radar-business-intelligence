-- ============================================================================
-- Startup Radar POA — Schema do Banco de Dados
-- Motor: PostgreSQL 15+ (Supabase)
--
-- Convenções:
--   * snake_case para todos os identificadores
--   * chaves naturais da Receita Federal preservadas como VARCHAR (não INT),
--     pois possuem zeros à esquerda com significado (ex.: código de município)
--   * todas as tabelas de fato possuem índice cobrindo os filtros mais comuns
--     do dashboard (município + data, cnae)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Tabelas de referência (carga única, praticamente estáticas)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS municipios (
    codigo_municipio    VARCHAR(7) PRIMARY KEY,      -- código de município da Receita Federal
    nome                TEXT NOT NULL,
    uf                  CHAR(2) NOT NULL DEFAULT 'RS',
    codigo_ibge         VARCHAR(7),                  -- para cruzar com malhas geográficas (mapa)
    latitude            NUMERIC(9,6),
    longitude           NUMERIC(9,6)
);
COMMENT ON TABLE municipios IS 'Whitelist de municípios da Região Metropolitana de Porto Alegre usada para filtrar o dataset nacional na origem.';

CREATE TABLE IF NOT EXISTS cnaes (
    codigo              VARCHAR(7) PRIMARY KEY,
    descricao           TEXT NOT NULL,
    grupo_setorial      TEXT                          -- agrupamento manual/heurístico para ranking (ex.: "Tecnologia", "Alimentação")
);

CREATE TABLE IF NOT EXISTS natureza_juridica (
    codigo              VARCHAR(4) PRIMARY KEY,
    descricao           TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 2. Tabelas de fato (carregadas pelo pipeline, volume maior)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS empresas (
    cnpj_basico         VARCHAR(8) PRIMARY KEY,       -- 8 primeiros dígitos do CNPJ (identifica a empresa, não o estabelecimento)
    razao_social        TEXT NOT NULL,
    natureza_juridica   VARCHAR(4) REFERENCES natureza_juridica(codigo),
    porte               SMALLINT,                     -- 01=MEI/ME, 03=Pequeno, 05=Demais
    capital_social       NUMERIC(15,2),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS estabelecimentos (
    cnpj                 VARCHAR(14) PRIMARY KEY,      -- CNPJ completo (14 dígitos)
    cnpj_basico          VARCHAR(8) NOT NULL REFERENCES empresas(cnpj_basico),
    nome_fantasia        TEXT,
    situacao_cadastral   SMALLINT NOT NULL,             -- 01=Nula,02=Ativa,03=Suspensa,04=Inapta,08=Baixada
    data_situacao        DATE,
    data_inicio_atividade DATE NOT NULL,
    cnae_principal       VARCHAR(7) REFERENCES cnaes(codigo),
    codigo_municipio     VARCHAR(7) NOT NULL REFERENCES municipios(codigo_municipio),
    logradouro           TEXT,
    numero               TEXT,
    bairro               TEXT,
    cep                  VARCHAR(8),
    telefone             TEXT,
    email                TEXT,
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices cobrindo os filtros reais do dashboard (evitar sequential scan em tabela que cresce)
CREATE INDEX IF NOT EXISTS idx_estab_municipio_data ON estabelecimentos (codigo_municipio, data_inicio_atividade DESC);
CREATE INDEX IF NOT EXISTS idx_estab_cnae            ON estabelecimentos (cnae_principal);
CREATE INDEX IF NOT EXISTS idx_estab_situacao_ativa   ON estabelecimentos (situacao_cadastral) WHERE situacao_cadastral = 2;
CREATE INDEX IF NOT EXISTS idx_estab_data_inicio      ON estabelecimentos (data_inicio_atividade DESC);

-- ----------------------------------------------------------------------------
-- 3. Agregados pré-computados (o pipeline recalcula; o dashboard só lê)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS estatisticas_crescimento (
    cnae_codigo         VARCHAR(7) NOT NULL REFERENCES cnaes(codigo),
    codigo_municipio    VARCHAR(7) NOT NULL REFERENCES municipios(codigo_municipio),
    ano_mes             DATE NOT NULL,                 -- sempre o dia 1 do mês (ex.: 2026-06-01)
    total_aberturas     INT NOT NULL DEFAULT 0,
    variacao_pct        NUMERIC(6,2),                  -- variação vs. média móvel dos 6 meses anteriores
    PRIMARY KEY (cnae_codigo, codigo_municipio, ano_mes)
);
CREATE INDEX IF NOT EXISTS idx_stats_ano_mes ON estatisticas_crescimento (ano_mes DESC);

-- ----------------------------------------------------------------------------
-- 4. Enriquecimento externo (Google Places) — tabela separada de propósito:
--    isola dado de terceiro (pago, sujeito a ToS) do dado oficial da Receita.
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS leads_enriquecidos (
    cnpj                 VARCHAR(14) PRIMARY KEY REFERENCES estabelecimentos(cnpj),
    place_id             TEXT,
    endereco_formatado   TEXT,
    telefone_places      TEXT,
    website              TEXT,
    rating_google        NUMERIC(2,1),
    total_avaliacoes     INT,
    enriquecido_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 5. Insights gerados por IA (auditáveis: sempre referenciam o snapshot usado)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS insights_ia (
    id                   SERIAL PRIMARY KEY,
    titulo               TEXT NOT NULL,
    conteudo             TEXT NOT NULL,
    baseado_em           JSONB NOT NULL,     -- snapshot exato dos agregados usados no prompt (auditoria anti-alucinação)
    modelo               TEXT NOT NULL DEFAULT 'claude-sonnet-4-5-20250929',
    gerado_em            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 6. Row Level Security — habilitado desde o início.
--    Leitura pública (dashboard é read-only para visitantes autenticados),
--    escrita restrita ao service_role (usado apenas pelo pipeline via backend).
-- ----------------------------------------------------------------------------

ALTER TABLE empresas                ENABLE ROW LEVEL SECURITY;
ALTER TABLE estabelecimentos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE estatisticas_crescimento ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads_enriquecidos      ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights_ia             ENABLE ROW LEVEL SECURITY;

CREATE POLICY "leitura_autenticada_empresas"
    ON empresas FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "leitura_autenticada_estabelecimentos"
    ON estabelecimentos FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "leitura_autenticada_stats"
    ON estatisticas_crescimento FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "leitura_autenticada_leads_enriquecidos"
    ON leads_enriquecidos FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "leitura_autenticada_insights"
    ON insights_ia FOR SELECT
    TO authenticated
    USING (true);

-- Nenhuma policy de INSERT/UPDATE/DELETE é criada para o papel `authenticated`.
-- Isso significa: por padrão, ninguém além do service_role (usado só pelo
-- pipeline, nunca pelo frontend) pode escrever. Ajuste conscientemente se
-- precisar de escrita a partir do app (ex.: favoritar um lead).
