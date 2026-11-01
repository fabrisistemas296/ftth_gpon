import { useEffect, useState } from 'react';
import { topologiasApi } from '../api/endpoints';
import type { Componente, Conexion, Viabilidad } from '../api/types';

export function useViabilidad(
  topologiaId: number | null,
  componentes: Componente[],
  conexiones: Conexion[],
  errorFormulario: string | null = null,
) {
  // Mover el dibujo no cambia la viabilidad; sí lo hacen sus parámetros y conexiones.
  const firma = JSON.stringify({
    topologiaId,
    componentes: componentes.map((c) => ({ ...c, posicion_x: 0, posicion_y: 0 })),
    conexiones,
    errorFormulario,
  });
  const [respuesta, setRespuesta] = useState<{ firma: string; datos?: Viabilidad; error?: string } | null>(null);

  useEffect(() => {
    const previa = JSON.parse(firma);
    if (previa.topologiaId == null || previa.errorFormulario) return;
    let vigente = true;
    const t = setTimeout(() => {
      topologiasApi.viabilidad(previa.topologiaId, { componentes: previa.componentes, conexiones: previa.conexiones })
        .then((datos) => { if (vigente) setRespuesta({ firma, datos }); })
        .catch((e: unknown) => {
          if (vigente) setRespuesta({ firma, error: e instanceof Error ? e.message : 'No se pudo comprobar la viabilidad.' });
        });
    }, 250);
    return () => { vigente = false; clearTimeout(t); };
  }, [firma]);

  // Nunca habilitar tráfico con el resultado de parámetros anteriores.
  const actual = respuesta?.firma === firma ? respuesta : null;
  return {
    datos: errorFormulario ? undefined : actual?.datos,
    error: errorFormulario ?? actual?.error,
    calculando: topologiaId != null && !errorFormulario && !actual,
    viable: !errorFormulario && actual?.datos?.estado === 'viable',
  };
}
