import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BarraSuperior } from '../components/BarraSuperior';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { escenariosApi, proyectosApi, simulacionesApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Escenario, ProyectoDetalle } from '../api/types';
import { CAPACIDAD_DOWNSTREAM_MBPS, UMBRAL_CONGESTION_PCT, consumo, fmt, rangoReceptorComun } from '../simulacion/trafico';
import { formatoFecha } from '../utils';
import { useAuth } from '../auth/AuthContext';

const msg = (e: unknown, def: string) => (e instanceof ApiError ? e.message : def);

// Escala de potencia para el gráfico del receptor (dBm).
const ESCALA_MIN = -36;
const ESCALA_MAX = 0;
const pct = (dbm: number) => Math.max(0, Math.min(100, ((dbm - ESCALA_MIN) / (ESCALA_MAX - ESCALA_MIN)) * 100));

export function Resultados() {
  const { id, simId } = useParams();
  const proyectoId = Number(id);
  const simulacionId = Number(simId);
  const { usuario } = useAuth();
  // El profesor ve los resultados en modo lectura (sin recalcular ni crear simulaciones).
  const lectura = usuario?.rol === 'profesor';
  const base = lectura ? `/profesor/proyectos/${proyectoId}` : `/proyectos/${proyectoId}`;

  const [detalle, setDetalle] = useState<ProyectoDetalle | null>(null);
  const [escenarios, setEscenarios] = useState<Escenario[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recalculando, setRecalculando] = useState(false);
  const [errorCalculo, setErrorCalculo] = useState<string | null>(null);
  const [recalculado, setRecalculado] = useState(false);

  const cargar = useCallback(async () => {
    const d = await proyectosApi.detalle(proyectoId);
    setDetalle(d);
  }, [proyectoId]);

  useEffect(() => {
    (async () => {
      try {
        await cargar();
      } catch (e) {
        setError(msg(e, 'No se pudo cargar la simulación.'));
      }
      escenariosApi.listar().then(setEscenarios).catch(() => undefined);
      setCargando(false);
    })();
  }, [cargar]);

  const sim = detalle?.simulaciones.find((s) => s.id === simulacionId);
  const rango = useMemo(() => rangoReceptorComun(detalle?.topologia?.componentes ?? []), [detalle]);

  const recalcular = async () => {
    setRecalculando(true);
    setErrorCalculo(null);
    setRecalculado(false);
    try {
      await simulacionesApi.calcular(simulacionId);
      await cargar();
      setRecalculado(true);
    } catch (e) {
      setErrorCalculo(msg(e, 'No se pudo recalcular la simulación.'));
    } finally {
      setRecalculando(false);
    }
  };

  const izquierda = (
    <>
      <Link to={base} className="topbar__volver">{lectura ? '← Volver al proyecto' : '← Volver a la topología'}</Link>
      <span className="topbar__sep" aria-hidden="true" />
      <span className="topbar__marca topbar__titulo">{detalle?.nombre ?? 'Proyecto'}</span>
    </>
  );

  if (cargando) {
    return (
      <div className="pagina">
        <BarraSuperior izquierda={izquierda} />
        <Cargando texto="Cargando resultados" pantallaCompleta />
      </div>
    );
  }

  if (error || !detalle || !sim) {
    return (
      <div className="pagina">
        <BarraSuperior izquierda={izquierda} />
        <main className="contenedor">
          <div className="vacio">
            <h2>No se encontró la simulación</h2>
            <p>{error ?? 'La simulación no existe o no pertenece a este proyecto.'}</p>
            <Link className="btn btn--secundario" to={lectura ? base : `${base}/simulacion`}>{lectura ? 'Volver al proyecto' : 'Ir a simulaciones'}</Link>
          </div>
        </main>
      </div>
    );
  }

  const ro = sim.resultado_optico;
  const rt = sim.resultado_trafico;
  const esc = escenarios.find((e) => e.id === sim.escenario_id);
  const perfil = consumo(sim.tipo_consumo);
  const operativo = ro?.estado_operativo === 'operativo';
  const margen = ro && rango ? ro.potencia_recibida_dbm - rango.sensibilidad : null;
  const congestion = !!rt?.congestion;

  // Explicación en lenguaje simple de lo que muestran los resultados.
  let lecturaOptica = '';
  if (ro) {
    if (operativo) {
      lecturaOptica = margen != null
        ? `El enlace más exigido llega con ${fmt(ro.potencia_recibida_dbm)} dBm, ${fmt(margen)} dB por encima de la sensibilidad mínima: todas las ONT/ONU reciben señal suficiente.`
        : `El enlace más exigido llega con ${fmt(ro.potencia_recibida_dbm)} dBm, dentro del rango de su receptor: todas las ONT/ONU reciben señal suficiente.`;
    } else if (rango && ro.potencia_recibida_dbm > rango.sobrecarga) {
      lecturaOptica = `Llega demasiada potencia (${fmt(ro.potencia_recibida_dbm)} dBm) y el receptor se satura. Agregá atenuación: un tramo de fibra más largo o una relación de división mayor.`;
    } else {
      lecturaOptica = `Al menos una ONT/ONU recibe ${fmt(ro.potencia_recibida_dbm)} dBm, por debajo de lo que su receptor puede detectar. Reducí las pérdidas: menos división en los splitters, tramos más cortos, menos conectores, o una OLT de clase C+.`;
    }
  }
  const lecturaTrafico = rt
    ? `La demanda de ${sim.cantidad_usuarios} usuarios con consumo de ${perfil.nombre.toLowerCase()} (${fmt(perfil.mbps, perfil.mbps % 1 ? 1 : 0)} Mbps cada uno) ocupa el ${fmt(rt.utilizacion_pct, 1)} % de la capacidad descendente del puerto PON.` +
      (congestion
        ? ` Supera el umbral de ${UMBRAL_CONGESTION_PCT} %: reducí la cantidad de usuarios por puerto o repartilos en más puertos PON.`
        : ' Queda por debajo del umbral de congestión.')
    : '';

  return (
    <div className="pagina">
      <BarraSuperior izquierda={izquierda} />
      <main className="contenedor contenedor--ancho">
        <div className="encabezado">
          <div>
            <h1>Resultados de la simulación</h1>
            <p>
              {esc?.nombre ?? 'Sin escenario'} · {sim.cantidad_usuarios} usuarios · {perfil.nombre.toLowerCase()} · ejecutada {formatoFecha(sim.fecha_ejecucion)}
            </p>
          </div>
          {lectura ? (
            <span className="sello-lectura">Modo solo lectura</span>
          ) : (
            <div className="acciones">
              <button type="button" className="btn btn--secundario" onClick={() => void recalcular()} disabled={recalculando}>
                {recalculando ? 'Recalculando…' : 'Recalcular con la topología actual'}
              </button>
              <Link className="btn btn--primario" to={`${base}/simulacion`}>Nueva simulación</Link>
            </div>
          )}
        </div>

        {errorCalculo && <Aviso>{errorCalculo}</Aviso>}
        {recalculado && <Aviso tipo="ok">Resultados actualizados con la topología actual.</Aviso>}

        {!ro || !rt ? (
          <div className="vacio">
            <h2>Esta simulación no tiene resultados</h2>
            <p>{lectura ? 'El cálculo no se completó, probablemente porque la topología tenía errores.' : 'El cálculo no se completó, probablemente porque la topología tenía errores. Corregila en el editor y recalculá.'}</p>
            {!lectura && <div className="acciones">
              <Link className="btn btn--secundario" to={base}>Ir al editor</Link>
              <button type="button" className="btn btn--primario" onClick={() => void recalcular()} disabled={recalculando}>
                {recalculando ? 'Calculando…' : 'Calcular ahora'}
              </button>
            </div>}
          </div>
        ) : (
          <>
            <div className="kpis">
              <div className="kpi">
                <span>Pérdida total · peor caso</span>
                <strong className="mono">{fmt(ro.perdida_total_db)} dB</strong>
                <small>Enlace OLT → ONT/ONU más exigido</small>
              </div>
              <div className="kpi">
                <span>Potencia recibida</span>
                <strong className="mono">{fmt(ro.potencia_recibida_dbm)} dBm</strong>
                <small>En la ONT/ONU del peor caso</small>
              </div>
              <div className="kpi">
                <span>Margen sobre sensibilidad</span>
                <strong className="mono">{margen != null ? `${fmt(margen)} dB` : '—'}</strong>
                <small>{rango ? `Sensibilidad mínima ${fmt(rango.sensibilidad, 0)} dBm` : 'Las ONT/ONU tienen rangos distintos'}</small>
              </div>
              <div className={`kpi kpi--estado${operativo ? '' : ' kpi--alerta'}`}>
                <span>Estado de la red</span>
                <strong>{operativo ? 'Operativa' : 'Fuera de rango'}</strong>
                <small>{operativo ? 'Todas las ONT/ONU dentro de rango' : 'Al menos una ONT/ONU fuera de rango'}</small>
              </div>
            </div>

            <div className="resultados">
              <section className="bloque">
                <div className="bloque__cab">
                  <h2>Potencia en el receptor</h2>
                  {rango && <span className="texto-suave">Ventana operativa: {fmt(rango.sensibilidad, 0)} a {fmt(rango.sobrecarga, 0)} dBm</span>}
                </div>
                <div className="escala-potencia" role="img" aria-label={`Potencia recibida ${fmt(ro.potencia_recibida_dbm)} dBm`}>
                  <div className="escala-potencia__eje" />
                  {rango && (
                    <div className="escala-potencia__ventana" style={{ left: `${pct(rango.sensibilidad)}%`, width: `${pct(rango.sobrecarga) - pct(rango.sensibilidad)}%` }} />
                  )}
                  <div className={`escala-potencia__punto${operativo ? '' : ' escala-potencia__punto--alerta'}`} style={{ left: `${pct(ro.potencia_recibida_dbm)}%` }} />
                </div>
                <div className="escala-potencia__marcas">
                  {[-36, -28, -18, -8, 0].map((v) => (
                    <span key={v} style={{ left: `${pct(v)}%` }}>{v === 0 ? '0 dBm' : `−${Math.abs(v)}`}</span>
                  ))}
                </div>
                <p className="lectura">{lecturaOptica}</p>
              </section>

              <section className="bloque">
                <h2>Indicadores de tráfico</h2>
                <div className="demanda">
                  <div className="demanda__cab">
                    <span>Utilización del enlace</span>
                    <strong className={`mono grande${congestion ? ' texto-alerta' : ''}`}>{fmt(rt.utilizacion_pct)} %</strong>
                  </div>
                  <div className="barra">
                    <div className={`barra__relleno${congestion ? ' barra__relleno--alerta' : ''}`} style={{ width: `${Math.min(100, rt.utilizacion_pct)}%` }} />
                    <div className="barra__umbral" style={{ left: `${UMBRAL_CONGESTION_PCT}%` }} />
                  </div>
                  <div className="barra__escala"><span>0 %</span><span>umbral {UMBRAL_CONGESTION_PCT} %</span><span>100 %</span></div>
                </div>
                <Aviso tipo={congestion ? 'error' : 'ok'}>{congestion ? 'Congestión detectada' : 'Sin congestión'}</Aviso>
                <div className="mini-kpis">
                  <div><span>Throughput total</span><strong className="mono">{fmt(rt.throughput_mbps)} Mbps</strong></div>
                  <div><span>Por usuario</span><strong className="mono">{rt.throughput_por_usuario_mbps != null ? `${fmt(rt.throughput_por_usuario_mbps)} Mbps` : '—'}</strong></div>
                  <div><span>Tiempo de respuesta</span><strong className="mono">{rt.tiempo_respuesta_ms != null ? `${fmt(rt.tiempo_respuesta_ms)} ms` : '—'}</strong></div>
                  <div><span>Capacidad PON</span><strong className="mono">{fmt(CAPACIDAD_DOWNSTREAM_MBPS, 0)} Mbps</strong></div>
                </div>
                <p className="lectura">{lecturaTrafico}</p>
              </section>
            </div>
            <p className="texto-suave nota">
              {lectura
                ? 'Los resultados corresponden a la topología vigente al momento en que el alumno ejecutó el cálculo.'
                : 'Los resultados corresponden a la topología vigente al momento del cálculo. Si modificaste la red después, usá "Recalcular con la topología actual".'}
            </p>
          </>
        )}
      </main>
    </div>
  );
}
