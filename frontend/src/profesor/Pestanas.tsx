import { NavLink } from 'react-router-dom';

export function PestanasProfesor() {
  return (
    <nav className="pestanas" aria-label="Secciones del profesor">
      <NavLink to="/proyectos" end className={({ isActive }) => `pestana${isActive ? ' pestana--activa' : ''}`}>
        Mis proyectos
      </NavLink>
      <NavLink to="/profesor" end className={({ isActive }) => `pestana${isActive ? ' pestana--activa' : ''}`}>
        Proyectos de alumnos
      </NavLink>
    </nav>
  );
}
