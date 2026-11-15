import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react';
import { authApi } from '../api/endpoints';
import { setUnauthorizedHandler, tokenStore } from '../api/client';
import type { Usuario } from '../api/types';
import { Sesion } from './sesion';

interface AuthState {
  usuario: Usuario | null;
  cargando: boolean;
  sesionExpirada: boolean;
  login: (email: string, password: string) => Promise<Usuario>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sesion] = useState(() => new Sesion(authApi, tokenStore));
  const estado = useSyncExternalStore(sesion.suscribir, sesion.snapshot, sesion.snapshot);

  useEffect(() => {
    setUnauthorizedHandler(sesion.expirar);
    void sesion.recuperar();
    return () => {
      sesion.cancelarPendientes();
      setUnauthorizedHandler(null);
    };
  }, [sesion]);

  const value = useMemo(
    () => ({ ...estado, login: sesion.login, logout: sesion.logout }),
    [estado, sesion],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return ctx;
}
