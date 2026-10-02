import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { RutaProtegida, inicioSegunRol } from './auth/RutaProtegida';
import { Login } from './pages/Login';
import { Registro } from './pages/Registro';
import { Proyectos } from './pages/Proyectos';
import { Editor } from './pages/Editor';
import { Simulacion } from './pages/Simulacion';
import { Resultados } from './pages/Resultados';
import { ProfesorProyectos } from './pages/ProfesorProyectos';
import { ProfesorProyecto } from './pages/ProfesorProyecto';
import { ProfesorEscenarios } from './pages/ProfesorEscenarios';
import { NoEncontrada } from './pages/NoEncontrada';
import { Cargando } from './components/Cargando';

function Inicio() {
  const { usuario, cargando } = useAuth();
  if (cargando) return <Cargando texto="Cargando" pantallaCompleta />;
  return <Navigate to={usuario ? inicioSegunRol(usuario.rol) : '/login'} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
      <Route path="/proyectos" element={<RutaProtegida rol="alumno"><Proyectos /></RutaProtegida>} />
      <Route
        path="/proyectos/:id"
        element={<RutaProtegida rol="alumno"><Editor /></RutaProtegida>}
      />
      <Route
        path="/proyectos/:id/simulacion"
        element={<RutaProtegida rol="alumno"><Simulacion /></RutaProtegida>}
      />
      <Route
        path="/proyectos/:id/simulaciones/:simId"
        element={<RutaProtegida rol="alumno"><Resultados /></RutaProtegida>}
      />
      <Route
        path="/profesor"
        element={<RutaProtegida rol="profesor"><ProfesorProyectos /></RutaProtegida>}
      />
      <Route path="/profesor/escenarios" element={<RutaProtegida rol="profesor"><ProfesorEscenarios /></RutaProtegida>} />
      <Route path="/profesor/proyectos/:id" element={<RutaProtegida rol="profesor"><ProfesorProyecto /></RutaProtegida>} />
      <Route
        path="/profesor/proyectos/:id/simulaciones/:simId"
        element={<RutaProtegida rol="profesor"><Resultados /></RutaProtegida>}
      />
      <Route path="*" element={<NoEncontrada />} />
    </Routes>
  );
}
