import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { Componente } from '../api/types';
import { resumenNodo } from './catalogo';
import { IconoComponente } from './IconoComponente';

export type DatosNodo = { componente: Componente; nombre: string };
export type NodoFlow = Node<DatosNodo, 'componente'>;

export function NodoComponente({ data, selected }: NodeProps<NodoFlow>) {
  const { componente: c, nombre } = data;
  return (
    <div className={`nodo nodo--${c.tipo.toLowerCase()}${selected ? ' nodo--sel' : ''}`}>
      <Handle type="source" position={Position.Left} id="izq" />
      <IconoComponente tipo={c.tipo} />
      <div className="nodo__texto">
        <span className="nodo__nombre">{nombre}</span>
        <span className="nodo__dato">{resumenNodo(c)}</span>
      </div>
      <Handle type="source" position={Position.Right} id="der" />
    </div>
  );
}
