import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PestanasProfesor } from '../profesor/Pestanas';

export function PestanasProyectos() {
  const { usuario } = useAuth();
  if (usuario?.rol === 'profesor') return <PestanasProfesor />;
  return (
    <nav className="pestanas" aria-label="Proyectos">
      <NavLink to="/proyectos" end className={({ isActive }) => `pestana${isActive ? ' pestana--activa' : ''}`}>Mis proyectos</NavLink>
      <NavLink to="/proyectos/publicados" className={({ isActive }) => `pestana${isActive ? ' pestana--activa' : ''}`}>Proyectos publicados</NavLink>
    </nav>
  );
}
