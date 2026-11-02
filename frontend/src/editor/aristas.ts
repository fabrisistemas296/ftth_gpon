import type { Edge, Node } from '@xyflow/react';
import type { Componente, Conexion } from '../api/types';

// Las conexiones no guardan qué lado del nodo usan: se elige el lado según
// la posición relativa de los componentes para que el trazo sea legible.
export function construirAristas(conexiones: Conexion[], nodes: Node[], seleccionadas: Set<string> = new Set()): Edge[] {
  const pos = new Map(nodes.map((n) => [n.id, n.position.x]));
  const componentes = new Map(nodes.map((n) => [n.id, (n.data as { componente?: Componente }).componente]));
  return conexiones.map((c) => {
    const s = String(c.componente_origen_id);
    const t = String(c.componente_destino_id);
    const haciaDerecha = (pos.get(s) ?? 0) <= (pos.get(t) ?? 0);
    const lote = [componentes.get(s), componentes.get(t)].find((c) => c?.tipo === 'LOTE_FIBRA_ONT');
    return {
      id: String(c.id),
      source: s,
      target: t,
      sourceHandle: haciaDerecha ? 'der' : 'izq',
      targetHandle: haciaDerecha ? 'izq' : 'der',
      selected: seleccionadas.has(String(c.id)),
      className: 'arista',
      label: lote ? `${lote.cantidad} ${lote.cantidad === 1 ? 'par' : 'pares'}` : undefined,
    };
  });
}
