/**
 * ContactosEptPanel — add contactos (correo) for an active caso EPT.
 *
 * Note: there is NO GET endpoint for contactos, so this panel keeps a local
 * session list of contacts added during the current session. A note explains
 * this limitation to the user.
 */
import { useState } from "react";
import { z } from "zod";
import { Mail, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAgregarContacto } from "./hooks";
import type { ContactoEptRead } from "./api";

interface Props {
  casoId: number;
  canWrite: boolean;
}

const emailSchema = z.string().email("Correo electrónico inválido");

export function ContactosEptPanel({ casoId, canWrite }: Props) {
  const [correo, setCorreo] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [sessionContactos, setSessionContactos] = useState<ContactoEptRead[]>(
    []
  );

  const { mutateAsync, isPending } = useAgregarContacto();

  function validateEmail(value: string): boolean {
    const result = emailSchema.safeParse(value);
    if (!result.success) {
      setEmailError(result.error.errors[0].message);
      return false;
    }
    setEmailError(null);
    return true;
  }

  async function handleAgregar() {
    if (!validateEmail(correo)) {
      return;
    }

    try {
      const contacto = await mutateAsync({ casoId, body: { correo } });
      setSessionContactos((prev) => [...prev, contacto]);
      setCorreo("");
      setEmailError(null);
      toast.success("Contacto agregado");
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al agregar el contacto";
      toast.error(msg);
    }
  }

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Mail className="size-4 text-muted-foreground" />
        <h3 className="text-[14px] font-semibold">Contactos EPT</h3>
      </div>

      {canWrite && (
        <div className="space-y-2">
          <Label htmlFor="contacto-correo">Correo electrónico</Label>
          <div className="flex items-start gap-2">
            <div className="flex-1 space-y-1">
              <Input
                id="contacto-correo"
                type="email"
                value={correo}
                onChange={(e) => {
                  setCorreo(e.target.value);
                  if (emailError) setEmailError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void handleAgregar();
                  }
                }}
                placeholder="nombre@empresa.cl"
                className="h-9 text-[13px]"
                aria-label="Correo del contacto"
                data-testid="input-contacto-correo"
                aria-invalid={emailError ? "true" : undefined}
              />
              {emailError && (
                <p
                  className="text-[11.5px] text-destructive"
                  data-testid="error-correo"
                >
                  {emailError}
                </p>
              )}
            </div>
            <Button
              size="sm"
              onClick={() => void handleAgregar()}
              disabled={isPending || !correo}
              data-testid="btn-agregar-contacto"
            >
              <UserPlus className="size-3.5 mr-1" />
              Agregar contacto
            </Button>
          </div>
        </div>
      )}

      {/* Session contactos list */}
      {sessionContactos.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Contactos agregados
          </p>
          <ul className="space-y-1" data-testid="lista-contactos">
            {sessionContactos.map((c) => (
              <li
                key={c.id}
                className="flex items-center gap-2 text-[13px] py-1 px-2 rounded-md bg-muted/30"
                data-testid="contacto-item"
              >
                <Mail className="size-3 text-muted-foreground shrink-0" />
                <span>{c.correo}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {sessionContactos.length === 0 && !canWrite && (
        <p className="text-[13px] text-muted-foreground">
          Sin contactos registrados en esta sesión.
        </p>
      )}

      <p className="text-[11.5px] text-muted-foreground/70 italic">
        Los contactos agregados se muestran en esta sesión
      </p>
    </Card>
  );
}
