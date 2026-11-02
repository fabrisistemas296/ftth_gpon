import type { Componente, Conexion } from '../api/types';
import { esTerminal } from './catalogo';

function erroresCapacidad(componentes: Componente[], conexiones: Conexion[]): string[] {
  const porId = new Map(componentes.map((c) => [c.id, c]));
  const vecinos = new Map(componentes.map((c) => [c.id, [] as number[]]));
  conexiones.forEach((c) => {
    vecinos.get(c.componente_origen_id)?.push(c.componente_destino_id);
    vecinos.get(c.componente_destino_id)?.push(c.componente_origen_id);
  });
  const olts = componentes.filter((c) => c.tipo === 'OLT');
  const padres = new Map<number, number | null>();
  if (olts.length === 1) {
    padres.set(olts[0].id, null);
    const cola = [olts[0].id];
    for (let i = 0; i < cola.length; i++) {
      const actual = cola[i];
      for (const v of vecinos.get(actual) ?? []) {
        if (!padres.has(v)) { padres.set(v, actual); cola.push(v); }
      }
    }
  }
  return componentes.filter((c) => c.tipo === 'SPLITTER').flatMap((c) => {
    const salidas = (vecinos.get(c.id) ?? []).filter((v) => padres.has(c.id)
      ? v !== padres.get(c.id) : esTerminal(porId.get(v)!.tipo));
    const ocupadas = salidas.reduce((n, v) => n + (porId.get(v)?.cantidad ?? 1), 0);
    const capacidad = Number(c.relacion_division?.split(':')[1]);
    return ocupadas > capacidad ? [`El splitter ${c.id} (${c.relacion_division}) tiene ${capacidad} salidas y las conexiones requieren ${ocupadas}. Cada par del lote ocupa una salida.`] : [];
  });
}

// Reglas de conexión entre componentes (criterio de aceptación de RF-07).
export function validarConexion(
  origen: Componente | undefined,
  destino: Componente | undefined,
  conexiones: Conexion[],
  componentes: Componente[] = [],
): string | null {
  if (!origen || !destino) return 'No se encontró uno de los componentes.';
  if (origen.id === destino.id) return 'Un componente no puede conectarse consigo mismo.';
  const existe = conexiones.some(
    (c) =>
      (c.componente_origen_id === origen.id && c.componente_destino_id === destino.id) ||
      (c.componente_origen_id === destino.id && c.componente_destino_id === origen.id),
  );
  if (existe) return 'Esos componentes ya están conectados.';
  if (esTerminal(origen.tipo) && esTerminal(destino.tipo)) return 'Una ONT o lote terminal no puede conectarse a otra ONT o lote terminal.';
  if (origen.tipo === 'OLT' && destino.tipo === 'OLT') return 'Dos OLT no pueden conectarse entre sí.';
  for (const ont of [origen, destino].filter((c) => esTerminal(c.tipo))) {
    const enlaces = conexiones.filter((c) => c.componente_origen_id === ont.id || c.componente_destino_id === ont.id);
    if (enlaces.length >= 1) return 'Cada ONT o lote fibra + ONT admite un solo enlace hacia la red.';
  }
  for (const fibra of [origen, destino].filter((c) => c.tipo === 'FIBRA')) {
    const enlaces = conexiones.filter((c) => c.componente_origen_id === fibra.id || c.componente_destino_id === fibra.id);
    if (enlaces.length >= 2) return 'Cada fibra tiene dos extremos; usá un splitter para dividir la señal.';
  }
  for (const [c, otro] of [[origen, destino], [destino, origen]]) {
    if (c.tipo === 'LOTE_FIBRA_ONT' && c.cantidad > 1 && otro.tipo !== 'SPLITTER')
      return 'Un lote de varios pares fibra + ONT debe conectarse a un splitter.';
  }
  const alcanzados = new Set([origen.id]);
  let cambio = true;
  while (cambio) {
    cambio = false;
    for (const c of conexiones) {
      if (alcanzados.has(c.componente_origen_id) && !alcanzados.has(c.componente_destino_id)) {
        alcanzados.add(c.componente_destino_id); cambio = true;
      }
      if (alcanzados.has(c.componente_destino_id) && !alcanzados.has(c.componente_origen_id)) {
        alcanzados.add(c.componente_origen_id); cambio = true;
      }
    }
  }
  if (alcanzados.has(destino.id)) return 'Esta conexión formaría un ciclo en la red GPON.';
  const todos = [...new Map([...componentes, origen, destino].map((c) => [c.id, c])).values()];
  const propuesta: Conexion = { id: -1, topologia_id: origen.topologia_id, componente_origen_id: origen.id, componente_destino_id: destino.id };
  return erroresCapacidad(todos, [...conexiones, propuesta])[0] ?? null;
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
  const onts = componentes.filter((c) => esTerminal(c.tipo));

  if (olts.length === 0) problemas.push({ nivel: 'error', texto: 'Agregá una OLT: es el origen de la señal.' });
  if (olts.length > 1) problemas.push({ nivel: 'error', texto: `La topología debe tener una sola OLT (hay ${olts.length}).` });
  if (onts.length === 0) problemas.push({ nivel: 'error', texto: 'Agregá al menos una ONT/ONU.' });

  const vecinos = new Map<number, number[]>();
  componentes.forEach((c) => vecinos.set(c.id, []));
  conexiones.forEach((c) => {
    vecinos.get(c.componente_origen_id)?.push(c.componente_destino_id);
    vecinos.get(c.componente_destino_id)?.push(c.componente_origen_id);
  });

  componentes.forEach((c) => {
    const adyacentes = vecinos.get(c.id) ?? [];
    if (c.tipo === 'FIBRA' && adyacentes.length !== 2)
      problemas.push({ nivel: 'error', texto: `${nombres[c.id]} debe tener sus dos extremos conectados, sin conexiones adicionales.` });
    if (esTerminal(c.tipo) && adyacentes.length > 1)
      problemas.push({ nivel: 'error', texto: `${nombres[c.id]} admite una única conexión a la red.` });
    if (c.tipo === 'LOTE_FIBRA_ONT' && c.cantidad > 1 && adyacentes.some((v) => componentes.find((p) => p.id === v)?.tipo !== 'SPLITTER'))
      problemas.push({ nivel: 'error', texto: `${nombres[c.id]} necesita un splitter con ${c.cantidad} salidas disponibles.` });
  });
  erroresCapacidad(componentes, conexiones).forEach((texto) => problemas.push({ nivel: 'error', texto }));

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
      .filter((c) => !esTerminal(c.tipo) && c.tipo !== 'OLT' && !alcanzables.has(c.id))
      .forEach((c) => problemas.push({ nivel: 'error', texto: `${nombres[c.id]} no está conectado a la red de la OLT.` }));
  }
  return problemas;
}
