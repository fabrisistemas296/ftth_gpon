// SQLite guarda las fechas como "YYYY-MM-DD HH:MM:SS" en UTC.
export function parseFecha(valor: string): Date {
  const iso = valor.includes('T') ? valor : valor.replace(' ', 'T');
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
}

export function formatoFecha(valor: string): string {
  const d = parseFecha(valor);
  if (Number.isNaN(d.getTime())) return valor;
  const hoy = new Date();
  const mismoDia = d.toDateString() === hoy.toDateString();
  const hora = d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
  if (mismoDia) return `hoy, ${hora}`;
  return `${d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })} ${hora}`;
}
