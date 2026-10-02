import type { Componente, Conexion } from '../api/types';

// Reglas de conexión entre componentes (criterio de aceptación de RF-07).
export function validarConexion(
  origen: Componente | undefined,
  destino: Componente | undefined,
  conexiones: Conexion[],
): string | null {
  if (!origen || !destino) return 'No se encontró uno de los componentes.';
  if (origen.id === destino.id) return 'Un componente no puede conectarse consigo mismo.';
  const existe = conexiones.some(
    (c) =>
      (c.componente_origen_id === origen.id && c.componente_destino_id === destino.id) ||
      (c.componente_origen_id === destino.id && c.componente_destino_id === origen.id),
  );
  if (existe) return 'Esos componentes ya están conectados.';
  if (origen.tipo === 'ONT_ONU' && destino.tipo === 'ONT_ONU') return 'Una ONT/ONU no puede conectarse a otra ONT/ONU.';
  if (origen.tipo === 'OLT' && destino.tipo === 'OLT') return 'Dos OLT no pueden conectarse entre sí.';
  for (const ont of [origen, destino].filter((c) => c.tipo === 'ONT_ONU')) {
    const enlaces = conexiones.filter((c) => c.componente_origen_id === ont.id || c.componente_destino_id === ont.id);
    if (enlaces.length >= 1) return 'Cada ONT/ONU admite un solo enlace hacia la red.';
  }
  return null;
}

export interface Problema {
  nivel: 'error' | 'aviso';
  texto: string;
}

// Revisión estructural previa a simular: replica las condiciones que el
// motor de cálculo del backend exige para aceptar la topología.
export function revisarTopologia(componentes: Componente[], conexiones: Conexion[], nombres: Record<number, string>): Problema[] {
  const problemas: Problema[] = [];
  const olts = componentes.filter((c) => c.tipo === 'OLT');
  const onts = componentes.filter((c) => c.tipo === 'ONT_ONU');

  if (olts.length === 0) problemas.push({ nivel: 'error', texto: 'Agregá una OLT: es el origen de la señal.' });
  if (olts.length > 1) problemas.push({ nivel: 'error', texto: `La topología debe tener una sola OLT (hay ${olts.length}).` });
  if (onts.length === 0) problemas.push({ nivel: 'error', texto: 'Agregá al menos una ONT/ONU.' });

  const vecinos = new Map<number, number[]>();
  componentes.forEach((c) => vecinos.set(c.id, []));
  conexiones.forEach((c) => {
    vecinos.get(c.componente_origen_id)?.push(c.componente_destino_id);
    vecinos.get(c.componente_destino_id)?.push(c.componente_origen_id);
  });

  if (olts.length === 1) {
    const alcanzables = new Set<number>([olts[0].id]);
    const cola = [olts[0].id];
    while (cola.length) {
      const actual = cola.shift()!;
      for (const v of vecinos.get(actual) ?? []) {
        if (!alcanzables.has(v)) {
          alcanzables.add(v);
          cola.push(v);
        }
      }
    }
    onts
      .filter((o) => !alcanzables.has(o.id))
      .forEach((o) => problemas.push({ nivel: 'error', texto: `${nombres[o.id]} no está conectada a la OLT.` }));
    componentes
      .filter((c) => c.tipo !== 'ONT_ONU' && c.tipo !== 'OLT' && !alcanzables.has(c.id))
      .forEach((c) => problemas.push({ nivel: 'aviso', texto: `${nombres[c.id]} no está conectado a la red de la OLT.` }));
  }
  return problemas;
}
