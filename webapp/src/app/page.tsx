import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { StatCard } from "@/components/dashboard/StatCard";
import { GrowthChart } from "@/components/dashboard/GrowthChart";
import { LeadsTable } from "@/components/dashboard/LeadsTable";
import { SignOutButton } from "@/components/dashboard/SignOutButton";
import type { EstatisticaCrescimento, InsightIA, Lead } from "@/lib/types";
import { formatarVariacaoPct, truncar } from "@/lib/format";

const ICON_BUILDING = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M6 22V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v18" strokeLinecap="round" />
    <path d="M2 22h20" strokeLinecap="round" />
    <path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 16h1M14 16h1" strokeLinecap="round" />
  </svg>
);

const ICON_TREND = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 17l6-6 4 4 8-8" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M14 6h7v7" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ICON_MAP = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 20l-6-3V5l6 3m0 12l6-3m-6 3V8m6 9l6 3V7l-6-3m0 16V5m0 0L9 8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ICON_USERS = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// Server Component: os dados são buscados no servidor, com a sessão do
// usuário já resolvida via cookies — nenhuma chave sensível chega ao browser.
export default async function DashboardPage() {
  const supabase = await createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const [statsResult, insightResult, totalEmpresasResult, leadsResult] = await Promise.all([
    supabase
      .from("estatisticas_crescimento")
      .select("*, cnaes(descricao), municipios(nome)")
      // só entram no ranking combinações com variação já calculada (6 meses
      // de histórico) e um mínimo de aberturas — evita que 1 abertura isolada
      // vs. média de 0,2 vire uma variação de milhares de % no topo da lista
      .not("variacao_pct", "is", null)
      .gte("total_aberturas", 5)
      .order("variacao_pct", { ascending: false, nullsFirst: false })
      .limit(8),
    supabase
      .from("insights_ia")
      .select("*")
      .order("gerado_em", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase.from("estabelecimentos").select("*", { count: "exact", head: true }),
    supabase
      .from("estabelecimentos")
      .select(
        `cnpj, nome_fantasia, data_inicio_atividade, situacao_cadastral,
         empresas(razao_social, porte),
         cnaes(descricao),
         municipios(nome),
         leads_enriquecidos(endereco_formatado, telefone_places, website, rating_google)`,
      )
      .eq("situacao_cadastral", 2)
      .order("data_inicio_atividade", { ascending: false })
      .limit(500), // paginação simples por LIMIT no MVP; evoluir para cursor/keyset se o volume crescer
  ]);

  const stats = (statsResult.data ?? []) as unknown as EstatisticaCrescimento[];
  const insight = insightResult.data as InsightIA | null;
  const totalEmpresas = totalEmpresasResult.count ?? 0;
  const leads = (leadsResult.data ?? []) as unknown as Lead[];

  const chartData = stats.map((s) => {
    const nomeCompleto = s.cnaes?.descricao ?? `CNAE ${s.cnae_codigo}`;
    return {
      setor: truncar(nomeCompleto, 26),
      setorCompleto: nomeCompleto,
      municipio: s.municipios?.nome ?? `Município ${s.codigo_municipio}`,
      variacaoPct: s.variacao_pct ?? 0,
      totalAberturas: s.total_aberturas,
    };
  });

  return (
    <div className="min-h-screen">
      <nav className="sticky top-0 z-10 backdrop-blur bg-base-950/85 border-b border-base-800">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-mono text-xs uppercase tracking-widest text-accent">
            Startup Radar POA
          </span>
          <div className="flex items-center gap-5 text-sm text-base-400">
            <a href="#visao-geral" className="hover:text-base-50 transition-colors">Visão geral</a>
            <a href="#setores" className="hover:text-base-50 transition-colors">Setores</a>
            <a href="#leads" className="hover:text-base-50 transition-colors">Leads</a>
            <SignOutButton />
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-10 space-y-14">
        <header id="visao-geral" className="scroll-mt-20">
          <p className="text-accent font-mono text-xs uppercase tracking-widest">Grande Porto Alegre</p>
          <h1 className="text-3xl font-semibold mt-2">Onde o empreendedorismo está crescendo</h1>
          <p className="text-base-400 text-sm mt-2 max-w-2xl">
            Um raio-x da Região Metropolitana de Porto Alegre com base em dados públicos da Receita
            Federal — setores em alta, municípios cobertos e as empresas que abriram por último.
          </p>

          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
            <StatCard
              icon={ICON_BUILDING}
              label="Estabelecimentos ativos mapeados"
              value={totalEmpresas.toLocaleString("pt-BR")}
            />
            <StatCard
              icon={ICON_TREND}
              label="Setor com maior variação"
              value={stats[0]?.cnaes?.descricao ? truncar(stats[0].cnaes.descricao, 22) : "—"}
              delta={stats[0] ? formatarVariacaoPct(stats[0].variacao_pct) : undefined}
            />
            <StatCard icon={ICON_MAP} label="Municípios cobertos" value="34" />
            <StatCard icon={ICON_USERS} label="Leads carregados nesta página" value={leads.length.toLocaleString("pt-BR")} />
          </section>
        </header>

        {insight && (
          <section className="card border-accent-dim/60">
            <p className="text-accent-bright text-xs font-mono uppercase tracking-wide mb-2">
              Insight gerado por IA
            </p>
            <p className="text-base-200 leading-relaxed">{insight.conteudo}</p>
          </section>
        )}

        <section id="setores" className="scroll-mt-20">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-lg font-semibold">Setores em crescimento</h2>
            <span className="text-xs text-base-600 font-mono">variação vs. média móvel 6m</span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <GrowthChart data={chartData} />
            </div>
            <div className="card">
              <h3 className="text-sm font-medium text-base-200 mb-4">Ranking detalhado</h3>
              <ol className="space-y-3">
                {stats.slice(0, 8).map((s, i) => (
                  <li key={`${s.cnae_codigo}-${s.codigo_municipio}-${s.ano_mes}`} className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-base-600 font-mono text-xs w-4 shrink-0">{i + 1}</span>
                      <div className="min-w-0">
                        <span className="text-sm text-base-200 truncate block">
                          {s.cnaes?.descricao ?? `CNAE ${s.cnae_codigo}`}
                        </span>
                        <span className="text-xs text-base-600 truncate block">
                          {s.municipios?.nome ?? `Município ${s.codigo_municipio}`}
                        </span>
                      </div>
                    </div>
                    <span className="badge-up shrink-0">
                      {formatarVariacaoPct(s.variacao_pct)}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section id="leads" className="scroll-mt-20">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-lg font-semibold">Leads — empresas ativas na RMPA</h2>
            <span className="text-xs text-base-600 font-mono">
              últimas {leads.length.toLocaleString("pt-BR")} aberturas ativas
            </span>
          </div>
          {leadsResult.error ? (
            <p className="text-danger text-sm">Erro ao carregar leads: {leadsResult.error.message}</p>
          ) : (
            <LeadsTable leads={leads} />
          )}
        </section>

        <footer className="text-xs text-base-600 border-t border-base-800 pt-6">
          Dados: Receita Federal (CNPJ) — lote processado manualmente pelo pipeline, sem atualização automática.
        </footer>
      </main>
    </div>
  );
}
