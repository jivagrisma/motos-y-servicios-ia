"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { api, BANDA_STYLES, EMPRESAS, formatoPrecio, type Lead, type Meta } from "@/lib/api";

const INTENCION_LABEL: Record<string, string> = {
  compra_inmediata: "Quiere comprar ya",
  agendando: "Quiere agendar visita",
  explorando_precios: "Está comparando precios",
  sin_intencion_clara: "Intención por definir",
};

const FORMA_LABEL: Record<string, string> = {
  contado: "Contado",
  credito: "Crédito",
  no_informa: "Forma de pago por definir",
};

function LeadsContent() {
  const params = useSearchParams();
  const [empresa, setEmpresa] = useState(params.get("empresa") ?? "EMP-01");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [asesor, setAsesor] = useState("");
  const [banda, setBanda] = useState("");
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState("");
  const [abierto, setAbierto] = useState<string | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
  }, []);

  useEffect(() => {
    setLeads(null);
    setError("");
    setAbierto(null);
    api.leads({ empresa, asesor: asesor || undefined, banda: banda || undefined })
      .then((r) => setLeads(r.leads))
      .catch((e) => setError(String(e.message ?? e)));
  }, [empresa, asesor, banda]);

  const asesoresEmpresa = useMemo(
    () => (meta?.asesores ?? []).filter((a) => a.empresa_id === empresa),
    [meta, empresa],
  );
  const nombreEmpresa = EMPRESAS.find((e) => e.id === empresa)?.nombre;

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-6">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Mis leads de hoy</h1>
          <p className="text-sm text-slate-500">{nombreEmpresa} · ordenados por prioridad</p>
        </div>
        <Link href={`/?empresa=${empresa}`} className="text-sm text-slate-500 underline">
          Tablero
        </Link>
      </header>

      <section className="mb-4 space-y-2 rounded-xl border bg-white p-3">
        <div className="flex flex-wrap gap-2">
          {EMPRESAS.map((e) => (
            <button
              key={e.id}
              onClick={() => setEmpresa(e.id)}
              className={`rounded-full border px-3 py-1 text-sm ${
                empresa === e.id ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 text-slate-700"
              }`}
            >
              {e.id}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={asesor}
            onChange={(e) => setAsesor(e.target.value)}
            className="rounded-lg border border-slate-400 bg-white px-3 py-1.5 text-sm text-slate-900"
          >
            <option value="">Todos los asesores</option>
            {asesoresEmpresa.map((a) => (
              <option key={a.asesor_id} value={a.asesor_id}>
                {a.nombre}
              </option>
            ))}
          </select>
          <select
            value={banda}
            onChange={(e) => setBanda(e.target.value)}
            className="rounded-lg border border-slate-400 bg-white px-3 py-1.5 text-sm text-slate-900"
          >
            <option value="">Toda prioridad</option>
            <option value="Alta">Solo Alta</option>
            <option value="Media">Solo Media</option>
            <option value="Baja">Solo Baja</option>
          </select>
          {leads && <span className="self-center text-sm text-slate-500">{leads.length} leads</span>}
        </div>
      </section>

      {error && (
        <p className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">Error: {error}</p>
      )}
      {!leads && !error && <p className="p-6 text-center text-sm text-slate-700">Cargando…</p>}

      <ul className="space-y-3">
        {leads?.map((lead) => (
          <li key={lead.lead_id} className="rounded-xl border bg-white shadow-sm">
            <button
              onClick={() => setAbierto(abierto === lead.lead_id ? null : lead.lead_id)}
              className="flex w-full items-start gap-3 p-4 text-left"
            >
              <div
                className={`mt-0.5 flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-lg border text-center ${BANDA_STYLES[lead.banda]}`}
              >
                <span className="text-lg leading-none font-bold">{lead.score_total}</span>
                <span className="text-[10px] uppercase">{lead.banda}</span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{lead.nombre_cliente || "Sin nombre"}</p>
                <p className="truncate text-sm font-medium text-slate-800">
                  {lead.modelo_interes_texto || "Modelo por definir"}
                  {lead.precio_lista ? ` · ${formatoPrecio(lead.precio_lista)}` : ""}
                </p>
                <p className="mt-0.5 text-xs text-slate-900">
                  {lead.ciudad_canonica || "Ciudad s/d"} · {lead.canal} · {lead.punto_venta_id}
                </p>
                {lead.razones.length > 0 && (
                  <p className="mt-1 truncate text-xs font-medium text-emerald-700">
                    ★ {lead.razones.join(" · ")}
                  </p>
                )}
              </div>
            </button>

            {abierto === lead.lead_id && (
              <div className="border-t px-4 py-3 text-sm">
                <p className="mb-2">
                  <a href={`tel:${lead.telefono_e164}`} className="font-semibold text-blue-700 underline">
                    {lead.telefono_e164 || "sin teléfono"}
                  </a>{" "}
                  · estado: {lead.estado_gestion}
                </p>
                {lead.intencion && (
                  <p className="text-slate-700">
                    <strong>Intención:</strong> {INTENCION_LABEL[lead.intencion] ?? lead.intencion}
                  </p>
                )}
                <p className="text-slate-700">
                  <strong>Forma de pago:</strong> {FORMA_LABEL[lead.forma_pago ?? "no_informa"]}
                  {lead.cuota_inicial === "SI" && lead.cuota_inicial_monto && ` · cuota inicial: ${lead.cuota_inicial_monto}`}
                </p>
                {lead.objecion_principal && (
                  <p className="text-slate-700">
                    <strong>Objeción:</strong> {lead.objecion_principal}
                  </p>
                )}
                <p className="text-slate-700">
                  <strong>Pidió cita:</strong> {lead.pidio_cita ? "Sí" : "No"} · <strong>cotización:</strong>{" "}
                  {lead.pidio_cotizacion ? "Sí" : "No"}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Registrado {lead.fecha_registro_iso} · lead {lead.lead_id}
                  {lead.asignado_asesor_id ? ` · asignado a ${lead.asignado_asesor_id}` : ""}
                </p>
              </div>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<p className="p-6 text-center text-sm text-slate-700">Cargando…</p>}>
      <LeadsContent />
    </Suspense>
  );
}
