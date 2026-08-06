export interface EstatisticaCrescimento {
  cnae_codigo: string;
  codigo_municipio: string;
  ano_mes: string;
  total_aberturas: number;
  variacao_pct: number | null;
  cnaes: { descricao: string } | null;
  municipios: { nome: string } | null;
}

export interface Lead {
  cnpj: string;
  nome_fantasia: string | null;
  data_inicio_atividade: string;
  situacao_cadastral: number;
  empresas: { razao_social: string; porte: number | null } | null;
  cnaes: { descricao: string } | null;
  municipios: { nome: string } | null;
  leads_enriquecidos: {
    endereco_formatado: string | null;
    telefone_places: string | null;
    website: string | null;
    rating_google: number | null;
  } | null;
}

export interface InsightIA {
  id: number;
  titulo: string;
  conteudo: string;
  gerado_em: string;
}
