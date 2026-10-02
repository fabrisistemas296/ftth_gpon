// Cliente HTTP: agrega el token JWT, traduce los errores de FastAPI a
// mensajes legibles y avisa cuando la sesión expira (401).

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

const TOKEN_KEY = 'ftth_token';

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

// FastAPI devuelve `detail` como texto (HTTPException) o como lista de
// errores de validación (422). Se convierte en un único mensaje.
function mensajeDeError(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((e: { msg?: string; loc?: (string | number)[] }) => {
        const campo = e.loc?.filter((p) => p !== 'body').join('.');
        const msg = (e.msg ?? 'Dato inválido').replace(/^Value error, /, '');
        return campo ? `${campo}: ${msg}` : msg;
      })
      .join(' · ');
  }
  if (status >= 500) return 'El servidor tuvo un error. Probá de nuevo en unos segundos.';
  return `Error ${status}`;
}

interface Opciones {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  json?: unknown;
  form?: Record<string, string>;
  auth?: boolean;
}

export async function api<T>(path: string, opts: Opciones = {}): Promise<T> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (opts.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = new URLSearchParams(opts.form).toString();
  }

  const token = tokenStore.get();
  if (opts.auth !== false && token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: opts.method ?? 'GET', headers, body });
  } catch {
    throw new ApiError(0, `No se pudo conectar con el servidor (${API_URL}). Verificá que el backend esté en ejecución.`);
  }

  const texto = await res.text();
  let data: unknown = null;
  if (texto) {
    try {
      data = JSON.parse(texto);
    } catch {
      data = texto;
    }
  }

  if (!res.ok) {
    if (res.status === 401 && opts.auth !== false && onUnauthorized) onUnauthorized();
    throw new ApiError(res.status, mensajeDeError(res.status, data));
  }
  return data as T;
}
