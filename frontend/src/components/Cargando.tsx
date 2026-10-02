export function Cargando({ texto = 'Cargando', pantallaCompleta = false }: { texto?: string; pantallaCompleta?: boolean }) {
  return (
    <div className={pantallaCompleta ? 'cargando cargando--full' : 'cargando'} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{texto}…</span>
    </div>
  );
}
