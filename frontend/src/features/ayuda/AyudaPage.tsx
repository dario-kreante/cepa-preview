/**
 * AyudaPage — manual de uso breve y enlace al portal de incidencias (COMP-2609-01).
 *
 * Destino común del botón "Ayuda y soporte" del menú lateral y del ícono (?) del
 * Topbar. Accesible para todos los perfiles.
 */
import type { ReactNode } from "react";
import { ExternalLink, LifeBuoy } from "lucide-react";
import { Card } from "@/components/ui/card";

export const URL_PORTAL_INCIDENCIAS = "https://cepa-incidencias.dramirez-gysactiva.chatgpt.site";

interface Seccion {
  titulo: string;
  contenido: ReactNode;
}

const SECCIONES: Seccion[] = [
  {
    titulo: "Buscar un paciente",
    contenido: (
      <>
        <p>
          Escribe en el buscador del menú lateral y presiona Enter, o usa el buscador de{" "}
          <strong>Ingresos y pacientes</strong>. Se puede buscar por RUT, folio, nombre o{" "}
          <strong>ID SALUTEM</strong>.
        </p>
        <p>Haz clic en un resultado para abrir su ficha con licencias, fármacos, controles y atenciones SALUTEM.</p>
      </>
    ),
  },
  {
    titulo: "Crear un ingreso",
    contenido: (
      <p>
        En <strong>Ingresos y pacientes</strong>, usa el botón <strong>Nuevo ingreso</strong> (perfiles
        Coordinación y Administrativo). Completa los datos del paciente y del caso; el folio se asigna
        según el programa. Al guardar, el ingreso queda activo.
      </p>
    ),
  },
  {
    titulo: "Registrar una licencia médica",
    contenido: (
      <p>
        Desde <strong>Licencias médicas</strong> o desde la pestaña Licencias de la ficha del paciente.
        Ingresa el folio de la licencia, el reposo y las fechas. Si subes el PDF en{" "}
        <strong>Lectura de PDF</strong>, el sistema propone los datos para que los revises.
      </p>
    ),
  },
  {
    titulo: "Controles médicos",
    contenido: (
      <p>
        En <strong>Controles médicos</strong> se registran y revisan los controles de cada ingreso. Los
        controles con etiqueta <strong>SALUTEM</strong> se crean solos a partir de las atenciones de
        Médico/a registradas en SALUTEM; no hace falta ingresarlos a mano.
      </p>
    ),
  },
  {
    titulo: "Gestión de fármacos",
    contenido: (
      <p>
        En <strong>Gestión de fármacos</strong> se registran recetas, esquemas y su seguimiento. Cuando
        SALUTEM informa medicamentos, aparecen como <strong>fármacos sugeridos</strong> para confirmarlos
        en el registro del ingreso.
      </p>
    ),
  },
  {
    titulo: "Dónde ver las alertas",
    contenido: (
      <p>
        El ícono de campana del encabezado abre el panel de alertas. La píldora roja indica cuántas
        alertas están pendientes, y los números junto a Licencias y Seguimiento EPT en el menú muestran
        las pendientes de cada módulo.
      </p>
    ),
  },
];

export function AyudaPage() {
  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Ayuda y soporte</h1>
        <p className="text-[13px] text-muted-foreground">
          Guía rápida de uso del sistema. Si algo no funciona como esperas, repórtalo.
        </p>
      </div>

      <Card className="p-4 flex items-center gap-3">
        <LifeBuoy className="size-5 text-primary shrink-0" />
        <p className="flex-1 text-[13px]">
          ¿Encontraste un error o tienes una sugerencia? Cuéntanos en el portal de incidencias.
        </p>
        <a
          href={URL_PORTAL_INCIDENCIAS}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-[13px] font-medium hover:bg-primary/90 transition-colors"
        >
          Reportar un problema
          <ExternalLink className="size-3.5" />
        </a>
      </Card>

      <div className="space-y-3">
        {SECCIONES.map((s) => (
          <Card key={s.titulo} className="p-5 space-y-2">
            <h2 className="text-[15px] font-semibold tracking-tight">{s.titulo}</h2>
            <div className="text-[13px] text-muted-foreground leading-relaxed space-y-2">
              {s.contenido}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
