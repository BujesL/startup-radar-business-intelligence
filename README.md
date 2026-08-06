# Startup Radar POA

Estudo de caso: identificação de setores em crescimento na Região
Metropolitana de Porto Alegre a partir de dados públicos de CNPJ da Receita
Federal, com dashboard web e enriquecimento opcional de leads via Google
Places.

> **Escopo declarado:** exercício de estudo do fluxo Python → Supabase →
> Vercel. Não é um serviço com atualização automática de dados — o pipeline
> é executado manualmente e carrega um snapshot.

## Arquitetura

```
database/   → schema.sql (Postgres/Supabase) + referência de municípios
pipeline/   → scripts Python (download → filtro → transformação → carga → agregados → IA)
webapp/     → dashboard Next.js 15 (deploy no Vercel)
```

## Passo a passo — do zero ao deploy

### 1. Infraestrutura (Supabase)

1. Crie um projeto em https://supabase.com (região `sa-east-1` para menor latência do Brasil).
2. No SQL Editor do Supabase, execute `database/schema.sql` na íntegra.
3. Em **Project Settings → API**, copie `Project URL` e a `anon public key`.
4. Em **Project Settings → Database → Connection string → Session pooler**, copie a connection string (você vai precisar trocar `[YOUR-PASSWORD]` pela senha do banco).
5. Em **Authentication → Users**, crie manualmente o(s) usuário(s) que vão acessar o dashboard (e-mail/senha) — não há tela pública de cadastro neste MVP, por design.

### 2. Pipeline de dados (local, uma vez)

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha SUPABASE_DB_URL

# Confirme o identificador do lote vigente em:
# https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/
python 1_download.py --lote 2026-06
python 0_load_reference_tables.py --lote 2026-06
python 2_filter_region.py --lote 2026-06
python 3_transform.py --lote 2026-06
python 4_load.py
python 5_compute_stats.py

# Opcionais (custam chamadas de API — preencha as chaves no .env antes)
python 6_enrich_places.py
python 7_generate_insight.py
```

Cada script loga progresso e quantidade de linhas processadas. Se
`1_download.py` falhar, é quase sempre porque o nome do lote ou dos arquivos
mudou no site da Receita — confira a URL manualmente antes de reportar bug.

### 3. Dashboard (local)

```bash
cd webapp
npm install
cp .env.example .env.local   # preencha NEXT_PUBLIC_SUPABASE_URL e ANON_KEY
npm run dev
```

Acesse `http://localhost:3000` e entre com o usuário criado no passo 1.5.

### 4. Deploy

1. **GitHub:** crie um repositório privado, `git init` na raiz deste projeto, commit e push. O `.gitignore` já exclui `node_modules`, `.env` e os dados brutos do pipeline.
2. **Vercel:** importe o repositório, defina o **Root Directory** como `webapp/`, e configure as duas variáveis de ambiente (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`) em Project Settings → Environment Variables. Deploy automático a cada push.

## Decisões técnicas relevantes (para a apresentação do case)

- **Filtro regional na origem, não depois:** o pipeline resolve os códigos de município da RMPA e filtra com Polars em modo lazy/streaming, evitando carregar o dataset nacional inteiro em memória.
- **Agregados pré-computados:** `estatisticas_crescimento` é recalculada pelo pipeline, não em runtime — o dashboard nunca faz `GROUP BY` pesado a cada carregamento de página.
- **IA sem alucinação:** o insight da Claude API recebe só o JSON já agregado pelo Postgres; nunca uma pergunta livre sobre o dataset. O JSON usado é salvo em `insights_ia.baseado_em` para auditoria.
- **RLS desde o schema inicial:** leitura liberada para usuários autenticados, escrita restrita ao `service_role` (só o pipeline tem essa chave, nunca o frontend).
- **Enriquecimento de leads limitado e em lote:** Google Places só é chamado para o top-N leads (custo controlado), nunca de forma síncrona a uma requisição do usuário.

## Roadmap (fora do escopo desta v1, por decisão deliberada de prazo)

- Atualização automática recorrente do pipeline (ex.: cron mensal)
- Mapa completo do Brasil (hoje: apenas RMPA)
- Exportação em Excel/PDF (hoje: apenas CSV)
- Página de perfil detalhado por empresa com "empresas semelhantes"

<!-- yolo merge test -->
<!-- pull shark test -->
<!-- pull shark batch 1 -->
<!-- pull shark batch 2 -->
<!-- pull shark batch 3 -->
