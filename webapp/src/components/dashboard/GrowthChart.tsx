"use client";

import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatarVariacaoPct } from "@/lib/format";

export interface GrowthChartDatum {
  setor: string;
  setorCompleto: string;
  municipio: string;
  variacaoPct: number;
  totalAberturas: number;
}

interface GrowthChartProps {
  data: GrowthChartDatum[];
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: GrowthChartDatum }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-base-850 border border-base-700 rounded-lg px-3 py-2 text-sm shadow-lg max-w-xs">
      <p className="text-base-50 font-medium leading-snug">{d.setorCompleto}</p>
      <p className="text-base-400 text-xs mt-0.5">{d.municipio}</p>
      <div className="flex items-center justify-between gap-6 mt-2">
        <span className="text-base-400 text-xs">Variação vs. média 6m</span>
        <span className={d.variacaoPct >= 0 ? "text-accent-bright font-mono" : "text-danger font-mono"}>
          {formatarVariacaoPct(d.variacaoPct)}
        </span>
      </div>
      <div className="flex items-center justify-between gap-6">
        <span className="text-base-400 text-xs">Aberturas no mês</span>
        <span className="text-base-200 font-mono">{d.totalAberturas.toLocaleString("pt-BR")}</span>
      </div>
    </div>
  );
}

/**
 * Ranking horizontal dos setores (CNAEs) com maior variação percentual de
 * aberturas na RMPA. Barra horizontal escolhida deliberadamente sobre
 * vertical: nomes de setor são longos e não cabem em rótulos de eixo X sem
 * rotação (rotação de texto prejudica leitura rápida em um dashboard).
 */
export function GrowthChart({ data }: GrowthChartProps) {
  const maiorValor = Math.max(1, ...data.map((d) => Math.abs(d.variacaoPct)));

  return (
    <div className="card h-[420px]">
      <div className="flex items-baseline justify-between mb-4">
        <h3 className="text-sm font-medium text-base-200">
          Setores com maior crescimento — RMPA
        </h3>
        <span className="text-xs text-base-600 font-mono">% vs. média móvel 6m</span>
      </div>
      <ResponsiveContainer width="100%" height="88%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 4 }} barCategoryGap={10}>
          <CartesianGrid strokeDasharray="3 3" stroke="#272C38" horizontal={false} />
          <XAxis
            type="number"
            stroke="#7B8394"
            fontSize={12}
            unit="%"
            domain={[0, Math.ceil(maiorValor * 1.15)]}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="setor"
            stroke="#7B8394"
            fontSize={12}
            width={168}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip cursor={{ fill: "#1C2029" }} content={<CustomTooltip />} />
          <Bar dataKey="variacaoPct" radius={[0, 4, 4, 0]} maxBarSize={22}>
            {data.map((d, i) => (
              <Cell key={i} fill={i === 0 ? "#5FE8AC" : "#3ECF8E"} fillOpacity={i === 0 ? 1 : 0.75} />
            ))}
            <LabelList
              dataKey="variacaoPct"
              position="right"
              formatter={(v: number) => formatarVariacaoPct(v)}
              fill="#C4C9D4"
              fontSize={12}
              fontFamily="var(--font-jetbrains)"
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
