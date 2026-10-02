import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Background,
  BackgroundVariant,
  ConnectionMode,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { BarraSuperior } from '../components/BarraSuperior';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { componentesApi, conexionesApi, proyectosApi, topologiasApi, type ComponenteInput } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Componente, Conexion, Proyecto, TipoComponente } from '../api/types';
import { NodoComponente, type NodoFlow } from '../editor/NodoComponente';
import { PanelConfiguracion } from '../editor/PanelConfiguracion';
import { Paleta, TIPO_DND } from '../editor/Paleta';
import { aInput, componenteVacio, nombresComponentes } from '../editor/catalogo';
import { revisarTopologia, validarConexion } from '../editor/validacion';
import { construirAristas } from '../editor/aristas';

const tiposNodo = { componente: NodoComponente };
const msg = (e: unknown, def: string) => (e instanceof ApiError || e instanceof Error ? e.message : def);

function aNodo(c: Componente, nombre: string, previo?: NodoFlow): NodoFlow {
  // Se reutiliza el nodo previo (conserva medidas, posición y selección);
  // si se descartan las medidas, React Flow vuelve a ocultar el nodo.
  if (previo) return { ...previo, data: { componente: c, nombre } };
  return {
    id: String(c.id),
    type: 'componente',
    position: { x: c.posicion_x, y: c.posicion_y },
    data: { componente: c, nombre },
    selected: false,
  };
}

function EditorInterno() {
  const { id } = useParams();
  const proyectoId = Number(id);
  const navigate = useNavigate();
  const { screenToFlowPosition, fitView } = useReactFlow();
  const lienzoRef = useRef<HTMLDivElement>(null);

  const [proyecto, setProyecto] = useState<Proyecto | null>(null);
  const [topologiaId, setTopologiaId] = useState<number | null>(null);
  const [componentes, setComponentes] = useState<Componente[]>([]);
  const [conexiones, setConexiones] = useState<Conexion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<NodoFlow>([]);
  const [aristasSel, setAristasSel] = useState<Set<string>>(new Set());

  const [pendientes, setPendientes] = useState(0);
  const [aviso, setAviso] = useState<{ tipo: 'error' | 'ok'; texto: string } | null>(null);
  const agregados = useRef(0);

  const nombres = useMemo(() => nombresComponentes(componentes), [componentes]);
  const problemas = useMemo(() => revisarTopologia(componentes, conexiones, nombres), [componentes, conexiones, nombres]);

  // Envuelve cada llamada a la API para mostrar el estado "Guardando…" y los errores.
  const conGuardado = useCallback(async <T,>(fn: () => Promise<T>, error: string): Promise<T | undefined> => {
    setPendientes((n) => n + 1);
    try {
      return await fn();
    } catch (e) {
      setAviso({ tipo: 'error', texto: msg(e, error) });
      return undefined;
    } finally {
      setPendientes((n) => n - 1);
    }
  }, []);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(null), aviso.tipo === 'error' ? 6000 : 3000);
    return () => clearTimeout(t);
  }, [aviso]);

  // Carga inicial: detalle del proyecto (topología, componentes y conexiones).
  useEffect(() => {
    let cancelado = false;
    (async () => {
      setCargando(true);
      setErrorCarga(null);
      try {
        let d = await proyectosApi.detalle(proyectoId);
        if (!d.topologia) {
          try {
            await topologiasApi.crear(proyectoId);
          } catch (e) {
            // 400 = otra pestaña o carga paralela ya la creó; cualquier otro error se informa.
            if (!(e instanceof ApiError && e.status === 400)) throw e;
          }
          d = await proyectosApi.detalle(proyectoId);
          if (!d.topologia) throw new Error('No se pudo crear la topología del proyecto.');
        }
        if (cancelado) return;
        setProyecto(d);
        setTopologiaId(d.topologia!.id);
        setComponentes(d.topologia!.componentes);
        setConexiones(d.topologia!.conexiones);
        setTimeout(() => fitView({ padding: 0.25, maxZoom: 1.1 }), 50);
      } catch (e) {
        if (!cancelado) setErrorCarga(msg(e, 'No se pudo abrir el proyecto.'));
      } finally {
        if (!cancelado) setCargando(false);
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [proyectoId, fitView]);

  // Sincroniza el lienzo con los datos persistidos, conservando posición y selección.
  useEffect(() => {
    setNodes((prev) => {
      const porId = new Map(prev.map((n) => [n.id, n]));
      return componentes.map((c) => aNodo(c, nombres[c.id], porId.get(String(c.id))));
    });
  }, [componentes, nombres, setNodes]);

  const edges = useMemo<Edge[]>(() => construirAristas(conexiones, nodes, aristasSel), [conexiones, nodes, aristasSel]);

  const onEdgesChange = useCallback((cambios: EdgeChange[]) => {
    setAristasSel((prev) => {
      const sig = new Set(prev);
      cambios.forEach((ch) => {
        if (ch.type === 'select') {
          if (ch.selected) sig.add(ch.id);
          else sig.delete(ch.id);
        }
      });
      return sig;
    });
  }, []);

  const porId = useMemo(() => new Map(componentes.map((c) => [String(c.id), c])), [componentes]);

  // La selección se deriva del estado del lienzo (clics, selección múltiple o programática).
  const seleccion = useMemo(
    () => ({ nodos: nodes.filter((n) => n.selected).map((n) => n.id), aristas: edges.filter((e) => e.selected).map((e) => e.id) }),
    [nodes, edges],
  );

  // ---------- Agregar componentes ----------
  const agregar = useCallback(
    async (tipo: TipoComponente, posicion?: { x: number; y: number }) => {
      if (topologiaId == null) return;
      let pos = posicion;
      if (!pos) {
        const r = lienzoRef.current?.getBoundingClientRect();
        const centro = r ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : { x: 400, y: 300 };
        // Escalonado para que los componentes nuevos no queden encimados.
        const paso = agregados.current++ % 5;
        pos = screenToFlowPosition({ x: centro.x - 200 + paso * 50, y: centro.y - 160 + paso * 72 });
      }
      const nuevo = await conGuardado(() => componentesApi.crear(componenteVacio(topologiaId, tipo, pos!.x, pos!.y)), 'No se pudo agregar el componente.');
      if (nuevo) {
        setComponentes((cs) => [...cs, nuevo]);
        // Queda seleccionado para configurarlo de inmediato.
        setTimeout(() => setNodes((ns) => ns.map((n) => ({ ...n, selected: n.id === String(nuevo.id) }))), 0);
      }
    },
    [topologiaId, screenToFlowPosition, conGuardado, setNodes],
  );

  const onDragOver = (e: DragEvent) => {
    if (e.dataTransfer.types.includes(TIPO_DND)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    }
  };

  const onDrop = (e: DragEvent) => {
    const tipo = e.dataTransfer.getData(TIPO_DND) as TipoComponente;
    if (!tipo) return;
    e.preventDefault();
    const pos = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    void agregar(tipo, { x: pos.x - 80, y: pos.y - 28 });
  };

  // ---------- Mover componentes ----------
  const onNodeDragStop = useCallback(
    async (_: unknown, __: Node, movidos: Node[]) => {
      for (const n of movidos) {
        const c = porId.get(n.id);
        if (!c) continue;
        const x = Math.round(n.position.x);
        const y = Math.round(n.position.y);
        if (x === Math.round(c.posicion_x) && y === Math.round(c.posicion_y)) continue;
        const actualizado = await conGuardado(
          () => componentesApi.actualizar(c.id, { ...aInput(c), posicion_x: x, posicion_y: y }),
          'No se pudo guardar la nueva posición.',
        );
        if (actualizado) {
          setComponentes((cs) => cs.map((k) => (k.id === c.id ? actualizado : k)));
        } else {
          // Se revierte a la última posición guardada.
          setNodes((ns) => ns.map((k) => (k.id === n.id ? { ...k, position: { x: c.posicion_x, y: c.posicion_y } } : k)));
        }
      }
    },
    [porId, conGuardado, setNodes],
  );

  // ---------- Conectar ----------
  const motivoInvalido = useCallback(
    (origen: string | null, destino: string | null) =>
      validarConexion(porId.get(origen ?? ''), porId.get(destino ?? ''), conexiones),
    [porId, conexiones],
  );

  const isValidConnection = useCallback(
    (c: Connection | Edge) => motivoInvalido(c.source, c.target) === null,
    [motivoInvalido],
  );

  const onConnect = useCallback(
    async (c: Connection) => {
      if (topologiaId == null) return;
      const motivo = motivoInvalido(c.source, c.target);
      if (motivo) {
        setAviso({ tipo: 'error', texto: motivo });
        return;
      }
      const nueva = await conGuardado(
        () => conexionesApi.crear(topologiaId, Number(c.source), Number(c.target)),
        'No se pudo crear la conexión.',
      );
      if (nueva) setConexiones((cs) => [...cs, nueva]);
    },
    [topologiaId, motivoInvalido, conGuardado],
  );

  // Al soltar una conexión sobre un punto inválido se explica el motivo.
  const onConnectEnd = useCallback(
    (_: MouseEvent | TouchEvent, estado: { isValid: boolean | null; fromNode: { id: string } | null; toNode: { id: string } | null }) => {
      if (estado.isValid === false && estado.fromNode && estado.toNode) {
        const motivo = motivoInvalido(estado.fromNode.id, estado.toNode.id);
        if (motivo) setAviso({ tipo: 'error', texto: motivo });
      }
    },
    [motivoInvalido],
  );

  // ---------- Eliminar ----------
  const eliminar = useCallback(
    async (idsNodos: string[], idsAristas: string[]) => {
      const nodosSet = new Set(idsNodos);
      // Primero las conexiones (las seleccionadas y las que tocan a los componentes a borrar).
      const aristas = conexiones.filter(
        (c) =>
          idsAristas.includes(String(c.id)) ||
          nodosSet.has(String(c.componente_origen_id)) ||
          nodosSet.has(String(c.componente_destino_id)),
      );
      for (const a of aristas) {
        const ok = await conGuardado(() => conexionesApi.eliminar(a.id), 'No se pudo eliminar la conexión.');
        if (ok === undefined) return;
        setConexiones((cs) => cs.filter((k) => k.id !== a.id));
        setAristasSel((sel) => { const n = new Set(sel); n.delete(String(a.id)); return n; });
      }
      for (const idN of idsNodos) {
        const ok = await conGuardado(() => componentesApi.eliminar(Number(idN)), 'No se pudo eliminar el componente.');
        if (ok === undefined) return;
        setComponentes((cs) => cs.filter((k) => String(k.id) !== idN));
      }
    },
    [conexiones, conGuardado],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return;
      const el = e.target as HTMLElement;
      if (el.closest('input, textarea, select, [contenteditable="true"]')) return;
      if (!seleccion.nodos.length && !seleccion.aristas.length) return;
      e.preventDefault();
      void eliminar(seleccion.nodos, seleccion.aristas);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [seleccion, eliminar]);


  // ---------- Configurar ----------
  const aplicarConfiguracion = useCallback(
    async (c: Componente, datos: ComponenteInput) => {
      const nodo = nodes.find((n) => n.id === String(c.id));
      const conPosicion = nodo
        ? { ...datos, posicion_x: Math.round(nodo.position.x), posicion_y: Math.round(nodo.position.y) }
        : datos;
      setPendientes((n) => n + 1);
      try {
        const actualizado = await componentesApi.actualizar(c.id, conPosicion);
        setComponentes((cs) => cs.map((k) => (k.id === c.id ? actualizado : k)));
      } catch (e) {
        throw new Error(msg(e, 'No se pudieron guardar los cambios.'));
      } finally {
        setPendientes((n) => n - 1);
      }
    },
    [nodes],
  );

  const seleccionado = seleccion.nodos.length === 1 && seleccion.aristas.length === 0 ? porId.get(seleccion.nodos[0]) : undefined;
  const aristaSel = seleccion.aristas.length === 1 && seleccion.nodos.length === 0 ? conexiones.find((c) => String(c.id) === seleccion.aristas[0]) : undefined;
  const errores = problemas.filter((p) => p.nivel === 'error');

  if (cargando) {
    return (
      <div className="pagina">
        <BarraSuperior />
        <Cargando texto="Abriendo proyecto" pantallaCompleta />
      </div>
    );
  }

  if (errorCarga || !proyecto) {
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
    <div className="editor">
      <BarraSuperior
        izquierda={
          <>
            <Link to="/proyectos" className="topbar__volver">← Mis proyectos</Link>
            <span className="topbar__sep" aria-hidden="true" />
            <span className="topbar__marca topbar__titulo">{proyecto.nombre}</span>
            <span className="topbar__estado" aria-live="polite">{pendientes > 0 ? 'Guardando…' : 'Cambios guardados'}</span>
          </>
        }
        acciones={
          <button type="button" className="btn btn--claro" onClick={() => navigate(`/proyectos/${proyectoId}/simulacion`)}>
            Configurar simulación
          </button>
        }
      />
      <div className="editor__cuerpo">
        <Paleta onAgregar={(t) => void agregar(t)} />

        <div className="lienzo" ref={lienzoRef} onDragOver={onDragOver} onDrop={onDrop}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={tiposNodo}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDragStop={onNodeDragStop}
            onConnect={onConnect}
            onConnectEnd={onConnectEnd}
            isValidConnection={isValidConnection}
            connectionMode={ConnectionMode.Loose}
            deleteKeyCode={null}
            snapToGrid
            snapGrid={[10, 10]}
            minZoom={0.3}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#c7d0d9" />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable nodeColor={(n) => (n.data as { componente?: Componente })?.componente?.tipo === 'OLT' ? '#0f2a3d' : '#8fb3cc'} />
          </ReactFlow>
          <div className="lienzo__info">{componentes.length} componentes · {conexiones.length} conexiones</div>
          {componentes.length === 0 && (
            <div className="lienzo__vacio">
              <h2>La topología está vacía</h2>
              <p>Empezá agregando una OLT, después fibra, un splitter y las ONT/ONU de los usuarios.</p>
            </div>
          )}
          {aviso && (
            <div className="lienzo__aviso">
              <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>
            </div>
          )}
        </div>

        <aside className="lateral">
          {seleccionado ? (
            <PanelConfiguracion
              componente={seleccionado}
              nombre={nombres[seleccionado.id]}
              onAplicar={(datos) => aplicarConfiguracion(seleccionado, datos)}
              onEliminar={() => void eliminar([String(seleccionado.id)], [])}
            />
          ) : aristaSel ? (
            <div className="panel">
              <div className="panel__cab">
                <span className="panel__tipo">Conexión</span>
                <h2>{nombres[aristaSel.componente_origen_id]} ↔ {nombres[aristaSel.componente_destino_id]}</h2>
              </div>
              <p className="texto-suave">Las conexiones definen el recorrido de la señal. Eliminala para reconectar los componentes de otra forma.</p>
              <div className="panel__acciones">
                <button type="button" className="btn btn--secundario btn--peligro-borde" onClick={() => void eliminar([], [String(aristaSel.id)])}>
                  Eliminar conexión
                </button>
              </div>
            </div>
          ) : (
            <div className="panel">
              <div className="panel__cab">
                <span className="panel__tipo">Revisión de la topología</span>
                <h2>{errores.length === 0 && componentes.length > 0 ? 'Lista para simular' : 'Pendiente'}</h2>
              </div>
              {seleccion.nodos.length + seleccion.aristas.length > 1 ? (
                <>
                  <p className="texto-suave">{seleccion.nodos.length + seleccion.aristas.length} elementos seleccionados.</p>
                  <button type="button" className="btn btn--secundario btn--peligro-borde" onClick={() => void eliminar(seleccion.nodos, seleccion.aristas)}>
                    Eliminar selección
                  </button>
                </>
              ) : (
                <p className="texto-suave">Seleccioná un componente para configurar sus parámetros.</p>
              )}
              {problemas.length === 0 && componentes.length > 0 ? (
                <Aviso tipo="ok">La red tiene una OLT y todas las ONT/ONU están conectadas a ella.</Aviso>
              ) : (
                <ul className="problemas">
                  {problemas.map((p, i) => (
                    <li key={i} className={`problemas__item problemas__item--${p.nivel}`}>{p.texto}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export function Editor() {
  return (
    <ReactFlowProvider>
      <EditorInterno />
    </ReactFlowProvider>
  );
}
