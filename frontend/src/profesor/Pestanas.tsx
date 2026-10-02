import { NavLink } from 'react-router-dom';

export function PestanasProfesor() {
  return (
    <nav className="pestanas" aria-label="Secciones del profesor">
      <NavLink to="/profesor" end className={({ isActive }) => `pestana${isActive ? ' pestana--activa' : ''}`}>
        Proyectos de alumnos
      </NavLink>
      <NavLink to="/profesor/escenarios" className={({ isActive }) => `pestana${isActive ? ' pestana--activa' : ''}`}>
        Escenarios predefinidos
      </NavLink>
    </nav>
  );
}
