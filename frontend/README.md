# Simulador FTTH-GPON — Frontend

Frontend en React + TypeScript (Vite) para la API FastAPI del simulador.

## Requisitos

- Node.js 18 o superior
- El backend en ejecución (por defecto en `http://127.0.0.1:8000`)

## Puesta en marcha

```bash
npm install
cp .env.example .env      # ajustar VITE_API_URL si el backend corre en otra dirección
npm run dev               # abre http://localhost:5173
```

Para generar la versión de producción: `npm run build` (queda en `dist/`).

## Estructura

```
src/
├── api/
│   ├── client.ts      # fetch con JWT, errores de FastAPI legibles, manejo de 401
│   ├── endpoints.ts   # llamadas a /auth, /usuarios, /proyectos, /topologias, /componentes, /conexiones
│   └── types.ts       # tipos equivalentes a los esquemas Pydantic
├── auth/
│   ├── AuthContext.tsx   # sesión: login, logout, usuario actual (/usuarios/me)
│   └── RutaProtegida.tsx # protege rutas por sesión y por rol
├── components/        # barra superior, modal, avisos, badges, carga
├── editor/            # piezas del editor de topología
│   ├── catalogo.ts             # valores iniciales, nombres y constantes (iguales a core/constantes.py)
│   ├── validacion.ts           # reglas de conexión y revisión de la topología
│   ├── NodoComponente.tsx      # nodo del lienzo (OLT, fibra, splitter, ONT/ONU)
│   ├── PanelConfiguracion.tsx  # formulario de parámetros con validación
│   └── Paleta.tsx              # componentes para arrastrar o agregar
├── profesor/          # navegación de las vistas del profesor
├── simulacion/
│   └── trafico.ts     # perfiles de consumo y capacidad PON (iguales a core/constantes.py)
├── pages/             # Login, Registro, Proyectos, Editor, Simulacion, Resultados,
│                      # ProfesorProyectos, ProfesorProyecto, ProfesorEscenarios
├── styles.css         # sistema visual (colores y tipografía de los prototipos)
├── App.tsx            # rutas
└── main.tsx
```

## Estado por partes

- **Parte 1:** inicio de sesión, registro, sesión persistente, rutas protegidas
  por rol y gestión de proyectos del alumno (listar, buscar, crear, editar,
  eliminar). Al crear un proyecto se crea también su topología.
- **Parte 2:** editor de topología con React Flow. Agregar componentes (clic o
  arrastrar), moverlos, conectarlos con validación de reglas, configurar sus
  parámetros, eliminar componentes y conexiones (botón o tecla Supr) y revisión
  de la topología antes de simular. Cada acción se guarda en el backend.
- **Parte 3:** configuración de la simulación (escenario predefinido, cantidad de
  usuarios, tipo de consumo), ejecución con `/simulaciones/{id}/calcular`,
  pantalla de resultados (óptico y tráfico), recálculo e historial.

  Los escenarios se cargan en la base con el script `cargar_escenarios.py`
  del backend (la API no tiene endpoint para crearlos).
- **Parte 4:** vistas del profesor. Listado de los proyectos de todos los alumnos
  con búsqueda y filtro por estado, detalle de cada proyecto en solo lectura
  (topología navegable, parámetros de cada componente, simulaciones y sus
  resultados) y edición del catálogo de escenarios predefinidos.

## Rutas

| Ruta | Rol | Pantalla |
|---|---|---|
| `/login`, `/registro` | público | Acceso |
| `/proyectos` | alumno | Mis proyectos |
| `/proyectos/:id` | alumno | Editor de topología |
| `/proyectos/:id/simulacion` | alumno | Configurar y ejecutar simulación |
| `/proyectos/:id/simulaciones/:simId` | alumno | Resultados |
| `/profesor` | profesor | Proyectos de los alumnos |
| `/profesor/proyectos/:id` | profesor | Detalle del proyecto (solo lectura) |
| `/profesor/proyectos/:id/simulaciones/:simId` | profesor | Resultados (solo lectura) |
| `/profesor/escenarios` | profesor | Escenarios predefinidos |
