import type { TipoComponente } from '../api/types';

export function IconoComponente({ tipo }: { tipo: TipoComponente }) {
  const comun = { width: 18, height: 18, viewBox: '0 0 18 18', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true };
  return (
    <span className={`icono-comp icono-comp--${tipo.toLowerCase()}`}>
      {tipo === 'OLT' && <svg {...comun}><rect x="2" y="4" width="14" height="10" rx="1.5" /><path d="M5 9h2M10 9h3" /></svg>}
      {tipo === 'FIBRA' && <svg {...comun}><path d="M2 12c3 0 3-6 7-6s4 6 7 6" /></svg>}
      {tipo === 'SPLITTER' && <svg {...comun}><path d="M2 9h5M7 9l8-5M7 9h8M7 9l8 5" /></svg>}
      {tipo === 'ONT_ONU' && <svg {...comun}><path d="M3 8l6-5 6 5v7H3z" /><path d="M7 15v-4h4v4" /></svg>}
    </span>
  );
}
