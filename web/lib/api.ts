const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Lead {
  lead_id: string;
  nombre_cliente: string;
  telefono_e164: string;
  ciudad_canonica: string;
  canal: string;
  canales_merged: string;
  punto_venta_id: string;
  estado_gestion: string;
  fecha_registro_iso: string;
  modelo_interes_texto: string;
  sku_sugerido: string;
  marca: string | null;
  linea: string | null;
  precio_lista: number | null;
  cuota_inicial: string | null;
  cuota_inicial_monto: string | null;
  forma_pago: string | null;
  intencion: string | null;
  objecion_principal: string | null;
  pidio_cita: number | null;
  pidio_cotizacion: number | null;
  score_total: number;
  banda: "Alta" | "Media" | "Baja";
  razones: string[];
  asignado_asesor_id: string | null;
}

export interface Tablero {
  empresa: string;
  kpi: { leads: number; alta: number; media: number; baja: number; sin_tocar: number };
  por_canal: Record<string, number>;
  por_punto_venta: { punto_venta_id: string; n: number; score_promedio: number }[];
  calidad: { rechazos: number; ext_llm: number; ext_regex: number };
}

export interface Meta {
  empresas: { empresa_id: string; nombre: string }[];
  asesores: { asesor_id: string; nombre: string; punto_venta_id: string; empresa_id: string; capacidad_diaria_leads: number }[];
  puntos_venta: { punto_venta_id: string; empresa_id: string; ciudad: string | null }[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

export const api = {
  meta: (empresa?: string) => get<Meta>(`/api/meta${empresa ? `?empresa=${empresa}` : ""}`),
  tablero: (empresa: string) => get<Tablero>(`/api/tablero?empresa=${empresa}`),
  leads: (p: { empresa: string; asesor?: string; banda?: string }) => {
    const q = new URLSearchParams({ empresa: p.empresa, limite: "200" });
    if (p.asesor) q.set("asesor", p.asesor);
    if (p.banda) q.set("banda", p.banda);
    return get<{ empresa: string; n: number; leads: Lead[] }>(`/api/leads-del-dia?${q}`);
  },
};

export const EMPRESAS = [
  { id: "EMP-01", nombre: "Motos y Motores del Norte" },
  { id: "EMP-02", nombre: "Comercializadora Andina" },
  { id: "EMP-03", nombre: "Motos Caribe" },
];

export const BANDA_STYLES: Record<string, string> = {
  Alta: "bg-red-100 text-red-800 border-red-300",
  Media: "bg-amber-100 text-amber-800 border-amber-300",
  Baja: "bg-slate-100 text-slate-600 border-slate-300",
};

export function formatoPrecio(v: number | null): string {
  if (!v) return "";
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(v);
}
