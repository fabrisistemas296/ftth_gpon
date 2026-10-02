import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { BarraSuperior } from '../components/BarraSuperior';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { EstadoBadge } from '../components/EstadoBadge';
import { escenariosApi, proyectosApi, simulacionesApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Escenario, ProyectoDetalle, TipoConsumo } from '../api/types';
import { nombresComponentes } from '../editor/catalogo';
import { revisarTopologia } from '../editor/validacion';
import { CAPACIDAD_DOWNSTREAM_MBPS, CONSUMOS, UMBRAL_CONGESTION_PCT, consumo, fmt } from '../simulacion/trafico';
import { formatoFecha } from '../utils';

const msg = (e: unknown, def: string) => (e instanceof ApiError ? e.message : def);

export function Simulacion() {
  const { id } = useParams();
  const proyectoId = Number(id);
  const navigate = useNavigate();

  const [detalle, setDetalle] = useState<ProyectoDetalle | null>(null);
  const [escenarios, setEscenarios] = useState<Escenario[]>([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);
  const [errorEscenarios, setErrorEscenarios] = useState<string | null>(null);

  const [escenarioId, setEscenarioId] = useState<number | null>(null);
  const [usuarios, setUsuarios] = useState('');
  const [tipo, setTipo] = useState<TipoConsumo>('web');
  const [errorUsuarios, setErrorUsuarios] = useState<string | null>(null);
  const [ejecutando, setEjecutando] = useState(false);
  const [errorEjecucion, setErrorEjecucion] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      try {
        const d = await proyectosApi.detalle(proyectoId);
        if (cancelado) return;
        setDetalle(d);
        // Se precargan los parámetros de la última simulación como punto de partida.
        const ultima = [...d.simulaciones].sort((a, b) => b.id - a.id)[0];
        if (ultima) {
          setEscenarioId(ultima.escenario_id);
          setUsuarios(String(ultima.cantidad_usuarios));
          setTipo(ultima.tipo_consumo);
        }
      } catch (e) {
        if (!cancelado) setErrorCarga(msg(e, 'No se pudo cargar el proyecto.'));
      }
      try {
        const es = await escenariosApi.listar();
        if (!cancelado) setEscenarios(es);
      } catch (e) {
        if (!cancelado) setErrorEscenarios(msg(e, 'No se pudieron cargar los escenarios predefinidos.'));
      } finally {
        if (!cancelado) setCargando(false);
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [proyectoId]);

  const componentes = useMemo(() => detalle?.topologia?.componentes ?? [], [detalle]);
  const conexiones = useMemo(() => detalle?.topologia?.conexiones ?? [], [detalle]);
  const nombres = useMemo(() => nombresComponentes(componentes), [componentes]);
  const errores = useMemo(
    () => revisarTopologia(componentes, conexiones, nombres).filter((p) => p.nivel === 'error'),
    [componentes, conexiones, nombres],
  );

  const escenario = escenarios.find((e) => e.id === escenarioId) ?? null;
  const cantidad = Number(usuarios);
  const cantidadValida = usuarios.trim() !== '' && Number.isInteger(cantidad) && cantidad > 0;
  const demanda = cantidadValida ? cantidad * consumo(tipo).mbps : 0;
  const utilizacion = Math.min(100, (demanda / CAPACIDAD_DOWNSTREAM_MBPS) * 100);
  const historial = useMemo(() => [...(detalle?.simulaciones ?? [])].sort((a, b) => b.id - a.id), [detalle]);

  const elegirEscenario = (e: Escenario | null) => {
    setEscenarioId(e?.id ?? null);
    if (e) {
      setUsuarios(String(e.cantidad_usuarios_default));
      setErrorUsuarios(null);
    }
  };

  const ejecutar = async () => {
    setErrorEjecucion(null);
    if (!cantidadValida) {
      setErrorUsuarios('Ingresá una cantidad de usuarios entera y mayor a 0.');
      return;
    }
    setEjecutando(true);
    try {
      const sim = await simulacionesApi.crear({
        proyecto_id: proyectoId,
        escenario_id: escenarioId,
        cantidad_usuarios: cantidad,
        tipo_consumo: tipo,
      });
      try {
        await simulacionesApi.calcular(sim.id);
      } catch (e) {
        // La simulación queda registrada sin resultados; se informa el motivo.
        setErrorEjecucion(msg(e, 'El cálculo no pudo completarse.'));
        setDetalle(await proyectosApi.detalle(proyectoId));
        return;
      }
      navigate(`/proyectos/${proyectoId}/simulaciones/${sim.id}`);
    } catch (e) {
      setErrorEjecucion(msg(e, 'No se pudo crear la simulación.'));
    } finally {
      setEjecutando(false);
    }
  };

  const izquierda = (
    <>
      <Link to={`/proyectos/${proyectoId}`} className="topbar__volver">← Volver a la topología</Link>
      <span className="topbar__sep" aria-hidden="true" />
      <span className="topbar__marca topbar__titulo">{detalle?.nombre ?? 'Proyecto'}</span>
    </>
  );

  if (cargando) {
    return (
      <div className="pagina">
        <BarraSuperior izquierda={izquierda} />
        <Cargando texto="Cargando" pantallaCompleta />
      </div>
    );
  }

  if (errorCarga || !detalle) {
    return (
      <div className="pagina">
        <BarraSuperior />
        <main className="contenedor">
          <div className="vacio">
            <h2>No se pudo abrir el proyecto</h2>
            <p>{errorCarga}</p>
            <Link className="btn btn--secundario" to="/proyectos">Volver a mis proyectos</Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="pagina">
      <BarraSuperior izquierda={izquierda} />
      <main className="contenedor contenedor--dos">
        <div className="columna">
          <div className="encabezado">
            <div>
              <h1>Configurar simulación de tráfico</h1>
              <p>Partí de un escenario predefinido o cargá los valores a mano. Los datos del escenario se pueden editar.</p>
            </div>
          </div>

          <section className="bloque" aria-labelledby="t-escenario">
            <div className="bloque__cab">
              <h2 id="t-escenario">Escenario de despliegue</h2>
              <span className="texto-suave">Opcional</span>
            </div>
            {errorEscenarios && <Aviso>{errorEscenarios}</Aviso>}
            {!errorEscenarios && escenarios.length === 0 && (
              <Aviso tipo="info">Todavía no hay escenarios cargados en el sistema. Podés simular indicando los valores a mano.</Aviso>
            )}
            <div className="opciones opciones--2" role="radiogroup" aria-label="Escenario">
              <button type="button" role="radio" aria-checked={escenarioId === null} className={`opcion${escenarioId === null ? ' opcion--sel' : ''}`} onClick={() => elegirEscenario(null)}>
                <strong>Sin escenario</strong>
                <span>Valores definidos manualmente</span>
              </button>
              {escenarios.map((e) => (
                <button key={e.id} type="button" role="radio" aria-checked={escenarioId === e.id} className={`opcion${escenarioId === e.id ? ' opcion--sel' : ''}`} onClick={() => elegirEscenario(e)} title={e.descripcion ?? undefined}>
                  <strong>{e.nombre}</strong>
                  <span className="mono">{e.cantidad_usuarios_default} usuarios · {fmt(e.distancia_tipica_km, e.distancia_tipica_km % 1 ? 1 : 0)} km típicos</span>
                </button>
              ))}
            </div>
            {escenario?.descripcion && <p className="texto-suave">{escenario.descripcion}</p>}
          </section>

          <section className="bloque" aria-labelledby="t-usuarios">
            <h2 id="t-usuarios">Usuarios conectados</h2>
            <div className="fila-campo">
              <label htmlFor="usuarios">Cantidad de usuarios</label>
              <input
                id="usuarios"
                inputMode="numeric"
                className="input-corto"
                value={usuarios}
                onChange={(e) => {
                  setUsuarios(e.target.value.replace(/[^\d]/g, ''));
                  setErrorUsuarios(null);
                }}
                aria-invalid={!!errorUsuarios}
              />
              {escenario && String(escenario.cantidad_usuarios_default) === usuarios && <span className="etiqueta">Tomado del escenario</span>}
            </div>
            {errorUsuarios && <span className="campo__error">{errorUsuarios}</span>}
          </section>

          <section className="bloque" aria-labelledby="t-consumo">
            <h2 id="t-consumo">Tipo de consumo predominante</h2>
            <div className="opciones opciones--4" role="radiogroup" aria-label="Tipo de consumo">
              {CONSUMOS.map((c) => (
                <button key={c.id} type="button" role="radio" aria-checked={tipo === c.id} className={`opcion${tipo === c.id ? ' opcion--sel' : ''}`} onClick={() => setTipo(c.id)}>
                  <strong>{c.nombre}</strong>
                  <span className="mono">{fmt(c.mbps, c.mbps % 1 ? 1 : 0)} Mbps</span>
                  <small>{c.detalle}</small>
                </button>
              ))}
            </div>
          </section>

          {historial.length > 0 && (
            <section className="bloque" aria-labelledby="t-historial">
              <h2 id="t-historial">Simulaciones anteriores</h2>
              <ul className="historial">
                {historial.map((s) => {
                  const esc = escenarios.find((e) => e.id === s.escenario_id);
                  const estado = s.resultado_optico?.estado_operativo === 'operativo' ? 'operativo' : s.resultado_optico ? 'fuera_de_rango' : 'sin_simular';
                  return (
                    <li key={s.id}>
                      <Link to={`/proyectos/${proyectoId}/simulaciones/${s.id}`} className="historial__item">
                        <span className="historial__fecha">{formatoFecha(s.fecha_ejecucion)}</span>
                        <span>{esc?.nombre ?? 'Sin escenario'} · {s.cantidad_usuarios} usuarios · {consumo(s.tipo_consumo).nombre.toLowerCase()}</span>
                        <span className="historial__estado">
                          {s.resultado_trafico?.congestion ? <span className="badge badge--fuera_de_rango">Congestión</span> : null}
                          <EstadoBadge estado={estado} />
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </div>

        <aside className="bloque resumen" aria-label="Resumen">
          <h2>Resumen</h2>
          <dl className="datos">
            <div><dt>Escenario</dt><dd>{escenario?.nombre ?? 'Sin escenario'}</dd></div>
            <div><dt>Usuarios</dt><dd className="mono">{cantidadValida ? cantidad : '—'}</dd></div>
            <div><dt>Consumo por usuario</dt><dd className="mono">{fmt(consumo(tipo).mbps, consumo(tipo).mbps % 1 ? 1 : 0)} Mbps</dd></div>
            <div><dt>Capacidad del puerto PON</dt><dd className="mono">{fmt(CAPACIDAD_DOWNSTREAM_MBPS, 0)} Mbps</dd></div>
          </dl>
          <div className="demanda">
            <div className="demanda__cab">
              <span>Demanda estimada</span>
              <strong className="mono">{fmt(demanda, demanda % 1 ? 1 : 0)} Mbps</strong>
            </div>
            <div className="barra" role="img" aria-label={`Utilización estimada ${fmt(utilizacion, 1)} por ciento`}>
              <div className={`barra__relleno${utilizacion >= UMBRAL_CONGESTION_PCT ? ' barra__relleno--alerta' : ''}`} style={{ width: `${utilizacion}%` }} />
              <div className="barra__umbral" style={{ left: `${UMBRAL_CONGESTION_PCT}%` }} />
            </div>
            <div className="barra__escala"><span>0 %</span><span>umbral {UMBRAL_CONGESTION_PCT} %</span><span>100 %</span></div>
            {cantidadValida && utilizacion >= UMBRAL_CONGESTION_PCT && (
              <Aviso>Con esta configuración la utilización estimada supera el umbral de congestión.</Aviso>
            )}
          </div>

          {errores.length > 0 ? (
            <div className="form-columna">
              <Aviso>La topología tiene errores y no se puede simular todavía:</Aviso>
              <ul className="problemas">
                {errores.map((p, i) => <li key={i} className="problemas__item problemas__item--error">{p.texto}</li>)}
              </ul>
              <Link className="btn btn--secundario" to={`/proyectos/${proyectoId}`}>Corregir en el editor</Link>
            </div>
          ) : (
            <>
              {errorEjecucion && <Aviso>{errorEjecucion}</Aviso>}
              <button type="button" className="btn btn--primario btn--grande" onClick={() => void ejecutar()} disabled={ejecutando}>
                {ejecutando ? 'Calculando…' : 'Ejecutar simulación'}
              </button>
            </>
          )}
        </aside>
      </main>
    </div>
  );
}
