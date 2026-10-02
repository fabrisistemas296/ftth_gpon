import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarraSuperior } from '../components/BarraSuperior';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { EstadoBadge, type Estado } from '../components/EstadoBadge';
import { PestanasProfesor } from '../profesor/Pestanas';
import { proyectosApi, usuariosApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Proyecto, ProyectoDetalle, Usuario } from '../api/types';
import { formatoFecha, parseFecha } from '../utils';

interface Resumen {
  componentes: number;
  simulaciones: number;
  estado: Estado;
}

function resumir(d: ProyectoDetalle): Resumen {
  const ultimo = [...d.simulaciones].filter((s) => s.resultado_optico).sort((a, b) => b.id - a.id)[0]?.resultado_optico?.estado_operativo;
  return {
    componentes: d.topologia?.componentes.length ?? 0,
    simulaciones: d.simulaciones.length,
    estado: ultimo === 'operativo' ? 'operativo' : ultimo ? 'fuera_de_rango' : 'sin_simular',
  };
}

export function ProfesorProyectos() {
  const navigate = useNavigate();
  const [proyectos, setProyectos] = useState<Proyecto[]>([]);
  const [usuarios, setUsuarios] = useState<Record<number, Usuario>>({});
  const [resumenes, setResumenes] = useState<Record<number, Resumen>>({});
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [estado, setEstado] = useState<'todos' | Estado>('todos');

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [ps, us] = await Promise.all([proyectosApi.listar(), usuariosApi.listar()]);
      setProyectos(ps);
      setUsuarios(Object.fromEntries(us.map((u) => [u.id, u])));
      ps.forEach((p) =>
        proyectosApi
          .detalle(p.id)
          .then((d) => setResumenes((r) => ({ ...r, [p.id]: resumir(d) })))
          .catch(() => undefined),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudieron cargar los proyectos.');
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const filas = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return [...proyectos]
      .filter((p) => {
        const u = usuarios[p.usuario_id];
        const texto = `${p.nombre} ${u?.nombre ?? ''} ${u?.email ?? ''}`.toLowerCase();
        if (q && !texto.includes(q)) return false;
        if (estado !== 'todos' && resumenes[p.id]?.estado !== estado) return false;
        return true;
      })
      .sort((a, b) => parseFecha(b.fecha_modificacion).getTime() - parseFecha(a.fecha_modificacion).getTime());
  }, [proyectos, usuarios, resumenes, busqueda, estado]);

  const alumnos = new Set(proyectos.map((p) => p.usuario_id)).size;

  return (
    <div className="pagina">
      <BarraSuperior />
      <main className="contenedor">
        <PestanasProfesor />
        <div className="encabezado">
          <div>
            <h1>Proyectos de los alumnos</h1>
            <p>Revisá las topologías y los resultados de cada alumno. El acceso es de solo lectura.</p>
          </div>
          <span className="sello-lectura">Modo solo lectura</span>
        </div>

        <div className="filtros">
          <div className="campo">
            <label htmlFor="f-texto">Buscar</label>
            <input id="f-texto" type="search" placeholder="Alumno, email o proyecto" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="f-estado">Estado del último cálculo</label>
            <select id="f-estado" value={estado} onChange={(e) => setEstado(e.target.value as 'todos' | Estado)}>
              <option value="todos">Todos</option>
              <option value="operativo">Operativo</option>
              <option value="fuera_de_rango">Fuera de rango</option>
              <option value="sin_simular">Sin simular</option>
            </select>
          </div>
        </div>

        {cargando && <Cargando texto="Cargando proyectos" />}
        {error && (
          <Aviso>
            {error} <button type="button" className="enlace" onClick={() => void cargar()}>Reintentar</button>
          </Aviso>
        )}

        {!cargando && !error && proyectos.length === 0 && (
          <div className="vacio">
            <h2>Todavía no hay proyectos</h2>
            <p>Cuando los alumnos creen proyectos de simulación, van a aparecer acá.</p>
          </div>
        )}

        {!cargando && proyectos.length > 0 && (
          <div className="tabla-envoltorio">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Alumno</th>
                  <th scope="col">Proyecto</th>
                  <th scope="col">Última modificación</th>
                  <th scope="col">Componentes</th>
                  <th scope="col">Simulaciones</th>
                  <th scope="col">Último cálculo</th>
                  <th scope="col"><span className="sr-only">Acción</span></th>
                </tr>
              </thead>
              <tbody>
                {filas.map((p) => {
                  const u = usuarios[p.usuario_id];
                  const r = resumenes[p.id];
                  return (
                    <tr key={p.id}>
                      <td>
                        <div className="celda-alumno">
                          <span>{u?.nombre ?? `Usuario ${p.usuario_id}`}</span>
                          <small>{u?.email}</small>
                        </div>
                      </td>
                      <td>{p.nombre}</td>
                      <td className="mono texto-suave">{formatoFecha(p.fecha_modificacion)}</td>
                      <td className="mono">{r ? r.componentes : '…'}</td>
                      <td className="mono">{r ? r.simulaciones : '…'}</td>
                      <td>{r ? <EstadoBadge estado={r.estado} /> : '…'}</td>
                      <td className="celda-accion">
                        <button type="button" className="btn btn--secundario" onClick={() => navigate(`/profesor/proyectos/${p.id}`)}>
                          Ver detalle
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {filas.length === 0 && (
                  <tr><td colSpan={7} className="texto-suave">Ningún proyecto coincide con los filtros.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        {!cargando && proyectos.length > 0 && (
          <p className="texto-suave nota">Mostrando {filas.length} de {proyectos.length} proyectos de {alumnos} {alumnos === 1 ? 'alumno' : 'alumnos'}.</p>
        )}
      </main>
    </div>
  );
}
