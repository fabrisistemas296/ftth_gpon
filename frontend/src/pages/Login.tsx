import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { inicioSegunRol } from '../auth/RutaProtegida';
import { AccesoLayout } from './AccesoLayout';
import { Aviso } from '../components/Aviso';
import { ApiError } from '../api/client';

export function Login() {
  const { usuario, login, sesionExpirada } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const registrado = (location.state as { registrado?: string } | null)?.registrado;

  const [email, setEmail] = useState(registrado ?? '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to={inicioSegunRol(usuario.rol)} replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const u = await login(email.trim(), password);
      navigate(inicioSegunRol(u.rol), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo iniciar sesión.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <AccesoLayout>
      <form className="tarjeta-form" onSubmit={onSubmit} noValidate>
        <div className="tarjeta-form__cab">
          <h2>Iniciar sesión</h2>
          <p>Ingresá con tu cuenta para acceder a tus proyectos.</p>
        </div>
        {registrado && !error && <Aviso tipo="ok">Cuenta creada. Ya podés iniciar sesión.</Aviso>}
        {sesionExpirada && !error && !registrado && <Aviso tipo="info">Tu sesión expiró. Volvé a iniciar sesión.</Aviso>}
        <div className="campo">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <Aviso>{error}</Aviso>}
        <button type="submit" className="btn btn--primario btn--grande" disabled={enviando || !email || !password}>
          {enviando ? 'Ingresando…' : 'Iniciar sesión'}
        </button>
        <p className="tarjeta-form__alt">
          ¿No tenés cuenta? <Link to="/registro">Registrate</Link>
        </p>
        <p className="tarjeta-form__nota">
          Las cuentas nuevas se crean con rol Alumno. El rol Profesor lo asigna el administrador del sistema.
        </p>
      </form>
    </AccesoLayout>
  );
}
