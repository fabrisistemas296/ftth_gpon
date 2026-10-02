import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { inicioSegunRol } from '../auth/RutaProtegida';
import { authApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import { AccesoLayout } from './AccesoLayout';
import { Aviso } from '../components/Aviso';

const MIN_PASSWORD = 8;

export function Registro() {
  const { usuario } = useAuth();
  const navigate = useNavigate();
  const [nombre, setNombre] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to={inicioSegunRol(usuario.rol)} replace />;

  const validar = (): string | null => {
    if (!nombre.trim()) return 'Ingresá tu nombre.';
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return 'Ingresá un email válido.';
    if (password.length < MIN_PASSWORD) return `La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`;
    if (password !== confirmacion) return 'Las contraseñas no coinciden.';
    return null;
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const problema = validar();
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      await authApi.registrar(nombre.trim(), email.trim(), password);
      navigate('/login', { replace: true, state: { registrado: email.trim() } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la cuenta.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <AccesoLayout>
      <form className="tarjeta-form" onSubmit={onSubmit} noValidate>
        <div className="tarjeta-form__cab">
          <h2>Crear cuenta</h2>
          <p>Registrate como alumno para diseñar y simular tus propias redes.</p>
        </div>
        <div className="campo">
          <label htmlFor="nombre">Nombre y apellido</label>
          <input id="nombre" autoComplete="name" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <span className="campo__ayuda">Mínimo {MIN_PASSWORD} caracteres.</span>
        </div>
        <div className="campo">
          <label htmlFor="confirmacion">Repetir contraseña</label>
          <input id="confirmacion" type="password" autoComplete="new-password" value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} />
        </div>
        {error && <Aviso>{error}</Aviso>}
        <button type="submit" className="btn btn--primario btn--grande" disabled={enviando}>
          {enviando ? 'Creando cuenta…' : 'Crear cuenta'}
        </button>
        <p className="tarjeta-form__alt">
          ¿Ya tenés cuenta? <Link to="/login">Iniciá sesión</Link>
        </p>
      </form>
    </AccesoLayout>
  );
}
