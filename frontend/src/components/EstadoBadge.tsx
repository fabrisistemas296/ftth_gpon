export type Estado = 'operativo' | 'fuera_de_rango' | 'sin_simular';

const TEXTO: Record<Estado, string> = {
  operativo: 'Operativo',
  fuera_de_rango: 'Fuera de rango',
  sin_simular: 'Sin simular',
};

export function EstadoBadge({ estado }: { estado: Estado }) {
  return <span className={`badge badge--${estado}`}>{TEXTO[estado]}</span>;
}
