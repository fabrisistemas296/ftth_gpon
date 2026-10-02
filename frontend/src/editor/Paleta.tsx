import type { TipoComponente } from '../api/types';
import { DESCRIPCION, ETIQUETA } from './catalogo';
import { IconoComponente } from './IconoComponente';

export const TIPO_DND = 'application/ftth-tipo';
const TIPOS: TipoComponente[] = ['OLT', 'FIBRA', 'SPLITTER', 'ONT_ONU'];

export function Paleta({ onAgregar, deshabilitado }: { onAgregar: (tipo: TipoComponente) => void; deshabilitado?: boolean }) {
  return (
    <aside className="paleta" aria-label="Componentes">
      <h2>Componentes</h2>
      <p>Arrastrá un componente al lienzo o hacé clic para agregarlo. Conectalos uniendo sus puntos laterales.</p>
      {TIPOS.map((t) => (
        <button
          key={t}
          type="button"
          className="paleta__item"
          draggable={!deshabilitado}
          disabled={deshabilitado}
          onDragStart={(e) => {
            e.dataTransfer.setData(TIPO_DND, t);
            e.dataTransfer.effectAllowed = 'move';
          }}
          onClick={() => onAgregar(t)}
        >
          <IconoComponente tipo={t} />
          <span>
            <strong>{ETIQUETA[t]}</strong>
            <small>{DESCRIPCION[t]}</small>
          </span>
        </button>
      ))}
      <div className="paleta__ayuda">
        <h3>Atajos</h3>
        <p><kbd>Supr</kbd> elimina lo seleccionado</p>
        <p><kbd>Shift</kbd> + arrastrar selecciona varios</p>
        <p>Rueda del mouse para acercar o alejar</p>
      </div>
    </aside>
  );
}
