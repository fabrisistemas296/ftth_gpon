import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from './AuthContext';
import type { Rol } from '../api/types';
import { Cargando } from '../components/Cargando';

export function RutaProtegida({ rol, children }: { rol?: Rol; children: ReactNode }) {
  const { usuario, cargando } = useAuth();
  if (cargando) return <Cargando texto="Verificando sesión" pantallaCompleta />;
  if (!usuario) return <Navigate to="/login" replace />;
  if (rol && usuario.rol !== rol) return <Navigate to={inicioSegunRol(usuario.rol)} replace />;
  return <>{children}</>;
}

export function inicioSegunRol(rol: Rol) {
  return rol === 'profesor' ? '/profesor' : '/proyectos';
}
