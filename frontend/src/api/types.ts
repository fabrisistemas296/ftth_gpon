// Tipos que reflejan los esquemas Pydantic del backend (app/schemas).

export type Rol = 'alumno' | 'profesor';

export interface Usuario {
  id: number;
  nombre: string;
  email: string;
  rol: Rol;
  fecha_registro: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  rol: Rol;
}

export interface Proyecto {
  id: number;
  nombre: string;
  descripcion: string | null;
  usuario_id: number;
  fecha_creacion: string;
  fecha_modificacion: string;
}

export interface ProyectoInput {
  nombre: string;
  descripcion: string | null;
}

export type TipoComponente = 'OLT' | 'FIBRA' | 'SPLITTER' | 'ONT_ONU';

export interface Componente {
  id: number;
  topologia_id: number;
  tipo: TipoComponente;
  posicion_x: number;
  posicion_y: number;
  potencia_tx_dbm: number | null;
  clase_potencia: string | null;
  longitud_km: number | null;
  atenuacion_db_km: number | null;
  cantidad_conectores: number | null;
  cantidad_empalmes: number | null;
  relacion_division: string | null;
  sensibilidad_min_dbm: number | null;
  potencia_sobrecarga_dbm: number | null;
}

export interface Conexion {
  id: number;
  topologia_id: number;
  componente_origen_id: number;
  componente_destino_id: number;
}

export interface Topologia {
  id: number;
  proyecto_id: number;
}

export interface ResultadoOptico {
  id: number;
  simulacion_id: number;
  perdida_total_db: number;
  potencia_recibida_dbm: number;
  estado_operativo: 'operativo' | 'fuera_de_rango' | string;
}

export interface ResultadoTrafico {
  id: number;
  simulacion_id: number;
  throughput_mbps: number;
  throughput_por_usuario_mbps: number | null;
  utilizacion_pct: number;
  congestion: number;
  tiempo_respuesta_ms: number | null;
}

export type TipoConsumo = 'web' | 'streaming' | 'videoconferencia' | 'descarga';

export interface SimulacionDetalle {
  id: number;
  escenario_id: number | null;
  fecha_ejecucion: string;
  cantidad_usuarios: number;
  tipo_consumo: TipoConsumo;
  resultado_optico: ResultadoOptico | null;
  resultado_trafico: ResultadoTrafico | null;
}

export interface ProyectoDetalle extends Proyecto {
  topologia: (Topologia & { componentes: Componente[]; conexiones: Conexion[] }) | null;
  simulaciones: SimulacionDetalle[];
}

export interface Escenario {
  id: number;
  nombre: string;
  cantidad_usuarios_default: number;
  distancia_tipica_km: number;
  descripcion: string | null;
}

export interface Simulacion {
  id: number;
  proyecto_id: number;
  escenario_id: number | null;
  fecha_ejecucion: string;
  cantidad_usuarios: number;
  tipo_consumo: TipoConsumo;
}

export interface SimulacionInput {
  proyecto_id: number;
  escenario_id: number | null;
  cantidad_usuarios: number | null;
  tipo_consumo: TipoConsumo;
}

export interface ResultadoCalculo {
  resultado_optico: ResultadoOptico;
  resultado_trafico: ResultadoTrafico;
}
