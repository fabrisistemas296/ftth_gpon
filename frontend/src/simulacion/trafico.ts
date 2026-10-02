import type { Componente, TipoConsumo } from '../api/types';

// Deben coincidir con app/core/constantes.py. En el frontend solo se usan
// para mostrar la demanda estimada antes de ejecutar; los resultados
// oficiales los calcula siempre el backend.
export const CAPACIDAD_DOWNSTREAM_MBPS = 2488;
export const UMBRAL_CONGESTION_PCT = 85;

export const CONSUMOS: { id: TipoConsumo; nombre: string; mbps: number; detalle: string }[] = [
  { id: 'web', nombre: 'Navegación web', mbps: 1.5, detalle: 'Páginas, redes sociales, correo' },
  { id: 'streaming', nombre: 'Streaming', mbps: 15, detalle: 'Video HD/4K bajo demanda' },
  { id: 'videoconferencia', nombre: 'Videoconferencia', mbps: 3, detalle: 'Clases y reuniones en línea' },
  { id: 'descarga', nombre: 'Descarga de archivos', mbps: 50, detalle: 'Tiende a ocupar todo el ancho de banda' },
];

export const consumo = (id: TipoConsumo) => CONSUMOS.find((c) => c.id === id)!;

export const fmt = (v: number, dec = 2) =>
  v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

// Si todas las ONT/ONU comparten sensibilidad y sobrecarga, el rango del
// receptor del peor caso es conocido aunque el backend no informe qué ONT es.
export function rangoReceptorComun(componentes: Componente[]) {
  const onts = componentes.filter((c) => c.tipo === 'ONT_ONU');
  if (!onts.length) return null;
  const s = onts[0].sensibilidad_min_dbm;
  const o = onts[0].potencia_sobrecarga_dbm;
  if (s == null || o == null) return null;
  const iguales = onts.every((c) => c.sensibilidad_min_dbm === s && c.potencia_sobrecarga_dbm === o);
  return iguales ? { sensibilidad: s, sobrecarga: o } : null;
}
