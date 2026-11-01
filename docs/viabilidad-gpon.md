# Viabilidad GPON antes de simular tráfico

El editor evalúa la red al modificar componentes, conexiones y parámetros del
formulario. La vista previa usa el mismo motor del servidor que la simulación,
con una espera de 250 ms al escribir. No guarda el formulario ni genera
simulaciones. Hay que aplicar los cambios antes de pasar a tráfico.

## Alcance y modelo

- Perfil GPON convencional de **20 km por recorrido completo OLT–ONT**. Se suman
  todos los tramos de fibra de ese recorrido, también con splitters en cascada.
  Dos tramos de 12 km y 9 km exceden el alcance aunque individualmente sean válidos.
- No se suma la fibra de ramas diferentes para aplicar ese límite. Una red puede
  tener más de 20 km de fibra instalada si cada recorrido OLT–ONT cumple el perfil.
- La potencia se calcula como `Tx OLT − pérdidas del recorrido`. Las pérdidas
  incluyen atenuación por kilómetro, conectores, empalmes y splitters.
- Cada ONT debe recibir entre su sensibilidad mínima y su límite de sobrecarga,
  ambos incluidos. Se muestran los márgenes frente a ambos límites.
- Si se configuró clase de potencia en la OLT, las pérdidas tampoco deben superar
  el presupuesto máximo adoptado por el simulador: B+ 28 dB y C+ 32 dB.
- La topología debe ser un árbol conectado con una OLT y al menos una ONT. Las
  fibras conectan dos extremos, las ONT son terminales y los splitters no pueden
  exceder las salidas de su relación de división.

Los 20 km no son un límite universal de la fibra óptica. ITU-T G.984.1 distingue
alcance físico (opciones de 10 y 20 km) de alcance lógico (60 km). Existen perfiles
de alcance extendido, fuera del modelo actual. Ver
[ITU-T G.984.1, apartados 8–10](https://www.itu.int/rec/T-REC-G.984.1-200803-I/en)
y [ITU-T G.984.7, alcance extendido](https://www.itu.int/ITU-T/recommendations/rec.aspx?rec=10887).

Esta es una comprobación didáctica **descendente**, según los parámetros
configurados. No certifica una instalación: faltan transmisor de ONT, receptor de
OLT y atenuación ascendente a 1310 nm para evaluar el retorno. Tampoco se reserva
un margen adicional para envejecimiento, reparaciones o variaciones de equipos.
La cantidad de usuarios y el tipo de consumo se analizan después, en el modelo
de tráfico existente; no alteran la distancia ni el presupuesto óptico.

## API y protección del cálculo

- `GET /topologias/{id}/viabilidad`: evalúa la topología guardada.
- `POST /topologias/{id}/viabilidad`: evalúa una fotografía temporal con
  `componentes` y `conexiones`; no modifica la base de datos.
- Responde `viable`, `no_viable` o `incompleta`, con motivos y resultados por ONT.
  Una falla de potencia o alcance es `no_viable`; un grafo o parámetros que no
  permiten calcular son `incompleta`.
- Ambas rutas exigen autenticación y acceso al proyecto. Un profesor puede
  consultar, como en las demás vistas de lectura.
- Crear o actualizar un tramo exige una longitud finita, mayor que cero y menor
  o igual que 20 km. Un registro histórico más largo se sigue pudiendo evaluar:
  su recorrido resulta no viable y debe corregirse.
- `POST /simulaciones/{id}/calcular` vuelve a evaluar los datos guardados.
  Si algún enlace falla, responde 422 **antes** de calcular tráfico y de guardar
  resultados. La vista previa enviada por el cliente nunca autoriza el cálculo.

No cambia el esquema de la base de datos. Los resultados históricos conservan
sus valores originales; la corrección se aplica a las evaluaciones y cálculos
nuevos. Si falla un recálculo, no se sobrescribe el resultado anterior.

## Verificación

Desde `backend`: `python -m pytest -q`. Incluye casos de 20 km exactos, exceso por
acumulación, ramas independientes, registros históricos inválidos, potencia
insuficiente, sobrecarga, presupuesto de clase, ciclos, permisos y bloqueo real
del motor de tráfico. La fixture desactiva la inicialización de producción para
que el arranque de TestClient tampoco acceda a la base real.

Desde `frontend`: `npm ci` y `npm run build`.
