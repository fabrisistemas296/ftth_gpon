import { Link } from 'react-router-dom';

export function NoEncontrada() {
  return (
    <div className="vacio vacio--full">
      <h2>Esta página no existe</h2>
      <p>Revisá la dirección o volvé al inicio.</p>
      <Link className="btn btn--primario" to="/">Ir al inicio</Link>
    </div>
  );
}
