import type { ReactNode } from 'react';
import { Logo } from '../components/Logo';

// Columna de presentación compartida por las pantallas de login y registro.
export function AccesoLayout({ children }: { children: ReactNode }) {
  return (
    <div className="acceso">
      <section className="acceso__marca">
        <div className="acceso__logo">
          <Logo size={36} />
          <span>Simulador FTTH-GPON</span>
        </div>
        <div className="acceso__texto">
          <p className="acceso__origen">Laboratorio GIRSYT · UTN Facultad Regional Mendoza</p>
          <h1>Diseñá, configurá y analizá redes de fibra hasta el hogar.</h1>
          <p>
            Construí topologías GPON con OLT, fibra, splitters y ONT/ONU, calculá el presupuesto óptico y estimá la
            capacidad de la red en distintos escenarios de despliegue.
          </p>
        </div>
        <dl className="acceso__datos">
          <div><dt>ITU-T G.984</dt><dd>Arquitectura GPON</dd></div>
          <div><dt>1:2 a 1:64</dt><dd>Relaciones de división</dd></div>
          <div><dt>B+ / C+</dt><dd>Clases de potencia</dd></div>
        </dl>
      </section>
      <section className="acceso__form">{children}</section>
    </div>
  );
}
