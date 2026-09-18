"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, EMPRESAS, type Tablero } from "@/lib/api";

export default function TableroPage() {
  const [empresa, setEmpresa] = useState("EMP-01");
  const [data, setData] = useState<Tablero | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    setError("");
    api.tablero(empresa).then(setData).catch((e) => setError(String(e.message ?? e)));
  }, [empresa]);

  const nombre = EMPRESAS.find((e) => e.id === empresa)?.nombre;

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">Tablero comercial</h1>
          <p className="text-sm text-slate-500">{nombre}</p>
        </div>
        <nav className="flex items-center gap-2">
          <Link
            href={`/leads?empresa=${empresa}`}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Mis leads de hoy →
          </Link>
        </nav>
      </header>

      <section className="mb-6 flex flex-wrap gap-2">
        {EMPRESAS.map((e) => (
          <button
            key={e.id}
            onClick={() => setEmpresa(e.id)}
            className={`rounded-full border px-4 py-1.5 text-sm ${
              empresa === e.id ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white text-slate-700"
            }`}
          >
            {e.nombre}
          </button>
        ))}
      </section>

      {error && (
        <p className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">
          No se pudo conectar al API: {error}
        </p>
      )}

      {data && (
        <>
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi label="Leads activos" valor={data.kpi.leads} />
            <Kpi label="Prioridad Alta" valor={data.kpi.alta} color="text-red-700" />
            <Kpi label="Sin tocar aún" valor={data.kpi.sin_tocar} color="text-amber-700" />
            <Kpi label="Prioridad Baja" valor={data.kpi.baja} color="text-slate-500" />
          </section>

          <section className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-900">Leads por canal</h2>
              <ul className="space-y-2">
                {Object.entries(data.por_canal).map(([canal, n]) => (
                  <li key={canal} className="flex items-center gap-2 text-sm">
                    <span className="w-32 shrink-0">{canal}</span>
                    <div className="h-2 flex-1 rounded bg-slate-100">
                      <div className="h-2 rounded bg-slate-700" style={{ width: `${(n / data.kpi.leads) * 100}%` }} />
                    </div>
                    <span className="w-8 text-right tabular-nums">{n}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl border bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-900">Por punto de venta</h2>
              <ul className="max-h-48 space-y-1 overflow-auto text-sm">
                {data.por_punto_venta.map((pv) => (
                  <li key={pv.punto_venta_id} className="flex justify-between">
                    <span>{pv.punto_venta_id}</span>
                    <span className="text-slate-900">
                      {pv.n} leads · prioridad media {pv.score_promedio}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="mt-4 rounded-xl border bg-white p-4 text-sm text-slate-600">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Calidad de datos</h2>
            <p>
              Conversaciones leídas con IA: <strong>{data.calidad.ext_llm}</strong> · con método
              alternativo: <strong>{data.calidad.ext_regex}</strong> · registros rechazados por
              datos inválidos: <strong>{data.calidad.rechazos}</strong>
            </p>
          </section>
        </>
      )}
    </main>
  );
}

function Kpi({ label, valor, color = "text-slate-900" }: { label: string; valor: number; color?: string }) {
  return (
    <div className="rounded-xl border bg-white p-4">
      <p className="text-xs text-slate-900">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>{valor}</p>
    </div>
  );
}
