import { test } from 'node:test';
import assert from 'node:assert/strict';
import { api, setUnauthorizedHandler, tokenStore } from '../src/api/client';

function preparar(t: { after: (fn: () => void) => void }) {
  const fetchAnterior = globalThis.fetch;
  const storageAnterior = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  const datos = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: (key: string) => datos.get(key) ?? null,
    setItem: (key: string, value: string) => { datos.set(key, value); },
    removeItem: (key: string) => { datos.delete(key); },
  } });
  t.after(() => {
    globalThis.fetch = fetchAnterior;
    setUnauthorizedHandler(null);
    if (storageAnterior) Object.defineProperty(globalThis, 'localStorage', storageAnterior);
    else Reflect.deleteProperty(globalThis, 'localStorage');
  });
}

test('un 401 pendiente del alumno no invalida la sesión nueva del profesor', async (t) => {
  preparar(t);
  let responder!: (r: Response) => void;
  let expiraciones = 0;
  globalThis.fetch = () => new Promise((resolve) => { responder = resolve; });
  setUnauthorizedHandler(() => { expiraciones++; tokenStore.clear(); });
  tokenStore.set('alumno');
  const anterior = api('/usuarios/me');
  const rechazo = assert.rejects(anterior, /Token vencido/);
  tokenStore.set('profesor');
  responder(new Response(JSON.stringify({ detail: 'Token vencido' }), { status: 401 }));
  await rechazo;
  assert.equal(expiraciones, 0);
  assert.equal(tokenStore.get(), 'profesor');
});

test('un 401 del token actual sí cierra su sesión', async (t) => {
  preparar(t);
  let expiraciones = 0;
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Token vencido' }), { status: 401 });
  setUnauthorizedHandler(() => { expiraciones++; tokenStore.clear(); });
  tokenStore.set('actual');
  await assert.rejects(api('/usuarios/me'), /Token vencido/);
  assert.equal(expiraciones, 1);
  assert.equal(tokenStore.get(), null);
});

test('la consulta de identidad usa el token explícito y evita la caché', async (t) => {
  preparar(t);
  let opciones: RequestInit | undefined;
  globalThis.fetch = async (_url, opts) => { opciones = opts; return new Response('{}'); };
  tokenStore.set('anterior');
  await api('/usuarios/me', { token: 'nuevo' });
  assert.equal((opciones?.headers as Record<string, string>).Authorization, 'Bearer nuevo');
  assert.equal(opciones?.cache, 'no-store');
});
