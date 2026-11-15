import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { Usuario } from '../src/api/types';
import { Sesion } from '../src/auth/sesion';

const alumno: Usuario = { id: 10, nombre: 'Tomás', email: 'tomas@example.com', rol: 'alumno', fecha_registro: '' };
const profesor: Usuario = { id: 1, nombre: 'Profesor', email: 'profesor@example.com', rol: 'profesor', fecha_registro: '' };

function pendiente<T>() {
  let resolver!: (valor: T) => void;
  let rechazar!: (error: Error) => void;
  const promesa = new Promise<T>((resolve, reject) => { resolver = resolve; rechazar = reject; });
  return { promesa, resolver, rechazar };
}

function tokens(inicial: string | null = null) {
  let valor = inicial;
  return { get: () => valor, set: (token: string) => { valor = token; }, clear: () => { valor = null; } };
}

test('una consulta anterior del alumno no reemplaza el login del profesor', async () => {
  const anterior = pendiente<Usuario>();
  const almacenamiento = tokens('token-alumno');
  const sesion = new Sesion({
    login: async () => ({ access_token: 'token-profesor', rol: 'profesor', token_type: 'bearer' }),
    yo: async (token) => token === 'token-alumno' ? anterior.promesa : profesor,
  }, almacenamiento);
  const recuperacion = sesion.recuperar();
  sesion.logout();
  await sesion.login(profesor.email, 'clave');
  anterior.resolver(alumno);
  await recuperacion;
  assert.equal(sesion.snapshot().usuario, profesor);
  assert.equal(almacenamiento.get(), 'token-profesor');
});

test('un fallo atrasado de la sesión anterior no borra el token del profesor', async () => {
  const anterior = pendiente<Usuario>();
  const almacenamiento = tokens('token-alumno');
  const sesion = new Sesion({
    login: async () => ({ access_token: 'token-profesor', rol: 'profesor', token_type: 'bearer' }),
    yo: async (token) => token === 'token-alumno' ? anterior.promesa : profesor,
  }, almacenamiento);
  const recuperacion = sesion.recuperar();
  sesion.logout();
  await sesion.login(profesor.email, 'clave');
  anterior.rechazar(new Error('Token anterior vencido'));
  await recuperacion;
  assert.equal(sesion.snapshot().usuario, profesor);
  assert.equal(almacenamiento.get(), 'token-profesor');
});

test('cerrar sesión durante un login pendiente impide que la cuenta vuelva a entrar', async () => {
  const perfil = pendiente<Usuario>();
  const almacenamiento = tokens();
  const sesion = new Sesion({
    login: async () => ({ access_token: 'nuevo', rol: 'profesor', token_type: 'bearer' }),
    yo: () => perfil.promesa,
  }, almacenamiento);
  const login = sesion.login(profesor.email, 'clave');
  const rechazo = assert.rejects(login, /cancelado/);
  await Promise.resolve();
  sesion.logout();
  perfil.resolver(profesor);
  await rechazo;
  assert.deepEqual(sesion.snapshot(), { usuario: null, cargando: false, sesionExpirada: false });
  assert.equal(almacenamiento.get(), null);
});

test('login sólo guarda token y usuario después de verificar el perfil de ese token', async () => {
  const perfil = pendiente<Usuario>();
  const almacenamiento = tokens('anterior');
  const recibidos: string[] = [];
  const sesion = new Sesion({
    login: async () => ({ access_token: 'profesor-nuevo', rol: 'profesor', token_type: 'bearer' }),
    yo: (token) => { recibidos.push(token); return perfil.promesa; },
  }, almacenamiento);
  const login = sesion.login(profesor.email, 'clave');
  await Promise.resolve();
  assert.equal(almacenamiento.get(), null);
  assert.equal(sesion.snapshot().usuario, null);
  assert.equal(sesion.snapshot().cargando, true);
  assert.deepEqual(recibidos, ['profesor-nuevo']);
  perfil.resolver(profesor);
  assert.equal(await login, profesor);
  assert.equal(almacenamiento.get(), 'profesor-nuevo');
});

test('un perfil de otra cuenta nunca se publica como login correcto', async () => {
  const almacenamiento = tokens();
  const sesion = new Sesion({
    login: async () => ({ access_token: 'token-profesor', rol: 'profesor', token_type: 'bearer' }),
    yo: async () => alumno,
  }, almacenamiento);
  await assert.rejects(sesion.login(profesor.email, 'clave'), /otra cuenta/);
  assert.equal(sesion.snapshot().usuario, null);
  assert.equal(almacenamiento.get(), null);
});

test('si falla la carga del perfil no queda una sesión a medio iniciar', async () => {
  const almacenamiento = tokens('viejo');
  const sesion = new Sesion({
    login: async () => ({ access_token: 'nuevo', rol: 'profesor', token_type: 'bearer' }),
    yo: async () => { throw new Error('No disponible'); },
  }, almacenamiento);
  await assert.rejects(sesion.login(profesor.email, 'clave'), /No disponible/);
  assert.equal(sesion.snapshot().usuario, null);
  assert.equal(sesion.snapshot().cargando, false);
  assert.equal(almacenamiento.get(), null);
});

test('la recuperación duplicada de StrictMode ignora la consulta cancelada', async () => {
  const anterior = pendiente<Usuario>();
  const almacenamiento = tokens('guardado');
  let llamadas = 0;
  const sesion = new Sesion({
    login: async () => { throw new Error('No se usa'); },
    yo: async () => ++llamadas === 1 ? anterior.promesa : profesor,
  }, almacenamiento);
  const primera = sesion.recuperar();
  sesion.cancelarPendientes();
  await sesion.recuperar();
  anterior.resolver(alumno);
  await primera;
  assert.equal(sesion.snapshot().usuario, profesor);
});

test('sin token la sesión queda cerrada sin consultar otro usuario', async () => {
  const sesion = new Sesion({
    login: async () => { throw new Error('No se usa'); },
    yo: async () => { throw new Error('No debe llamarse'); },
  }, tokens());
  await sesion.recuperar();
  assert.deepEqual(sesion.snapshot(), { usuario: null, cargando: false, sesionExpirada: false });
});
