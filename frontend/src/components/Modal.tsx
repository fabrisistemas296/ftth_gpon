import { useEffect, useRef, type ReactNode } from 'react';

interface Props {
  titulo: string;
  abierto: boolean;
  onCerrar: () => void;
  children: ReactNode;
  pie?: ReactNode;
}

export function Modal({ titulo, abierto, onCerrar, children, pie }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    const anterior = document.activeElement as HTMLElement | null;
    const primero = ref.current?.querySelector<HTMLElement>('input, textarea, select, button');
    primero?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCerrar();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      anterior?.focus();
    };
  }, [abierto, onCerrar]);

  if (!abierto) return null;
  return (
    <div className="modal-fondo" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-titulo" ref={ref}>
        <div className="modal__cab">
          <h2 id="modal-titulo">{titulo}</h2>
          <button type="button" className="btn-icono" aria-label="Cerrar" onClick={onCerrar}>
            <svg width="18" height="18" viewBox="0 0 18 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M4 4l10 10M14 4L4 14" />
            </svg>
          </button>
        </div>
        <div className="modal__cuerpo">{children}</div>
        {pie && <div className="modal__pie">{pie}</div>}
      </div>
    </div>
  );
}
