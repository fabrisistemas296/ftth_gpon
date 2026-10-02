import { api } from './client';
import type {
  Componente, Conexion, Escenario, LoginResponse, Proyecto, ProyectoDetalle, ProyectoInput, ResultadoCalculo,
  Simulacion, SimulacionInput, Topologia, Usuario,
} from './types';

// Las rutas llevan la barra final tal como están declaradas en los
// routers de FastAPI, para evitar redirecciones 307.

export const authApi = {
  login: (email: string, password: string) =>
    api<LoginResponse>('/auth/login', { method: 'POST', form: { username: email, password }, auth: false }),
  registrar: (nombre: string, email: string, password: string) =>
    api<Usuario>('/usuarios/', { method: 'POST', json: { nombre, email, password }, auth: false }),
  yo: () => api<Usuario>('/usuarios/me'),
};

export const proyectosApi = {
  listar: () => api<Proyecto[]>('/proyectos/'),
  detalle: (id: number) => api<ProyectoDetalle>(`/proyectos/${id}/detalle`),
  crear: (datos: ProyectoInput) => api<Proyecto>('/proyectos/', { method: 'POST', json: datos }),
  actualizar: (id: number, datos: ProyectoInput) => api<Proyecto>(`/proyectos/${id}`, { method: 'PUT', json: datos }),
  eliminar: (id: number) => api<Proyecto>(`/proyectos/${id}`, { method: 'DELETE' }),
};

export const topologiasApi = {
  crear: (proyecto_id: number) => api<Topologia>('/topologias/', { method: 'POST', json: { proyecto_id } }),
};

export type ComponenteInput = Omit<Componente, 'id'>;

export const componentesApi = {
  crear: (datos: ComponenteInput) => api<Componente>('/componentes/', { method: 'POST', json: datos }),
  actualizar: (id: number, datos: ComponenteInput) => api<Componente>(`/componentes/${id}`, { method: 'PUT', json: datos }),
  eliminar: (id: number) => api<Componente>(`/componentes/${id}`, { method: 'DELETE' }),
};

export const conexionesApi = {
  crear: (topologia_id: number, componente_origen_id: number, componente_destino_id: number) =>
    api<Conexion>('/conexiones/', { method: 'POST', json: { topologia_id, componente_origen_id, componente_destino_id } }),
  eliminar: (id: number) => api<{ message: string }>(`/conexiones/${id}`, { method: 'DELETE' }),
};

export const escenariosApi = {
  listar: () => api<Escenario[]>('/escenarios/'),
};

export const simulacionesApi = {
  crear: (datos: SimulacionInput) => api<Simulacion>('/simulaciones/', { method: 'POST', json: datos }),
  calcular: (id: number) => api<ResultadoCalculo>(`/simulaciones/${id}/calcular`, { method: 'POST' }),
  listar: (proyectoId: number) => api<Simulacion[]>(`/simulaciones/?proyecto_id=${proyectoId}`),
};

export const usuariosApi = {
  listar: () => api<Usuario[]>('/usuarios/'),
};

export type EscenarioInput = Omit<Escenario, 'id'>;

export const escenariosAdminApi = {
  actualizar: (id: number, datos: EscenarioInput) => api<Escenario>(`/escenarios/${id}`, { method: 'PUT', json: datos }),
};
