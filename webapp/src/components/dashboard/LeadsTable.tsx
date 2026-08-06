"use client";

import { useMemo, useState } from "react";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type { Lead } from "@/lib/types";

interface LeadsTableProps {
  leads: Lead[];
}

const columns: ColumnDef<Lead>[] = [
  {
    header: "Empresa",
    accessorFn: (row) => row.empresas?.razao_social ?? row.nome_fantasia ?? "—",
  },
  {
    header: "Setor (CNAE)",
    accessorFn: (row) => row.cnaes?.descricao ?? "—",
  },
  {
    header: "Município",
    accessorFn: (row) => row.municipios?.nome ?? "—",
  },
  {
    header: "Aberta em",
    accessorFn: (row) => new Date(row.data_inicio_atividade).toLocaleDateString("pt-BR"),
  },
  {
    header: "Contato",
    accessorFn: (row) => row.leads_enriquecidos?.telefone_places ?? "Não enriquecido",
  },
];

function exportarCsv(leads: Lead[]) {
  const cabecalho = ["CNPJ", "Razão Social", "Setor", "Município", "Data de Abertura", "Telefone"];
  const linhas = leads.map((l) => [
    l.cnpj,
    l.empresas?.razao_social ?? "",
    l.cnaes?.descricao ?? "",
    l.municipios?.nome ?? "",
    l.data_inicio_atividade,
    l.leads_enriquecidos?.telefone_places ?? "",
  ]);
  const csv = [cabecalho, ...linhas].map((linha) => linha.join(";")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `leads_startup_radar_poa_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function LeadsTable({ leads }: LeadsTableProps) {
  const [filtro, setFiltro] = useState("");

  const table = useReactTable({
    data: leads,
    columns,
    state: { globalFilter: filtro },
    onGlobalFilterChange: setFiltro,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const contagemFiltrada = useMemo(() => table.getRowModel().rows.length, [table, filtro]);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4 gap-3">
        <input
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          placeholder="Filtrar por empresa, setor ou município..."
          className="bg-base-850 border border-base-700 rounded-md px-3 py-2 text-sm w-full max-w-sm
                     focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
        <button
          onClick={() => exportarCsv(leads)}
          className="text-sm bg-base-800 hover:bg-base-700 border border-base-700 rounded-md px-3 py-2 whitespace-nowrap"
        >
          Exportar CSV ({contagemFiltrada})
        </button>
      </div>

      <div className="overflow-auto max-h-[480px] rounded-md border border-base-800">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-base-900 z-10">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-base-700 text-base-400 text-left">
                {hg.headers.map((header) => (
                  <th key={header.id} className="py-2 px-4 font-medium first:pl-4">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-base-800 hover:bg-base-900/60">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="py-2.5 px-4 text-base-200 first:pl-4">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
