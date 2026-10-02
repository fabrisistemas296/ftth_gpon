import type { Componente, TipoComponente } from '../api/types';
import type { ComponenteInput } from '../api/endpoints';

// Constantes de ingeniería: deben coincidir con app/core/constantes.py del
// backend. Se usan solo para mostrar una vista previa de pérdidas; el cálculo
// oficial lo hace siempre el servidor.
export const PERDIDA_CONECTOR_DB = 0.4;
export const PERDIDA_EMPALME_DB = 0.1;
export const PERDIDAS_SPLITTER_DB: Record<string, number> = {
  '1:2': 3.5, '1:4': 7.0, '1:8': 10.5, '1:16': 14.0, '1:32': 17.5, '1:64': 21.0,
};
export const RELACIONES = Object.keys(PERDIDAS_SPLITTER_DB);
export const CLASES_POTENCIA = ['B+', 'C+'] as const;

export const ETIQUETA: Record<TipoComponente, string> = {
  OLT: 'OLT',
  FIBRA: 'Fibra',
  SPLITTER: 'Splitter',
  ONT_ONU: 'ONT/ONU',
};

export const DESCRIPCION: Record<TipoComponente, string> = {
  OLT: 'Terminal de línea',
  FIBRA: 'Enlace de fibra óptica',
  SPLITTER: 'Divisor óptico pasivo',
  ONT_ONU: 'Terminal del usuario',
};

// Valores iniciales al agregar un componente (el backend exige los campos
// obligatorios de cada tipo).
export const VALORES_INICIALES: Record<TipoComponente, Partial<Componente>> = {
  OLT: { potencia_tx_dbm: 5, clase_potencia: 'B+' },
  FIBRA: { longitud_km: 1, atenuacion_db_km: 0.28, cantidad_conectores: 2, cantidad_empalmes: 0 },
  SPLITTER: { relacion_division: '1:8' },
  ONT_ONU: { sensibilidad_min_dbm: -28, potencia_sobrecarga_dbm: -8 },
};

const CAMPOS: (keyof ComponenteInput)[] = [
  'potencia_tx_dbm', 'clase_potencia', 'longitud_km', 'atenuacion_db_km', 'cantidad_conectores',
  'cantidad_empalmes', 'relacion_division', 'sensibilidad_min_dbm', 'potencia_sobrecarga_dbm',
];

export function componenteVacio(topologia_id: number, tipo: TipoComponente, x: number, y: number): ComponenteInput {
  const base = Object.fromEntries(CAMPOS.map((c) => [c, null])) as unknown as ComponenteInput;
  return { ...base, ...VALORES_INICIALES[tipo], topologia_id, tipo, posicion_x: Math.round(x), posicion_y: Math.round(y) };
}

export function aInput(c: Componente): ComponenteInput {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { id: _id, ...resto } = c;
  return { ...resto, posicion_x: Math.round(c.posicion_x), posicion_y: Math.round(c.posicion_y) };
}

export function perdidaFibra(c: Pick<Componente, 'longitud_km' | 'atenuacion_db_km' | 'cantidad_conectores' | 'cantidad_empalmes'>) {
  const fibra = (c.atenuacion_db_km ?? 0) * (c.longitud_km ?? 0);
  const conectores = (c.cantidad_conectores ?? 0) * PERDIDA_CONECTOR_DB;
  const empalmes = (c.cantidad_empalmes ?? 0) * PERDIDA_EMPALME_DB;
  return { fibra, conectores, empalmes, total: fibra + conectores + empalmes };
}

export function perdidaComponente(c: Componente): number {
  if (c.tipo === 'FIBRA') return perdidaFibra(c).total;
  if (c.tipo === 'SPLITTER') return PERDIDAS_SPLITTER_DB[c.relacion_division ?? ''] ?? 0;
  return 0;
}

export const num = (v: number, dec = 2) =>
  v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

// Resumen corto que se muestra dentro de cada nodo del lienzo.
export function resumenNodo(c: Componente): string {
  switch (c.tipo) {
    case 'OLT':
      return `${c.clase_potencia ?? '—'} · ${c.potencia_tx_dbm != null ? `${num(c.potencia_tx_dbm)} dBm` : 'sin potencia'}`;
    case 'FIBRA':
      return `${num(c.longitud_km ?? 0, c.longitud_km != null && c.longitud_km % 1 ? 1 : 0)} km · ${num(perdidaFibra(c).total)} dB`;
    case 'SPLITTER':
      return `${c.relacion_division ?? '—'} · ${num(perdidaComponente(c), 1)} dB`;
    case 'ONT_ONU':
      return `${num(c.sensibilidad_min_dbm ?? 0, 0)} a ${num(c.potencia_sobrecarga_dbm ?? 0, 0)} dBm`;
  }
}

// Nombres legibles: OLT, Fibra 1, Fibra 2, Splitter 1, ONT-1…
export function nombresComponentes(componentes: Componente[]): Record<number, string> {
  const contador: Record<string, number> = {};
  const totales: Record<string, number> = {};
  componentes.forEach((c) => (totales[c.tipo] = (totales[c.tipo] ?? 0) + 1));
  const nombres: Record<number, string> = {};
  [...componentes].sort((a, b) => a.id - b.id).forEach((c) => {
    contador[c.tipo] = (contador[c.tipo] ?? 0) + 1;
    const n = contador[c.tipo];
    if (c.tipo === 'ONT_ONU') nombres[c.id] = `ONT-${n}`;
    else if (totales[c.tipo] === 1) nombres[c.id] = ETIQUETA[c.tipo];
    else nombres[c.id] = `${ETIQUETA[c.tipo]} ${n}`;
  });
  return nombres;
}
