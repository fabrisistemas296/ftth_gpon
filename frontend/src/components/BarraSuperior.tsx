import { useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Logo } from './Logo';

export function BarraSuperior({ izquierda, acciones }: { izquierda?: ReactNode; acciones?: ReactNode }) {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  const salir = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="topbar">
      <div className="topbar__izq">
        {izquierda ?? (
          <>
            <Logo />
            <span className="topbar__marca">Simulador FTTH-GPON</span>
          </>
        )}
      </div>
      {usuario && (
        <div className="topbar__der">
          {acciones}
          <span className="topbar__usuario">{usuario.nombre}</span>
          <span className={`rol rol--${usuario.rol}`}>{usuario.rol === 'profesor' ? 'Profesor' : 'Alumno'}</span>
          <button type="button" className="btn btn--fantasma" onClick={salir}>
            Cerrar sesión
          </button>
        </div>
      )}
    </header>
  );
}
