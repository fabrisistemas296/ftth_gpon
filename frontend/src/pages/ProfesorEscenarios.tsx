import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { BarraSuperior } from '../components/BarraSuperior';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';
import { Modal } from '../components/Modal';
import { PestanasProfesor } from '../profesor/Pestanas';
import { escenariosAdminApi, escenariosApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Escenario } from '../api/types';
import { fmt } from '../simulacion/trafico';

export function ProfesorEscenarios() {
  const [escenarios, setEscenarios] = useState<Escenario[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const [editando, setEditando] = useState<Escenario | null>(null);
  const [nombre, setNombre] = useState('');
  const [usuarios, setUsuarios] = useState('');
  const [distancia, setDistancia] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setEscenarios(await escenariosApi.listar());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudieron cargar los escenarios.');
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(null), 3500);
    return () => clearTimeout(t);
  }, [aviso]);

  const abrir = (e: Escenario) => {
    setEditando(e);
    setNombre(e.nombre);
    setUsuarios(String(e.cantidad_usuarios_default));
    setDistancia(String(e.distancia_tipica_km).replace('.', ','));
    setDescripcion(e.descripcion ?? '');
    setErrorForm(null);
  };

  const cerrar = useCallback(() => {
    if (!guardando) setEditando(null);
  }, [guardando]);

  const guardar = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!editando) return;
    const n = nombre.trim();
    const u = Number(usuarios);
    const d = Number(distancia.replace(',', '.'));
    if (!n) return setErrorForm('El escenario necesita un nombre.');
    if (escenarios.some((x) => x.id !== editando.id && x.nombre.toLowerCase() === n.toLowerCase()))
      return setErrorForm('Ya existe otro escenario con ese nombre.');
    if (!Number.isInteger(u) || u <= 0) return setErrorForm('La cantidad de usuarios debe ser un entero mayor a 0.');
    if (!Number.isFinite(d) || d <= 0) return setErrorForm('La distancia típica debe ser un número mayor a 0.');
    setGuardando(true);
    setErrorForm(null);
    try {
      const actualizado = await escenariosAdminApi.actualizar(editando.id, {
        nombre: n,
        cantidad_usuarios_default: u,
        distancia_tipica_km: d,
        descripcion: descripcion.trim() || null,
      });
      setEscenarios((es) => es.map((x) => (x.id === actualizado.id ? actualizado : x)));
      setAviso(`Escenario "${actualizado.nombre}" actualizado.`);
      setEditando(null);
    } catch (e) {
      setErrorForm(e instanceof ApiError ? e.message : 'No se pudo guardar el escenario.');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="pagina">
      <BarraSuperior />
      <main className="contenedor">
        <PestanasProfesor />
        <div className="encabezado">
          <div>
            <h1>Escenarios predefinidos</h1>
            <p>Valores de referencia que los alumnos usan como punto de partida al configurar una simulación.</p>
          </div>
        </div>

        {aviso && <Aviso tipo="ok">{aviso}</Aviso>}
        {cargando && <Cargando texto="Cargando escenarios" />}
        {error && <Aviso>{error}</Aviso>}
        {!cargando && !error && escenarios.length === 0 && (
          <div className="vacio">
            <h2>No hay escenarios cargados</h2>
            <p>Los escenarios se cargan en la base de datos con el script cargar_escenarios.py del backend.</p>
          </div>
        )}

        {escenarios.length > 0 && (
          <div className="tabla-envoltorio">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Escenario</th>
                  <th scope="col">Usuarios por defecto</th>
                  <th scope="col">Distancia típica</th>
                  <th scope="col">Descripción</th>
                  <th scope="col"><span className="sr-only">Acción</span></th>
                </tr>
              </thead>
              <tbody>
                {escenarios.map((e) => (
                  <tr key={e.id}>
                    <td><strong>{e.nombre}</strong></td>
                    <td className="mono">{e.cantidad_usuarios_default}</td>
                    <td className="mono">{fmt(e.distancia_tipica_km, e.distancia_tipica_km % 1 ? 1 : 0)} km</td>
                    <td className="texto-suave">{e.descripcion ?? '—'}</td>
                    <td className="celda-accion"><button type="button" className="btn btn--secundario" onClick={() => abrir(e)}>Editar</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <Modal
        titulo="Editar escenario"
        abierto={editando !== null}
        onCerrar={cerrar}
        pie={
          <>
            <button type="button" className="btn btn--secundario" onClick={cerrar} disabled={guardando}>Cancelar</button>
            <button type="submit" form="form-escenario" className="btn btn--primario" disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar cambios'}</button>
          </>
        }
      >
        <form id="form-escenario" className="form-columna" onSubmit={guardar} noValidate>
          <div className="campo">
            <label htmlFor="e-nombre">Nombre</label>
            <input id="e-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </div>
          <div className="dos-columnas">
            <div className="campo">
              <label htmlFor="e-usuarios">Usuarios por defecto</label>
              <input id="e-usuarios" inputMode="numeric" value={usuarios} onChange={(e) => setUsuarios(e.target.value.replace(/[^\d]/g, ''))} />
            </div>
            <div className="campo">
              <label htmlFor="e-dist">Distancia típica (km)</label>
              <input id="e-dist" inputMode="decimal" value={distancia} onChange={(e) => setDistancia(e.target.value)} />
            </div>
          </div>
          <div className="campo">
            <label htmlFor="e-desc">Descripción <span className="opcional">(opcional)</span></label>
            <textarea id="e-desc" rows={3} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
          </div>
          {errorForm && <Aviso>{errorForm}</Aviso>}
        </form>
      </Modal>
    </div>
  );
}
