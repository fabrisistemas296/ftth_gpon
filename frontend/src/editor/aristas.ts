import type { Edge, Node } from '@xyflow/react';
import type { Conexion } from '../api/types';

// Las conexiones no guardan qué lado del nodo usan: se elige el lado según
// la posición relativa de los componentes para que el trazo sea legible.
export function construirAristas(conexiones: Conexion[], nodes: Node[], seleccionadas: Set<string> = new Set()): Edge[] {
  const pos = new Map(nodes.map((n) => [n.id, n.position.x]));
  return conexiones.map((c) => {
    const s = String(c.componente_origen_id);
    const t = String(c.componente_destino_id);
    const haciaDerecha = (pos.get(s) ?? 0) <= (pos.get(t) ?? 0);
    return {
      id: String(c.id),
      source: s,
      target: t,
      sourceHandle: haciaDerecha ? 'der' : 'izq',
      targetHandle: haciaDerecha ? 'izq' : 'der',
      selected: seleccionadas.has(String(c.id)),
      className: 'arista',
    };
  });
}
