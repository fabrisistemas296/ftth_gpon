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

Para ejecutar las pruebas del editor: `npm test`.

## Proyectos del profesor y copias para alumnos

Ambos perfiles tienen **Mis proyectos**: pueden crear, editar, eliminar y
simular sus propias redes. El profesor también puede revisar los proyectos de
alumnos en modo de lectura desde **Proyectos de alumnos**.

El profesor usa **Publicar** en la tarjeta de un proyecto para ofrecer su
topología guardada a los alumnos. Puede usar **Retirar publicación** para dejar
de ofrecerla. Los proyectos nuevos son borradores hasta publicarlos.

El alumno entra a **Proyectos publicados** y elige **Copiar a mis proyectos**.
Se abre su propia copia, con los componentes, lotes, parámetros, posiciones y
conexiones del original. La copia conserva su independencia al editar, retirar
o borrar el original. Las simulaciones se ejecutan sobre cada proyecto y no se
copian del profesor.

La configuración de simulación pide cantidad de usuarios y tipo de consumo; ya
no ofrece escenarios predefinidos. Reiniciar el backend aplica la migración de
publicación y mantiene los proyectos existentes como borradores.

## Lote fibra + ONT

La paleta incluye un bloque **Lote fibra + ONT**. Su cantidad representa pares
completos: cada cable termina en su propia ONT y todos comparten los parámetros
configurados. El panel reúne cantidad, longitud, atenuación, conectores y empalmes
por cable, sensibilidad y sobrecarga de cada ONT.

Conectá el bloque a un splitter con suficientes salidas. Un lote de 8 pares usa
8 salidas; un splitter 1:8 ocupado por ese lote no admite otra ONT ni otro cable
de salida. La cantidad aparece en el nodo y en su conexión.

Las longitudes y pérdidas se calculan por recorrido. Ocho cables de 2 km
representan ocho recorridos de 2 km, y cada uno suma también los tramos anteriores
al splitter. La viabilidad en vivo cuenta las ONT del lote y verifica potencia,
alcance y conexiones antes de habilitar tráfico.

Al reiniciar el backend se agrega automáticamente el campo `cantidad` a las bases
existentes, con valor 1 para los componentes anteriores, conservando sus datos.
Ver [criterios de viabilidad](../docs/viabilidad-gpon.md).

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
  y gestión de proyectos propios (listar, buscar, crear, editar,
  eliminar). Al crear un proyecto se crea también su topología.
- **Parte 2:** editor de topología con React Flow. Agregar componentes (clic o
  arrastrar), moverlos, conectarlos con validación de reglas, configurar sus
  parámetros, eliminar componentes y conexiones (botón o tecla Supr) y revisión
  de la topología antes de simular. Cada acción se guarda en el backend.
- **Parte 3:** configuración de la simulación (cantidad de usuarios y tipo de
  consumo), ejecución con `/simulaciones/{id}/calcular`,
  pantalla de resultados (óptico y tráfico), recálculo e historial.

- **Parte 4:** vistas del profesor. Listado de los proyectos de todos los alumnos
  con búsqueda y filtro por estado, detalle de cada proyecto en solo lectura
  (topología navegable, parámetros de cada componente, simulaciones y sus
  resultados), proyectos propios y publicación de topologías para copiar.

## Rutas

| Ruta | Rol | Pantalla |
|---|---|---|
| `/login`, `/registro` | público | Acceso |
| `/proyectos` | alumno y profesor | Mis proyectos |
| `/proyectos/publicados` | alumno | Copiar proyectos del profesor |
| `/proyectos/:id` | dueño | Editor de topología |
| `/proyectos/:id/simulacion` | dueño | Configurar y ejecutar simulación |
| `/proyectos/:id/simulaciones/:simId` | dueño | Resultados |
| `/profesor` | profesor | Proyectos de los alumnos |
| `/profesor/proyectos/:id` | profesor | Detalle del proyecto (solo lectura) |
| `/profesor/proyectos/:id/simulaciones/:simId` | profesor | Resultados (solo lectura) |
