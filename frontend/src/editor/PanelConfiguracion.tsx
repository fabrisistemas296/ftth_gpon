import { useEffect, useMemo, useState, type FormEvent } from 'react';
import type { Componente } from '../api/types';
import type { ComponenteInput } from '../api/endpoints';
import { Aviso } from '../components/Aviso';
import { CLASES_POTENCIA, DESCRIPCION, ETIQUETA, PERDIDA_CONECTOR_DB, PERDIDA_EMPALME_DB, PERDIDAS_SPLITTER_DB, RELACIONES, aInput, num, perdidaFibra } from './catalogo';

type Valores = Record<string, string>;

const aTexto = (v: number | string | null) => (v == null ? '' : String(v).replace('.', ','));
const aNumero = (s: string) => {
  const t = s.trim().replace(',', '.');
  if (t === '' || !/^-?\d+(\.\d+)?$/.test(t)) return NaN;
  return Number(t);
};

function valoresIniciales(c: Componente): Valores {
  return {
    potencia_tx_dbm: aTexto(c.potencia_tx_dbm),
    clase_potencia: c.clase_potencia ?? 'B+',
    longitud_km: aTexto(c.longitud_km),
    atenuacion_db_km: aTexto(c.atenuacion_db_km),
    cantidad_conectores: aTexto(c.cantidad_conectores ?? 0),
    cantidad_empalmes: aTexto(c.cantidad_empalmes ?? 0),
    relacion_division: c.relacion_division ?? '1:8',
    sensibilidad_min_dbm: aTexto(c.sensibilidad_min_dbm),
    potencia_sobrecarga_dbm: aTexto(c.potencia_sobrecarga_dbm),
  };
}

// Valida los valores del formulario y arma el cuerpo para PUT /componentes/{id}.
function construir(c: Componente, v: Valores): { datos?: ComponenteInput; errores: Record<string, string> } {
  const errores: Record<string, string> = {};
  const datos = aInput(c);
  const rango = (campo: keyof ComponenteInput, min: number, max: number, entero = false) => {
    const n = aNumero(v[campo as string]);
    if (Number.isNaN(n)) errores[campo as string] = 'Ingresá un número.';
    else if (entero && !Number.isInteger(n)) errores[campo as string] = 'Debe ser un número entero.';
    else if (n < min || n > max) errores[campo as string] = `Debe estar entre ${num(min, entero ? 0 : 2)} y ${num(max, entero ? 0 : 2)}.`;
    return n;
  };

  switch (c.tipo) {
    case 'OLT':
      datos.potencia_tx_dbm = rango('potencia_tx_dbm', -10, 15);
      datos.clase_potencia = v.clase_potencia;
      break;
    case 'FIBRA': {
      const lon = rango('longitud_km', 0, 100);
      if (!errores.longitud_km && lon === 0) errores.longitud_km = 'La longitud debe ser mayor a 0.';
      datos.longitud_km = lon;
      datos.atenuacion_db_km = rango('atenuacion_db_km', 0, 2);
      datos.cantidad_conectores = rango('cantidad_conectores', 0, 50, true);
      datos.cantidad_empalmes = rango('cantidad_empalmes', 0, 100, true);
      break;
    }
    case 'SPLITTER':
      datos.relacion_division = v.relacion_division;
      break;
    case 'ONT_ONU': {
      const sens = rango('sensibilidad_min_dbm', -45, 0);
      const sobre = rango('potencia_sobrecarga_dbm', -45, 10);
      if (!errores.sensibilidad_min_dbm && !errores.potencia_sobrecarga_dbm && sens >= sobre)
        errores.potencia_sobrecarga_dbm = 'Debe ser mayor que la sensibilidad mínima.';
      datos.sensibilidad_min_dbm = sens;
      datos.potencia_sobrecarga_dbm = sobre;
      break;
    }
  }
  return Object.keys(errores).length ? { errores } : { datos, errores };
}

interface Props {
  componente: Componente;
  nombre: string;
  soloLectura?: boolean;
  onAplicar: (datos: ComponenteInput) => Promise<void>;
  onEliminar: () => void;
}

export function PanelConfiguracion({ componente: c, nombre, soloLectura, onAplicar, onEliminar }: Props) {
  const [v, setV] = useState<Valores>(() => valoresIniciales(c));
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorApi, setErrorApi] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  // Se recargan los valores solo si cambia el componente o sus parámetros
  // (moverlo en el lienzo no descarta lo que se está editando).
  const iniciales = useMemo(() => valoresIniciales(c), [c]);
  const firma = `${c.id}|${JSON.stringify(iniciales)}`;
  useEffect(() => {
    setV(valoresIniciales(c));
    setErrores({});
    setErrorApi(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firma]);

  useEffect(() => {
    if (!guardado) return;
    const t = setTimeout(() => setGuardado(false), 2000);
    return () => clearTimeout(t);
  }, [guardado]);

  const sucio = Object.keys(v).some((k) => v[k] !== iniciales[k]);
  const set = (campo: string) => (e: { target: { value: string } }) => {
    setV((x) => ({ ...x, [campo]: e.target.value }));
    setErrores((x) => ({ ...x, [campo]: '' }));
  };

  const aplicar = async (e: FormEvent) => {
    e.preventDefault();
    const { datos, errores: errs } = construir(c, v);
    setErrores(errs);
    if (!datos) return;
    setGuardando(true);
    setErrorApi(null);
    try {
      await onAplicar(datos);
      setGuardado(true);
    } catch (err) {
      setErrorApi(err instanceof Error ? err.message : 'No se pudieron guardar los cambios.');
    } finally {
      setGuardando(false);
    }
  };

  const campoNum = (campo: string, etiqueta: string, unidad?: string, ayuda?: string) => (
    <div className="campo">
      <label htmlFor={`cfg-${campo}`}>{etiqueta}</label>
      <div className={`input-unidad${errores[campo] ? ' input-unidad--error' : ''}`}>
        <input id={`cfg-${campo}`} inputMode="decimal" value={v[campo]} onChange={set(campo)} disabled={soloLectura}
          aria-invalid={!!errores[campo]} aria-describedby={errores[campo] ? `err-${campo}` : undefined} />
        {unidad && <span>{unidad}</span>}
      </div>
      {errores[campo] ? <span id={`err-${campo}`} className="campo__error">{errores[campo]}</span> : ayuda && <span className="campo__ayuda">{ayuda}</span>}
    </div>
  );

  const previaFibra = c.tipo === 'FIBRA'
    ? perdidaFibra({
        longitud_km: aNumero(v.longitud_km) || 0,
        atenuacion_db_km: aNumero(v.atenuacion_db_km) || 0,
        cantidad_conectores: aNumero(v.cantidad_conectores) || 0,
        cantidad_empalmes: aNumero(v.cantidad_empalmes) || 0,
      })
    : null;

  return (
    <form className="panel" onSubmit={aplicar} noValidate>
      <div className="panel__cab">
        <span className="panel__tipo">{ETIQUETA[c.tipo]} · {DESCRIPCION[c.tipo]}</span>
        <h2>{nombre}</h2>
      </div>

      {c.tipo === 'OLT' && (
        <>
          <div className="campo">
            <label htmlFor="cfg-clase">Clase de potencia</label>
            <select id="cfg-clase" value={v.clase_potencia} onChange={set('clase_potencia')} disabled={soloLectura}>
              {CLASES_POTENCIA.map((cl) => <option key={cl} value={cl}>{cl}</option>)}
            </select>
            <span className="campo__ayuda">{v.clase_potencia === 'B+' ? 'B+: +1,5 a +5 dBm, presupuesto ~28 dB.' : 'C+: +3 a +7 dBm, presupuesto ~32 dB.'}</span>
          </div>
          {campoNum('potencia_tx_dbm', 'Potencia de transmisión', 'dBm')}
        </>
      )}

      {c.tipo === 'FIBRA' && (
        <>
          {campoNum('longitud_km', 'Longitud', 'km')}
          {campoNum('atenuacion_db_km', 'Atenuación', 'dB/km', 'Típico en 1490/1550 nm: 0,25 a 0,30 dB/km.')}
          <div className="dos-columnas">
            {campoNum('cantidad_conectores', 'Conectores')}
            {campoNum('cantidad_empalmes', 'Empalmes')}
          </div>
          {previaFibra && (
            <div className="previa">
              <div className="previa__titulo">Pérdida estimada del tramo</div>
              <div><span>Fibra</span><span>{num(previaFibra.fibra)} dB</span></div>
              <div><span>Conectores × {num(PERDIDA_CONECTOR_DB, 1)} dB</span><span>{num(previaFibra.conectores)} dB</span></div>
              <div><span>Empalmes × {num(PERDIDA_EMPALME_DB, 1)} dB</span><span>{num(previaFibra.empalmes)} dB</span></div>
              <div className="previa__total"><span>Total</span><span>{num(previaFibra.total)} dB</span></div>
            </div>
          )}
        </>
      )}

      {c.tipo === 'SPLITTER' && (
        <>
          <div className="campo">
            <label htmlFor="cfg-rel">Relación de división</label>
            <select id="cfg-rel" value={v.relacion_division} onChange={set('relacion_division')} disabled={soloLectura}>
              {RELACIONES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="previa">
            <div className="previa__titulo">Pérdida de inserción</div>
            <div className="previa__total"><span>{v.relacion_division}</span><span>{num(PERDIDAS_SPLITTER_DB[v.relacion_division] ?? 0, 1)} dB</span></div>
          </div>
        </>
      )}

      {c.tipo === 'ONT_ONU' && (
        <>
          {campoNum('sensibilidad_min_dbm', 'Sensibilidad mínima', 'dBm', 'Clase B+: −28 dBm. Clase C+: −32 dBm.')}
          {campoNum('potencia_sobrecarga_dbm', 'Potencia de sobrecarga', 'dBm', 'Típicamente entre −8 y −3 dBm.')}
        </>
      )}

      {errorApi && <Aviso>{errorApi}</Aviso>}
      {guardado && <Aviso tipo="ok">Cambios guardados.</Aviso>}

      {!soloLectura && (
        <div className="panel__acciones">
          <button type="button" className="btn btn--secundario btn--peligro-borde" onClick={onEliminar}>Eliminar</button>
          <button type="submit" className="btn btn--primario" disabled={guardando || !sucio}>
            {guardando ? 'Guardando…' : 'Aplicar cambios'}
          </button>
        </div>
      )}
    </form>
  );
}
