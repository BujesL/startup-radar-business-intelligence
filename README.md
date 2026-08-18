<div align="center">

# 📡 Startup Radar POA

**Pipeline de dados + dashboard para identificar setores em crescimento na Região Metropolitana de Porto Alegre**, a partir de dados públicos de CNPJ da Receita Federal.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Polars](https://img.shields.io/badge/Polars-1.9-CD792C?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

</div>

> **Escopo declarado:** este é um estudo de caso do fluxo `dados públicos → Python/Polars → Postgres → Next.js`. Não é um serviço com atualização automática — o pipeline roda sob demanda e carrega um snapshot mensal. As decisões de arquitetura abaixo foram tomadas conscientes desse escopo, não por limitação técnica.

---

## 🎯 O problema

A Receita Federal publica mensalmente o cadastro nacional de CNPJ (**centenas de milhões de registros**, distribuídos em arquivos `.zip` de CSV sem cabeçalho). Extrair um recorte útil disso — "quais setores estão abrindo mais empresas na Grande Porto Alegre nos últimos meses" — não é trivial: o arquivo nacional não cabe confortavelmente em memória em uma máquina comum, e não existe filtro por região no formato original.

O Startup Radar POA resolve isso com um pipeline em três fases (filtrar → agregar → servir) e apresenta o resultado em um dashboard de leitura rápida, com um lead scoring simples e um insight gerado por IA para contextualizar os números.

## 🏗️ Arquitetura

```
Receita Federal (CSV, escala nacional)
        │  scan_csv() — Polars lazy, predicate pushdown
        ▼
┌─────────────────────────────────────────┐
│  pipeline/  (Python)                     │
│  1_download → 2_filter_region →          │
│  3_transform → 4_load → 5_compute_stats  │
│  [opcional] 6_enrich_places → 7_generate_insight │
└─────────────────────────────────────────┘
        │  COPY (bulk load)
        ▼
┌─────────────────────────────────────────┐
│  Supabase (Postgres 15 + RLS)            │
│  tabelas de fato + agregados pré-computados │
└─────────────────────────────────────────┘
        │  Server Components (SSR, sem chave exposta ao browser)
        ▼
┌─────────────────────────────────────────┐
│  webapp/  (Next.js 15 + Vercel)          │
│  dashboard read-only, autenticado         │
└─────────────────────────────────────────┘
```

## ⚙️ Decisões técnicas que valem destacar

Estas são as escolhas que diferenciam o projeto de um script de ETL genérico — cada uma resolve um problema real de escala, custo ou segurança, e não é incidental:

| Decisão | Por quê |
|---|---|
| **Filtro regional na origem com Polars `scan_csv` (lazy)** | O dataset nacional de estabelecimentos tem centenas de milhões de linhas. Ler tudo com `pandas.read_csv()` tentaria alocar todas as colunas em RAM antes de filtrar. O modo lazy do Polars aplica o filtro de município ainda no plano de execução (predicate pushdown), nunca materializando o dataset inteiro. |
| **Agregados pré-computados, não calculados em runtime** | `estatisticas_crescimento` é recalculada pelo pipeline (com uma janela de média móvel de 6 meses via `AVG() OVER`). O dashboard só faz `SELECT`, nunca um `GROUP BY` pesado a cada carregamento de página. |
| **Carga via `COPY`, não `INSERT` linha a linha** | Para centenas de milhares de registros, `COPY` é ordens de magnitude mais rápido — é o mecanismo de carga em lote recomendado pelo próprio Postgres. |
| **RLS (Row Level Security) habilitado desde o schema inicial** | Leitura liberada para usuários autenticados; escrita restrita ao `service_role`, que só o pipeline possui. O frontend nunca tem permissão de escrita — mesmo que a chave `anon` fosse exposta, não haveria como alterar dados. |
| **IA sem alucinação por design** | A Claude API nunca recebe uma pergunta livre sobre o dataset. Ela recebe apenas o JSON já agregado pelo Postgres (top setores por variação %) e sua única tarefa é narrar esse JSON em 2–3 frases. O JSON usado é salvo em `insights_ia.baseado_em`, então qualquer frase gerada é auditável contra o número exato que a originou. |
| **Enriquecimento de leads limitado e em lote** | O Google Places só é chamado para o top-N leads dos setores em maior crescimento (`PLACES_ENRICHMENT_LIMIT`, configurável), nunca de forma síncrona a uma requisição do usuário. Idempotente via `ON CONFLICT` — pode ser re-executado sem duplicar nem estourar custo. |
| **Autenticação via Server Components + middleware de refresh de sessão** | A sessão do Supabase é resolvida no servidor a partir dos cookies da requisição — nenhuma chave sensível chega ao browser. O middleware renova o token a cada request, porque Server Components não conseguem escrever cookies fora de uma Server Action. |
| **Chaves naturais preservadas como `VARCHAR`, não `INT`** | Códigos de município e CNAE da Receita têm zeros à esquerda com significado semântico — convertê-los para inteiro corromperia o dado silenciosamente. |

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| **Pipeline de dados** | Python 3.11+, Polars 1.9 (lazy/streaming), psycopg 3 (`COPY`), httpx, Anthropic SDK |
| **Banco de dados** | PostgreSQL 15 (Supabase), Row Level Security, índices compostos por município + data |
| **Frontend** | Next.js 15 (App Router, Server Components), React 18, TypeScript 5, Tailwind CSS |
| **Visualização** | Recharts (gráfico de crescimento), TanStack Table (tabela de leads com ordenação/filtro), React Leaflet |
| **Auth & Infra** | Supabase Auth (`@supabase/ssr`), deploy no Vercel |
| **IA** | Claude API (`claude-sonnet-4-5`) — geração de insight textual a partir de dados já agregados |

## 📂 Estrutura do repositório

```
database/   → schema.sql (Postgres/Supabase) + referência dos 34 municípios da RMPA
pipeline/   → scripts Python (download → filtro → transformação → carga → agregados → enriquecimento → IA)
webapp/     → dashboard Next.js 15 (Server Components, auth, gráficos)
```

## 🚀 Como executar

### 1. Infraestrutura (Supabase)

```bash
# 1. Crie um projeto em supabase.com (região sa-east-1 para menor latência)
# 2. Execute database/schema.sql inteiro no SQL Editor
# 3. Copie a Project URL, a anon key e a connection string (Session pooler)
# 4. Crie manualmente o(s) usuário(s) de acesso em Authentication → Users
```

### 2. Pipeline de dados

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha SUPABASE_DB_URL

python 1_download.py --lote 2026-06
python 0_load_reference_tables.py --lote 2026-06
python 2_filter_region.py --lote 2026-06
python 3_transform.py --lote 2026-06
python 4_load.py
python 5_compute_stats.py

# opcionais — custam chamadas de API, preencha as chaves antes
python 6_enrich_places.py
python 7_generate_insight.py
```

### 3. Dashboard

```bash
cd webapp
npm install
cp .env.example .env.local   # NEXT_PUBLIC_SUPABASE_URL e ANON_KEY
npm run dev
```

### 4. Deploy

Repositório no GitHub → import no Vercel → **Root Directory:** `webapp/` → configurar as duas variáveis de ambiente em Project Settings. Deploy automático a cada push.

## 🗺️ Escopo da região analisada

34 municípios da Região Metropolitana de Porto Alegre (fonte: Metroplan/RS e IBGE), resolvidos dinamicamente pelo pipeline a partir da tabela de referência oficial que a própria Receita distribui junto ao lote — nunca por código fabricado manualmente, que é uma fonte comum de erro silencioso entre bases governamentais diferentes.

## 🔭 Roadmap (fora do escopo desta v1, por decisão deliberada de prazo)

- [ ] Atualização automática recorrente do pipeline (cron mensal)
- [ ] Mapa completo do Brasil (hoje: apenas RMPA)
- [ ] Exportação em Excel/PDF (hoje: apenas CSV)
- [ ] Página de perfil detalhado por empresa, com "empresas semelhantes"

---

<div align="center">

Desenvolvido por **[Vinícius Bujes de Lima](https://github.com/BujesL)**

</div>
