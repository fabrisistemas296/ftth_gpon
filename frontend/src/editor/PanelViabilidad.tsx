import { Aviso } from '../components/Aviso';
import { num } from './catalogo';
import type { useViabilidad } from './useViabilidad';

interface Props {
  evaluacion: ReturnType<typeof useViabilidad>;
  nombres: Record<number, string>;
  borrador?: boolean;
}

export function PanelViabilidad({ evaluacion: { datos, error, calculando }, nombres, borrador }: Props) {
  return (
    <section className="panel viabilidad" aria-label="Viabilidad de la red" aria-busy={calculando}>
      <div className="panel__cab">
        <span className="panel__tipo">Antes de simular tráfico</span>
        <h2>Viabilidad de la red</h2>
      </div>
      {borrador && <p className="texto-suave">Vista previa de los cambios sin guardar. Aplicá los cambios antes de continuar.</p>}
      {calculando && <Aviso tipo="info">Comprobando los parámetros actuales…</Aviso>}
      {error && <Aviso>{error}</Aviso>}
      {datos && (
        <>
          <Aviso tipo={datos.estado === 'viable' ? 'ok' : 'error'}>
            {datos.estado === 'viable' ? 'Red viable para simular tráfico.' : datos.estado === 'incompleta' ? 'Completá o corregí la topología.' : 'La red no es viable con estos parámetros.'}
          </Aviso>
          {datos.enlaces.length > 0 && <p className="texto-suave">{datos.cantidad_onts} ONT representadas en {datos.enlaces.length} {datos.enlaces.length === 1 ? 'recorrido' : 'recorridos'}.</p>}
          {datos.motivos.length > 0 && <ul className="problemas">{datos.motivos.map((m, i) => <li key={i} className="problemas__item problemas__item--error">{m}</li>)}</ul>}
          {datos.enlaces.map((e) => (
            <div key={e.ont_id} className="previa">
              <div className="previa__titulo">{nombres[e.ont_id] ?? `ONT/ONU ${e.ont_id}`} · {e.estado_operativo === 'operativo' ? 'Viable' : 'No viable'}</div>
              {e.cantidad_onts > 1 && <div><span>Pares fibra + ONT</span><span>{e.cantidad_onts}</span></div>}
              <div><span>Recorrido OLT–ONT</span><span>{num(e.longitud_total_km, 3)} / {datos.alcance_maximo_km} km</span></div>
              <div><span>Pérdidas</span><span>{num(e.perdida_total_db)} dB</span></div>
              <div><span>Potencia recibida</span><span>{num(e.potencia_recibida_dbm)} dBm</span></div>
              <div><span>Margen sobre sensibilidad</span><span>{num(e.margen_db)} dB</span></div>
              <div><span>Margen hasta sobrecarga</span><span>{num(e.margen_sobrecarga_db)} dB</span></div>
            </div>
          ))}
          <p className="campo__ayuda">Perfil GPON de {datos.alcance_maximo_km} km por recorrido completo. Comprobación óptica descendente según los parámetros configurados; no evalúa el enlace ascendente ni reserva de ingeniería.</p>
        </>
      )}
    </section>
  );
}
