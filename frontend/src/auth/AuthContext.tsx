import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { authApi } from '../api/endpoints';
import { setUnauthorizedHandler, tokenStore } from '../api/client';
import type { Usuario } from '../api/types';

interface AuthState {
  usuario: Usuario | null;
  cargando: boolean;
  sesionExpirada: boolean;
  login: (email: string, password: string) => Promise<Usuario>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);
  const [sesionExpirada, setSesionExpirada] = useState(false);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUsuario(null);
  }, []);

  // Si el backend responde 401 (token vencido o inválido) se cierra la sesión.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (tokenStore.get()) setSesionExpirada(true);
      tokenStore.clear();
      setUsuario(null);
    });
  }, []);

  // Al cargar la app, si hay token guardado se recupera el usuario.
  useEffect(() => {
    if (!tokenStore.get()) {
      setCargando(false);
      return;
    }
    authApi
      .yo()
      .then(setUsuario)
      .catch(() => tokenStore.clear())
      .finally(() => setCargando(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    tokenStore.set(access_token);
    const u = await authApi.yo();
    setUsuario(u);
    setSesionExpirada(false);
    return u;
  }, []);

  const value = useMemo(
    () => ({ usuario, cargando, sesionExpirada, login, logout }),
    [usuario, cargando, sesionExpirada, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return ctx;
}
