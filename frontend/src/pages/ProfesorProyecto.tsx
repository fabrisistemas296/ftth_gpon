import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Background, BackgroundVariant, ConnectionMode, Controls, ReactFlow, useNodesState, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { BarraSuperior } from '../components/BarraSuperior';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { EstadoBadge } from '../components/EstadoBadge';
import { escenariosApi, proyectosApi, usuariosApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Escenario, ProyectoDetalle, Usuario } from '../api/types';
import { NodoComponente, type NodoFlow } from '../editor/NodoComponente';
import { PanelConfiguracion } from '../editor/PanelConfiguracion';
import { nombresComponentes } from '../editor/catalogo';
import { revisarTopologia } from '../editor/validacion';
import { construirAristas } from '../editor/aristas';
import { consumo, fmt } from '../simulacion/trafico';
import { formatoFecha } from '../utils';

const tiposNodo = { componente: NodoComponente };

export function ProfesorProyecto() {
  const { id } = useParams();
  const proyectoId = Number(id);

  const [detalle, setDetalle] = useState<ProyectoDetalle | null>(null);
  const [alumno, setAlumno] = useState<Usuario | null>(null);
  const [escenarios, setEscenarios] = useState<Escenario[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<NodoFlow>([]);

  useEffect(() => {
    (async () => {
      try {
        const d = await proyectosApi.detalle(proyectoId);
        setDetalle(d);
        const comps = d.topologia?.componentes ?? [];
        const nombres = nombresComponentes(comps);
        setNodes(comps.map((c) => ({ id: String(c.id), type: 'componente', position: { x: c.posicion_x, y: c.posicion_y }, data: { componente: c, nombre: nombres[c.id] } })));
        usuariosApi.listar().then((us) => setAlumno(us.find((u) => u.id === d.usuario_id) ?? null)).catch(() => undefined);
        escenariosApi.listar().then(setEscenarios).catch(() => undefined);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : 'No se pudo cargar el proyecto.');
      } finally {
        setCargando(false);
      }
    })();
  }, [proyectoId, setNodes]);

  const componentes = useMemo(() => detalle?.topologia?.componentes ?? [], [detalle]);
  const conexiones = useMemo(() => detalle?.topologia?.conexiones ?? [], [detalle]);
  const nombres = useMemo(() => nombresComponentes(componentes), [componentes]);
  const problemas = useMemo(() => revisarTopologia(componentes, conexiones, nombres), [componentes, conexiones, nombres]);
  const edges = useMemo<Edge[]>(() => construirAristas(conexiones, nodes), [conexiones, nodes]);
  const seleccionados = nodes.filter((n) => n.selected);
  const seleccionado = seleccionados.length === 1 ? componentes.find((c) => String(c.id) === seleccionados[0].id) : undefined;
  const simulaciones = useMemo(() => [...(detalle?.simulaciones ?? [])].sort((a, b) => b.id - a.id), [detalle]);

  const izquierda = (
    <>
      <Link to="/profesor" className="topbar__volver">← Proyectos de alumnos</Link>
      <span className="topbar__sep" aria-hidden="true" />
      <span className="topbar__marca topbar__titulo">{detalle?.nombre ?? 'Proyecto'}</span>
    </>
  );

  if (cargando) {
    return (
      <div className="pagina">
        <BarraSuperior izquierda={izquierda} />
        <Cargando texto="Cargando proyecto" pantallaCompleta />
      </div>
    );
  }

  if (error || !detalle) {
    return (
      <div className="pagina">
        <BarraSuperior izquierda={izquierda} />
        <main className="contenedor">
          <div className="vacio">
            <h2>No se pudo abrir el proyecto</h2>
            <p>{error}</p>
            <Link className="btn btn--secundario" to="/profesor">Volver al listado</Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="pagina">
      <BarraSuperior izquierda={izquierda} />
      <main className="contenedor contenedor--ancho">
        <div className="encabezado">
          <div>
            <h1>{detalle.nombre}</h1>
            <p>
              {alumno ? `${alumno.nombre} (${alumno.email})` : `Alumno ${detalle.usuario_id}`} · creado {formatoFecha(detalle.fecha_creacion)} · modificado {formatoFecha(detalle.fecha_modificacion)}
            </p>
          </div>
          <span className="sello-lectura">Modo solo lectura</span>
        </div>
        {detalle.descripcion && <p className="lectura">{detalle.descripcion}</p>}

        <section className="bloque bloque--sin-padding" aria-label="Topología">
          <div className="vista-topologia">
            <div className="vista-topologia__lienzo">
              {componentes.length === 0 ? (
                <div className="lienzo__vacio"><h2>El alumno todavía no armó la topología</h2></div>
              ) : (
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  nodeTypes={tiposNodo}
                  onNodesChange={onNodesChange}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  connectionMode={ConnectionMode.Loose}
                  edgesFocusable={false}
                  deleteKeyCode={null}
                  fitView
                  fitViewOptions={{ padding: 0.2, maxZoom: 1.1 }}
                  minZoom={0.3}
                  maxZoom={2}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#c7d0d9" />
                  <Controls showInteractive={false} />
                </ReactFlow>
              )}
              <div className="lienzo__info">{componentes.length} componentes · {conexiones.length} conexiones</div>
            </div>
            <aside className="vista-topologia__panel">
              {seleccionado ? (
                <PanelConfiguracion componente={seleccionado} nombre={nombres[seleccionado.id]} soloLectura onAplicar={async () => undefined} onEliminar={() => undefined} />
              ) : (
                <div className="panel">
                  <div className="panel__cab">
                    <span className="panel__tipo">Revisión de la topología</span>
                    <h2>{problemas.filter((p) => p.nivel === 'error').length === 0 && componentes.length > 0 ? 'Lista para simular' : 'Con observaciones'}</h2>
                  </div>
                  <p className="texto-suave">Seleccioná un componente para ver sus parámetros.</p>
                  {problemas.length === 0 && componentes.length > 0 ? (
                    <Aviso tipo="ok">La red tiene una OLT y todas las ONT/ONU están conectadas a ella.</Aviso>
                  ) : (
                    <ul className="problemas">
                      {problemas.map((p, i) => <li key={i} className={`problemas__item problemas__item--${p.nivel}`}>{p.texto}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </aside>
          </div>
        </section>

        <section className="bloque" aria-labelledby="t-sims">
          <div className="bloque__cab">
            <h2 id="t-sims">Simulaciones</h2>
            <span className="texto-suave">{simulaciones.length} en total</span>
          </div>
          {simulaciones.length === 0 ? (
            <p className="texto-suave">El alumno todavía no ejecutó simulaciones en este proyecto.</p>
          ) : (
            <div className="tabla-envoltorio tabla-envoltorio--plano">
              <table className="tabla">
                <thead>
                  <tr>
                    <th scope="col">Fecha</th>
                    <th scope="col">Escenario</th>
                    <th scope="col">Usuarios · consumo</th>
                    <th scope="col">Pérdida</th>
                    <th scope="col">Potencia</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Utilización</th>
                    <th scope="col"><span className="sr-only">Acción</span></th>
                  </tr>
                </thead>
                <tbody>
                  {simulaciones.map((s) => {
                    const ro = s.resultado_optico;
                    const rt = s.resultado_trafico;
                    return (
                      <tr key={s.id}>
                        <td className="mono texto-suave">{formatoFecha(s.fecha_ejecucion)}</td>
                        <td>{escenarios.find((e) => e.id === s.escenario_id)?.nombre ?? 'Sin escenario'}</td>
                        <td>{s.cantidad_usuarios} · {consumo(s.tipo_consumo).nombre.toLowerCase()}</td>
                        <td className="mono">{ro ? `${fmt(ro.perdida_total_db)} dB` : '—'}</td>
                        <td className="mono">{ro ? `${fmt(ro.potencia_recibida_dbm)} dBm` : '—'}</td>
                        <td><EstadoBadge estado={ro ? (ro.estado_operativo === 'operativo' ? 'operativo' : 'fuera_de_rango') : 'sin_simular'} /></td>
                        <td className="mono">
                          {rt ? (
                            <span className={rt.congestion ? 'texto-alerta' : undefined}>
                              {fmt(rt.utilizacion_pct, 1)} %{rt.congestion ? ' · congestión' : ''}
                            </span>
                          ) : '—'}
                        </td>
                        <td className="celda-accion">
                          <Link className="btn btn--secundario" to={`/profesor/proyectos/${proyectoId}/simulaciones/${s.id}`}>Ver resultados</Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
