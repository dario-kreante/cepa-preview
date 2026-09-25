/**
 * ConfiguracionPage — índice de las pantallas de administración (COMP-2609-02).
 *
 * Lista los items de la sección "Administración" del menú, filtrados con la misma
 * regla RBAC del Sidebar (`itemsVisibles`). Las rutas destino mantienen su propio
 * control de acceso en el backend: este índice solo evita mostrar enlaces inútiles.
 */
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/lib/auth/AuthContext";
import type { Rol } from "@/lib/rbac";
import { SECCION_ADMINISTRACION, itemsVisibles } from "@/app/shell/nav";

const DESCRIPCIONES: Record<string, string> = {
  "/usuarios": "Alta de usuarios, asignación de perfiles y desactivación de cuentas.",
  "/config-formularios": "Campos y versiones de los formularios dinámicos de ingreso.",
  "/ventanas-proceso": "Columnas y orden por defecto de los listados de cada proceso.",
};

export function ConfiguracionPage() {
  const { rol } = useAuth();
  const items = itemsVisibles(SECCION_ADMINISTRACION.items, rol as Rol | null);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Configuración</h1>
        <p className="text-[13px] text-muted-foreground">
          Pantallas de administración disponibles para tu perfil.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map(({ to, label, icon: Icon }) => (
          <Link key={to} to={to} className="group">
            <Card className="p-4 flex items-start gap-3 h-full transition-colors group-hover:border-primary/40 group-hover:bg-muted/40">
              <div className="size-9 rounded-md bg-primary/10 text-primary grid place-items-center shrink-0">
                <Icon className="size-[18px]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[14px] font-semibold">{label}</div>
                {DESCRIPCIONES[to] && (
                  <p className="text-[12.5px] text-muted-foreground mt-0.5">{DESCRIPCIONES[to]}</p>
                )}
              </div>
              <ChevronRight className="size-4 text-muted-foreground mt-1" />
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
