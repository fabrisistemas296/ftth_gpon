import type { LoginResponse, Usuario } from '../api/types';

interface EstadoSesion {
  usuario: Usuario | null;
  cargando: boolean;
  sesionExpirada: boolean;
}

interface Autenticacion {
  login: (email: string, password: string) => Promise<LoginResponse>;
  yo: (token: string) => Promise<Usuario>;
}

interface Tokens {
  get: () => string | null;
  set: (token: string) => void;
  clear: () => void;
}

// Cada cambio de cuenta invalida las respuestas pendientes de la sesión anterior.
export class Sesion {
  private version = 0;
  private estado: EstadoSesion = { usuario: null, cargando: true, sesionExpirada: false };
  private oyentes = new Set<() => void>();

  constructor(private auth: Autenticacion, private tokens: Tokens) {}

  snapshot = () => this.estado;
  suscribir = (oyente: () => void) => {
    this.oyentes.add(oyente);
    return () => { this.oyentes.delete(oyente); };
  };

  private actualizar(estado: EstadoSesion) {
    this.estado = estado;
    this.oyentes.forEach((oyente) => oyente());
  }

  cancelarPendientes = () => { this.version++; };

  logout = () => {
    this.cancelarPendientes();
    this.tokens.clear();
    this.actualizar({ usuario: null, cargando: false, sesionExpirada: false });
  };

  expirar = () => {
    this.logout();
    this.actualizar({ usuario: null, cargando: false, sesionExpirada: true });
  };

  recuperar = async () => {
    const version = ++this.version;
    const token = this.tokens.get();
    if (!token) {
      this.actualizar({ usuario: null, cargando: false, sesionExpirada: false });
      return;
    }
    this.actualizar({ usuario: null, cargando: true, sesionExpirada: false });
    try {
      const usuario = await this.auth.yo(token);
      if (version === this.version && this.tokens.get() === token)
        this.actualizar({ usuario, cargando: false, sesionExpirada: false });
    } catch {
      if (version === this.version && this.tokens.get() === token) this.logout();
    }
  };

  login = async (email: string, password: string): Promise<Usuario> => {
    const version = ++this.version;
    this.tokens.clear();
    this.actualizar({ usuario: null, cargando: true, sesionExpirada: false });
    try {
      const credenciales = await this.auth.login(email.trim(), password);
      if (version !== this.version) throw new Error('El inicio de sesión fue cancelado.');
      const usuario = await this.auth.yo(credenciales.access_token);
      if (version !== this.version) throw new Error('El inicio de sesión fue cancelado.');
      if (usuario.email.toLowerCase() !== email.trim().toLowerCase() || usuario.rol !== credenciales.rol)
        throw new Error('El servidor devolvió otra cuenta. Volvé a iniciar sesión.');
      // Se publica la sesión únicamente cuando token y perfil están verificados.
      this.tokens.set(credenciales.access_token);
      this.actualizar({ usuario, cargando: false, sesionExpirada: false });
      return usuario;
    } catch (error) {
      if (version === this.version) {
        this.tokens.clear();
        this.actualizar({ usuario: null, cargando: false, sesionExpirada: false });
      }
      throw error;
    }
  };
}
