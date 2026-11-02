# Proyectos publicados por el profesor

Profesores y alumnos pueden crear, editar, simular y eliminar sus propios
proyectos. El profesor conserva acceso de lectura a los trabajos de alumnos;
eso no le permite modificar sus componentes, conexiones, topologías o resultados.

Un profesor publica o retira únicamente sus propios proyectos. La publicación
ofrece la topología guardada: las nuevas copias toman su estado actual. Se
pueden publicar ejercicios incompletos para que el alumno los termine; la
validación de viabilidad se exige antes de simular tráfico.

El alumno copia desde el catálogo de proyectos publicados. La operación crea,
en una transacción, un proyecto de su propiedad con topología, componentes y
conexiones nuevos. Conserva parámetros ópticos, cantidades de lotes y posiciones,
reasignando los identificadores de todos los extremos. No copia simulaciones,
resultados ni el estado de publicación. Ante una conexión inconsistente, se
revierte la operación entera.

Cada copia es independiente. Editar, retirar o eliminar el original no cambia
las copias existentes. Un proyecto retirado deja de admitir nuevas copias.

## API

- `GET /proyectos/?propios=true`: proyectos del usuario autenticado.
- `GET /proyectos/`: proyectos del alumno autenticado; para profesores, proyectos
  de alumnos para revisar.
- `PUT /proyectos/{id}/publicacion`, cuerpo `{"publicado": true | false}`:
  publicar o retirar, exclusivamente el profesor dueño.
- `GET /proyectos/publicados`: catálogo autenticado con proyectos publicados de
  profesores, título, descripción y nombre del autor.
- `POST /proyectos/{id}/copiar`: copia para el alumno autenticado. Un borrador,
  proyecto retirado, proyecto de alumno o identificador inexistente devuelve 404.

Los endpoints de edición verifican propiedad para ambos perfiles. El alumno
trabaja sobre la copia, no sobre el original publicado.

## Migración y escenarios anteriores

Al iniciar el backend se agrega `proyecto.publicado` si falta, inicialmente falso
para todos los proyectos existentes. La migración no publica, borra ni reemplaza
proyectos.

Los escenarios desaparecen de la configuración de simulación y de la navegación
del profesor. El inicio deja de cargar escenarios predefinidos automáticamente.
Las tablas, referencias y API anteriores se conservan por compatibilidad con
datos y clientes históricos; las nuevas simulaciones de la interfaz envían sus
usuarios y consumo explícitamente, sin seleccionar escenario.
