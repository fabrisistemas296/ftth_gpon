import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { ProyectoPublicado } from '../api/types';
import { proyectosApi } from '../api/endpoints';
import { BarraSuperior } from '../components/BarraSuperior';
import { PestanasProyectos } from '../components/PestanasProyectos';
import { Aviso } from '../components/Aviso';
import { Cargando } from '../components/Cargando';

export function ProyectosPublicados() {
  const navigate = useNavigate();
  const [proyectos, setProyectos] = useState<ProyectoPublicado[]>([]);
  const [cargando, setCargando] = useState(true);
  const [copiando, setCopiando] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try { setProyectos(await proyectosApi.publicados()); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudieron cargar los proyectos publicados.'); }
    finally { setCargando(false); }
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  const copiar = async (p: ProyectoPublicado) => {
    setCopiando(p.id);
    setError(null);
    try {
      const copia = await proyectosApi.copiar(p.id);
      navigate(`/proyectos/${copia.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo copiar el proyecto.');
    } finally { setCopiando(null); }
  };

  return (
    <div className="pagina">
      <BarraSuperior />
      <main className="contenedor">
        <PestanasProyectos />
        <div className="encabezado"><div>
          <h1>Proyectos publicados</h1>
          <p>Copiá un proyecto del profesor a tu lista. La copia incluye la topología completa y podés modificarla y simularla.</p>
        </div></div>
        {cargando && <Cargando texto="Cargando proyectos publicados" />}
        {error && <Aviso>{error} <button type="button" className="enlace" onClick={() => void cargar()} disabled={copiando !== null}>Actualizar lista</button></Aviso>}
        {!cargando && !error && proyectos.length === 0 && <div className="vacio"><h2>Todavía no hay proyectos publicados</h2><p>Los proyectos aparecerán acá cuando un profesor los publique.</p></div>}
        <div className="grilla-proyectos">
          {proyectos.map((p) => <article key={p.id} className="tarjeta-proyecto">
            <div className="tarjeta-proyecto__cab"><h2>{p.nombre}</h2></div>
            <p className="texto-suave">Publicado por {p.autor}</p>
            <p className="tarjeta-proyecto__desc">{p.descripcion || 'Sin descripción.'}</p>
            <button type="button" className="btn btn--primario" disabled={copiando !== null} onClick={() => void copiar(p)}>
              {copiando === p.id ? 'Copiando…' : 'Copiar a mis proyectos'}
            </button>
          </article>)}
        </div>
      </main>
    </div>
  );
}
