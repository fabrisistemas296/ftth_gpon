import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarraSuperior } from '../components/BarraSuperior';
import { Modal } from '../components/Modal';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { EstadoBadge, type Estado } from '../components/EstadoBadge';
import { proyectosApi, topologiasApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Proyecto, ProyectoDetalle } from '../api/types';
import { formatoFecha, parseFecha } from '../utils';

interface Resumen {
  componentes: number;
  simulaciones: number;
  estado: Estado;
}

function resumir(d: ProyectoDetalle): Resumen {
  const conResultado = d.simulaciones
    .filter((s) => s.resultado_optico)
    .sort((a, b) => b.id - a.id);
  const ultimo = conResultado[0]?.resultado_optico?.estado_operativo;
  return {
    componentes: d.topologia?.componentes.length ?? 0,
    simulaciones: d.simulaciones.length,
    estado: ultimo === 'operativo' ? 'operativo' : ultimo === 'fuera_de_rango' ? 'fuera_de_rango' : 'sin_simular',
  };
}

const msg = (e: unknown, def: string) => (e instanceof ApiError ? e.message : def);

type Formulario = { modo: 'crear' } | { modo: 'editar'; proyecto: Proyecto };

export function Proyectos() {
  const navigate = useNavigate();
  const [proyectos, setProyectos] = useState<Proyecto[]>([]);
  const [resumenes, setResumenes] = useState<Record<number, Resumen>>({});
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [aviso, setAviso] = useState<string | null>(null);

  const [form, setForm] = useState<Formulario | null>(null);
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState<string | null>(null);

  const [aEliminar, setAEliminar] = useState<Proyecto | null>(null);
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);

  const cargarResumen = useCallback(async (id: number) => {
    try {
      const d = await proyectosApi.detalle(id);
      setResumenes((r) => ({ ...r, [id]: resumir(d) }));
    } catch {
      /* el resumen es complementario: si falla, la tarjeta se muestra sin él */
    }
  }, []);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const lista = await proyectosApi.listar();
      setProyectos(lista);
      lista.forEach((p) => void cargarResumen(p.id));
    } catch (e) {
      setError(msg(e, 'No se pudieron cargar los proyectos.'));
    } finally {
      setCargando(false);
    }
  }, [cargarResumen]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(null), 3500);
    return () => clearTimeout(t);
  }, [aviso]);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return [...proyectos]
      .filter((p) => !q || p.nombre.toLowerCase().includes(q) || (p.descripcion ?? '').toLowerCase().includes(q))
      .sort((a, b) => parseFecha(b.fecha_modificacion).getTime() - parseFecha(a.fecha_modificacion).getTime());
  }, [proyectos, busqueda]);

  const abrirCrear = () => {
    setNombre('');
    setDescripcion('');
    setErrorForm(null);
    setForm({ modo: 'crear' });
  };

  const abrirEditar = (p: Proyecto) => {
    setNombre(p.nombre);
    setDescripcion(p.descripcion ?? '');
    setErrorForm(null);
    setForm({ modo: 'editar', proyecto: p });
  };

  const cerrarForm = useCallback(() => {
    if (!guardando) setForm(null);
  }, [guardando]);

  const guardar = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    if (!nombre.trim()) {
      setErrorForm('El proyecto necesita un nombre.');
      return;
    }
    const datos = { nombre: nombre.trim(), descripcion: descripcion.trim() || null };
    setGuardando(true);
    setErrorForm(null);
    try {
      if (form.modo === 'crear') {
        const nuevo = await proyectosApi.crear(datos);
        // Cada proyecto contiene exactamente una topología: se crea junto con el proyecto.
        try {
          await topologiasApi.crear(nuevo.id);
        } catch {
          /* si falla, el editor la crea al abrir el proyecto */
        }
        setProyectos((ps) => [nuevo, ...ps]);
        setResumenes((r) => ({ ...r, [nuevo.id]: { componentes: 0, simulaciones: 0, estado: 'sin_simular' } }));
        setAviso(`Proyecto "${nuevo.nombre}" creado.`);
      } else {
        const actualizado = await proyectosApi.actualizar(form.proyecto.id, datos);
        setProyectos((ps) => ps.map((p) => (p.id === actualizado.id ? actualizado : p)));
        setAviso('Cambios guardados.');
      }
      setForm(null);
    } catch (e2) {
      setErrorForm(msg(e2, 'No se pudo guardar el proyecto.'));
    } finally {
      setGuardando(false);
    }
  };

  const confirmarEliminar = async () => {
    if (!aEliminar) return;
    setEliminando(true);
    setErrorEliminar(null);
    try {
      await proyectosApi.eliminar(aEliminar.id);
      setProyectos((ps) => ps.filter((p) => p.id !== aEliminar.id));
      setAviso(`Proyecto "${aEliminar.nombre}" eliminado.`);
      setAEliminar(null);
    } catch (e) {
      setErrorEliminar(msg(e, 'No se pudo eliminar el proyecto.'));
    } finally {
      setEliminando(false);
    }
  };

  const cerrarEliminar = useCallback(() => {
    if (!eliminando) {
      setAEliminar(null);
      setErrorEliminar(null);
    }
  }, [eliminando]);

  return (
    <div className="pagina">
      <BarraSuperior />
      <main className="contenedor">
        <div className="encabezado">
          <div>
            <h1>Mis proyectos</h1>
            <p>Creá una topología nueva o abrí un proyecto guardado para seguir trabajando.</p>
          </div>
          <button type="button" className="btn btn--primario" onClick={abrirCrear}>
            <svg width="16" height="16" viewBox="0 0 16 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg>
            Nuevo proyecto
          </button>
        </div>

        {aviso && <Aviso tipo="ok">{aviso}</Aviso>}

        {proyectos.length > 0 && (
          <div className="buscador">
            <label htmlFor="buscar">Buscar</label>
            <input id="buscar" type="search" placeholder="Nombre o descripción" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
          </div>
        )}

        {cargando && <Cargando texto="Cargando proyectos" />}
        {error && (
          <Aviso>
            {error}{' '}
            <button type="button" className="enlace" onClick={() => void cargar()}>Reintentar</button>
          </Aviso>
        )}

        {!cargando && !error && proyectos.length === 0 && (
          <div className="vacio">
            <h2>Todavía no tenés proyectos</h2>
            <p>Un proyecto contiene una topología de red y las simulaciones que ejecutes sobre ella.</p>
            <button type="button" className="btn btn--primario" onClick={abrirCrear}>Crear mi primer proyecto</button>
          </div>
        )}

        {!cargando && proyectos.length > 0 && visibles.length === 0 && (
          <p className="texto-suave">Ningún proyecto coincide con "{busqueda}".</p>
        )}

        <div className="grilla-proyectos">
          {visibles.map((p) => {
            const r = resumenes[p.id];
            return (
              <article key={p.id} className="tarjeta-proyecto">
                <div className="tarjeta-proyecto__cab">
                  <h2>{p.nombre}</h2>
                  {r && <EstadoBadge estado={r.estado} />}
                </div>
                <p className="tarjeta-proyecto__desc">{p.descripcion || 'Sin descripción.'}</p>
                <div className="tarjeta-proyecto__datos">
                  <span>{r ? `${r.componentes} componentes` : '…'}</span>
                  <span>{r ? `${r.simulaciones} simulaciones` : ''}</span>
                </div>
                <div className="tarjeta-proyecto__pie">
                  <span>Modificado {formatoFecha(p.fecha_modificacion)}</span>
                  <div className="acciones">
                    <button type="button" className="btn-icono btn-icono--borde" aria-label={`Editar ${p.nombre}`} onClick={() => abrirEditar(p)}>
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M10.5 2.5l3 3L6 13H3v-3z" /></svg>
                    </button>
                    <button type="button" className="btn-icono btn-icono--borde" aria-label={`Eliminar ${p.nombre}`} onClick={() => setAEliminar(p)}>
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.6 8.5h5.8l.6-8.5" /></svg>
                    </button>
                    <button type="button" className="btn btn--secundario" onClick={() => navigate(`/proyectos/${p.id}`)}>Abrir</button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </main>

      <Modal
        titulo={form?.modo === 'editar' ? 'Editar proyecto' : 'Nuevo proyecto'}
        abierto={form !== null}
        onCerrar={cerrarForm}
        pie={
          <>
            <button type="button" className="btn btn--secundario" onClick={cerrarForm} disabled={guardando}>Cancelar</button>
            <button type="submit" form="form-proyecto" className="btn btn--primario" disabled={guardando}>
              {guardando ? 'Guardando…' : form?.modo === 'editar' ? 'Guardar cambios' : 'Crear proyecto'}
            </button>
          </>
        }
      >
        <form id="form-proyecto" className="form-columna" onSubmit={guardar} noValidate>
          <div className="campo">
            <label htmlFor="p-nombre">Nombre</label>
            <input id="p-nombre" value={nombre} maxLength={120} onChange={(e) => setNombre(e.target.value)} placeholder="Ej.: Barrio residencial – splitter 1:32" />
          </div>
          <div className="campo">
            <label htmlFor="p-desc">Descripción <span className="opcional">(opcional)</span></label>
            <textarea id="p-desc" rows={3} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
          </div>
          {errorForm && <Aviso>{errorForm}</Aviso>}
        </form>
      </Modal>

      <Modal
        titulo="Eliminar proyecto"
        abierto={aEliminar !== null}
        onCerrar={cerrarEliminar}
        pie={
          <>
            <button type="button" className="btn btn--secundario" onClick={cerrarEliminar} disabled={eliminando}>Cancelar</button>
            <button type="button" className="btn btn--peligro" onClick={() => void confirmarEliminar()} disabled={eliminando}>
              {eliminando ? 'Eliminando…' : 'Eliminar proyecto'}
            </button>
          </>
        }
      >
        <p>
          Se eliminará <strong>{aEliminar?.nombre}</strong> junto con su topología, sus componentes y todas sus
          simulaciones. Esta acción no se puede deshacer.
        </p>
        {errorEliminar && <Aviso>{errorEliminar}</Aviso>}
      </Modal>
    </div>
  );
}
