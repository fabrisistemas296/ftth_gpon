import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import type { Componente, Conexion } from '../src/api/types';
import { componenteVacio, nombresComponentes, perdidaComponente, resumenNodo } from '../src/editor/catalogo';
import { validarConexion, revisarTopologia } from '../src/editor/validacion';
import { PanelConfiguracion } from '../src/editor/PanelConfiguracion';
import { rangoReceptorComun } from '../src/simulacion/trafico';
import { construirAristas } from '../src/editor/aristas';
import { StaticRouter } from 'react-router-dom/server';
import { PestanasProfesor } from '../src/profesor/Pestanas';

function nodo(id: number, tipo: Componente['tipo'], datos: Partial<Componente> = {}): Componente {
  return { ...componenteVacio(1, tipo, 0, 0), id, ...datos };
}
const olt = nodo(1, 'OLT');
const fibra = nodo(2, 'FIBRA');
const splitter = nodo(3, 'SPLITTER');
const lote = nodo(4, 'LOTE_FIBRA_ONT');
const ont = nodo(5, 'ONT_ONU');
const componentes = [olt, fibra, splitter, lote, ont];
function conexion(a: number, b: number, id = 1): Conexion {
  return { id, topologia_id: 1, componente_origen_id: a, componente_destino_id: b };
}
const troncal = [conexion(1, 2, 1), conexion(2, 3, 2)];

test('el profesor navega entre sus proyectos y la revisión de alumnos, sin escenarios', () => {
  const html = renderToStaticMarkup(<StaticRouter location="/proyectos"><PestanasProfesor /></StaticRouter>);
  assert.match(html, /href="\/proyectos"/);
  assert.match(html, /Mis proyectos/);
  assert.match(html, /href="\/profesor"/);
  assert.match(html, /Proyectos de alumnos/);
  assert.doesNotMatch(html, /escenario/i);
});

test('el bloque nuevo incluye cantidad y parámetros completos de cable y receptor', () => {
  assert.equal(lote.cantidad, 8);
  assert.equal(lote.longitud_km, 1);
  assert.equal(lote.atenuacion_db_km, 0.28);
  assert.equal(lote.sensibilidad_min_dbm, -28);
  assert.equal(lote.potencia_sobrecarga_dbm, -8);
  assert.equal(fibra.cantidad, 1);
  assert.equal(ont.cantidad, 1);
});

test('el formulario muestra cantidad, fibra y ONT en un solo panel', () => {
  const html = renderToStaticMarkup(<PanelConfiguracion componente={lote} nombre="Lote" onAplicar={async () => {}} onEliminar={() => {}} />);
  for (const id of ['cantidad', 'longitud_km', 'atenuacion_db_km', 'cantidad_conectores', 'cantidad_empalmes', 'sensibilidad_min_dbm', 'potencia_sobrecarga_dbm']) {
    assert.match(html, new RegExp(`id="cfg-${id}"`));
  }
  assert.match(html, /Fibra de cada par/);
  assert.match(html, /ONT de cada par/);
  assert.match(html, /Pérdida por cable/);
});

test('la pérdida visible es por cable y no aumenta con la cantidad de pares', () => {
  assert.equal(perdidaComponente(lote), perdidaComponente({ ...lote, cantidad: 32 }));
  assert.match(resumenNodo(lote), /8 pares/);
});

test('el bloque consume todas las ocho salidas aunque sea un solo nodo', () => {
  assert.equal(validarConexion(splitter, lote, troncal, componentes), null);
  const usadas = [...troncal, conexion(3, 4, 3)];
  assert.match(validarConexion(splitter, ont, usadas, componentes)!, /requieren 9/);
  // La capacidad se comprueba en ambos sentidos del dibujo.
  assert.match(validarConexion(ont, splitter, usadas, componentes)!, /requieren 9/);
});

test('lotes y ONT individuales suman sus salidas', () => {
  const parcial = { ...lote, cantidad: 7 };
  const cs = componentes.map((c) => c.id === lote.id ? parcial : c);
  assert.equal(validarConexion(splitter, parcial, [...troncal, conexion(3, 5, 3)], cs), null);
  assert.match(validarConexion(splitter, lote, [...troncal, conexion(3, 5, 3)], componentes)!, /requieren 9/);
});

test('la capacidad se reserva incluso antes de unir el splitter a la OLT', () => {
  assert.match(validarConexion(splitter, lote, [conexion(3, 5)], componentes)!, /requieren 9/);
});

test('el lote es terminal y no admite una segunda conexión ni otra ONT', () => {
  assert.match(validarConexion(lote, ont, troncal, componentes)!, /terminal/);
  assert.match(validarConexion(lote, splitter, [...troncal, conexion(4, 1)], componentes)!, /solo enlace/);
});

test('una fibra individual no divide su señal para alimentar ocho pares', () => {
  assert.match(validarConexion(fibra, lote, troncal, componentes)!, /splitter/);
});

test('la revisión exige terminar cada cable y conectar el bloque', () => {
  const cs = componentes.filter((c) => c.tipo !== 'ONT_ONU');
  const nombres = nombresComponentes(cs);
  assert(revisarTopologia(cs, [conexion(1, 2)], nombres).some((p) => /extremos/.test(p.texto)));
  assert(revisarTopologia(cs, troncal, nombres).some((p) => /Lote.*no está conectada/.test(p.texto)));
  assert.equal(revisarTopologia(cs, [...troncal, conexion(3, 4)], nombres).length, 0);
});

test('los lotes participan en la ventana de potencia de resultados', () => {
  assert.deepEqual(rangoReceptorComun([lote]), { sensibilidad: -28, sobrecarga: -8 });
  assert.equal(rangoReceptorComun([lote, { ...ont, sensibilidad_min_dbm: -32 }]), null);
});

test('las aristas indican cuántos pares representa la conexión al bloque', () => {
  const nodes = [splitter, lote].map((c) => ({ id: String(c.id), position: { x: c.id, y: 0 }, data: { componente: c } }));
  assert.equal(construirAristas([conexion(4, 3)], nodes)[0].label, '8 pares');
});
