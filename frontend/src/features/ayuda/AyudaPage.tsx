/**
 * AyudaPage — centro de ayuda: guías por pantalla, preguntas frecuentes, glosario y soporte
 * (COMP-2609-01).
 *
 * Destino del botón "Ayuda y soporte" del menú lateral y del ícono (?) del Topbar, que abre
 * la guía de la pantalla actual con `?guia=<ruta>`. Las guías se filtran por el perfil: cada
 * quien ve las de las pantallas de su menú. El contenido vive en `contenido.ts`.
 */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  ChevronDown,
  CircleHelp,
  ExternalLink,
  Lightbulb,
  LifeBuoy,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCheck,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { NAV, itemsVisibles, type NavItem } from "@/app/shell/nav";
import { useAuth } from "@/lib/auth/AuthContext";
import { cn } from "@/lib/utils";
import {
  ATAJOS,
  GLOSARIO,
  GUIAS,
  PREGUNTAS,
  normalizar,
  textoDeGuia,
  type Guia,
} from "./contenido";

export const URL_PORTAL_INCIDENCIAS = "https://cepa-incidencias.dramirez-gysactiva.chatgpt.site";

const NOMBRE_ROL = { Coordinacion: "Coordinación", Administrativo: "Administrativo", Auditor: "Auditor" };

const idGuia = (ruta: string) => `guia-${ruta === "/" ? "dashboard" : ruta.slice(1)}`;

function desplazarA(ruta: string) {
  requestAnimationFrame(() =>
    document.getElementById(idGuia(ruta))?.scrollIntoView?.({ behavior: "smooth", block: "start" }),
  );
}

export function AyudaPage() {
  const { rol } = useAuth();
  const [params, setParams] = useSearchParams();
  const guiaPedida = params.get("guia");
  const [busqueda, setBusqueda] = useState("");
  const [pestana, setPestana] = useState("guias");
  const [abiertas, setAbiertas] = useState<Set<string>>(() => new Set(guiaPedida ? [guiaPedida] : []));

  // Guías de las pantallas que el perfil ve en su menú, agrupadas como el menú.
  const grupos = useMemo(() => {
    const porRuta = new Map(GUIAS.map((g) => [g.ruta, g]));
    return NAV.map((s) => ({
      seccion: s.label,
      items: itemsVisibles(s.items, rol)
        .map((i: NavItem) => ({ guia: porRuta.get(i.to), icono: i.icon }))
        .filter((x): x is { guia: Guia; icono: NavItem["icon"] } => !!x.guia),
    })).filter((g) => g.items.length > 0);
  }, [rol]);

  const iconos = useMemo(
    () => new Map(grupos.flatMap((g) => g.items.map((i) => [i.guia.ruta, i.icono] as const))),
    [grupos],
  );
  const visibles = useMemo(() => new Set(iconos.keys()), [iconos]);

  const mostrarGuia = (ruta: string) => {
    setPestana("guias");
    setBusqueda("");
    setAbiertas((prev) => new Set(prev).add(ruta));
    desplazarA(ruta);
  };

  // Ayuda contextual: el ícono (?) del Topbar llega con ?guia=<ruta de la pantalla>. Si se
  // pide otra guía estando ya en la ayuda, se ajusta el estado en el mismo render.
  const [guiaVista, setGuiaVista] = useState(guiaPedida);
  if (guiaPedida !== guiaVista) {
    setGuiaVista(guiaPedida);
    if (guiaPedida) {
      setPestana("guias");
      setBusqueda("");
      setAbiertas((prev) => new Set(prev).add(guiaPedida));
    }
  }
  useEffect(() => {
    if (guiaPedida) desplazarA(guiaPedida);
  }, [guiaPedida]);

  const alternar = (ruta: string) =>
    setAbiertas((prev) => {
      const next = new Set(prev);
      if (next.has(ruta)) next.delete(ruta);
      else next.add(ruta);
      return next;
    });

  const abrirGuia = (ruta: string) => {
    setParams({ guia: ruta }, { replace: true });
    mostrarGuia(ruta);
  };

  const q = normalizar(busqueda.trim());
  const resultados = useMemo(() => {
    if (!q) return null;
    return {
      guias: GUIAS.filter((g) => visibles.has(g.ruta) && textoDeGuia(g).includes(q)),
      preguntas: PREGUNTAS.filter((p) => normalizar(`${p.pregunta} ${p.respuesta}`).includes(q)),
      terminos: GLOSARIO.filter((t) => normalizar(`${t.termino} ${t.definicion}`).includes(q)),
    };
  }, [q, visibles]);

  const atajos = ATAJOS.filter((a) => (!a.roles || (rol && a.roles.includes(rol))) && visibles.has(a.guia));

  return (
    <div className="max-w-6xl grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px] items-start">
      <div className="space-y-5 min-w-0">
        {/* Portada con buscador */}
        <Card className="p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border-primary/15">
          <div className="flex items-start gap-3">
            <div className="size-10 rounded-lg bg-primary text-primary-foreground grid place-items-center shrink-0">
              <LifeBuoy className="size-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-[22px] font-semibold tracking-tight">¿En qué te ayudamos?</h1>
              <p className="text-[13px] text-muted-foreground">
                Guías paso a paso de cada pantalla, respuestas a dudas frecuentes y cómo pedir soporte.
              </p>
            </div>
          </div>
          <div className="relative mt-4">
            <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Busca una tarea, pantalla o término: «licencia», «folio», «citar»…"
              aria-label="Buscar en la ayuda"
              className="pl-9 pr-9 h-10 bg-background"
            />
            {busqueda && (
              <button
                type="button"
                onClick={() => setBusqueda("")}
                aria-label="Limpiar búsqueda"
                className="absolute right-2 top-1/2 -translate-y-1/2 size-6 grid place-items-center rounded hover:bg-muted text-muted-foreground cursor-pointer"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>
          {rol && (
            <p className="mt-2 text-[11px] text-muted-foreground">
              Mostrando las guías para tu perfil: <strong>{NOMBRE_ROL[rol]}</strong>
            </p>
          )}
        </Card>

        {resultados ? (
          <Resultados
            resultados={resultados}
            busqueda={busqueda}
            iconos={iconos}
            abiertas={abiertas}
            alternar={alternar}
            abrirGuia={abrirGuia}
          />
        ) : (
          <>
            {atajos.length > 0 && (
              <section aria-labelledby="atajos" className="space-y-2">
                <h2 id="atajos" className="text-[13px] font-semibold text-muted-foreground uppercase tracking-wide">
                  Lo más consultado
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {atajos.map((a) => {
                    const Icono = iconos.get(a.guia) ?? BookOpen;
                    return (
                      <button
                        key={a.guia}
                        type="button"
                        onClick={() => abrirGuia(a.guia)}
                        className="group text-left rounded-xl border bg-card p-4 hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer"
                      >
                        <Icono className="size-5 text-primary" />
                        <p className="mt-2 text-[13px] font-semibold leading-snug">{a.titulo}</p>
                        <p className="text-[12px] text-muted-foreground">{a.descripcion}</p>
                        <span className="mt-2 inline-flex items-center gap-1 text-[12px] font-medium text-primary">
                          Ver cómo <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>
            )}

            <ComoFuncionaSalutem />

            <Tabs value={pestana} onValueChange={setPestana} className="space-y-3">
              <TabsList>
                <TabsTrigger value="guias">Guías por pantalla</TabsTrigger>
                <TabsTrigger value="preguntas">Preguntas frecuentes</TabsTrigger>
                <TabsTrigger value="glosario">Glosario</TabsTrigger>
              </TabsList>

              <TabsContent value="guias" className="space-y-5">
                {grupos.map((g) => (
                  <section key={g.seccion} className="space-y-2">
                    <h3 className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide">
                      {g.seccion}
                    </h3>
                    <div className="space-y-2">
                      {g.items.map(({ guia, icono }) => (
                        <GuiaItem
                          key={guia.ruta}
                          guia={guia}
                          Icono={icono}
                          abierta={abiertas.has(guia.ruta)}
                          alternar={() => alternar(guia.ruta)}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </TabsContent>

              <TabsContent value="preguntas">
                <ListaPreguntas preguntas={PREGUNTAS} visibles={visibles} abrirGuia={abrirGuia} />
              </TabsContent>

              <TabsContent value="glosario">
                <ListaGlosario terminos={GLOSARIO} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>

      <Soporte />
    </div>
  );
}

function GuiaItem({
  guia,
  Icono,
  abierta,
  alternar,
}: {
  guia: Guia;
  Icono: NavItem["icon"];
  abierta: boolean;
  alternar: () => void;
}) {
  const panel = `${idGuia(guia.ruta)}-panel`;
  return (
    <Card id={idGuia(guia.ruta)} className={cn("overflow-hidden scroll-mt-20 transition-shadow", abierta && "shadow-sm ring-1 ring-primary/20")}>
      <button
        type="button"
        onClick={alternar}
        aria-expanded={abierta}
        aria-controls={panel}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-muted/40 transition-colors cursor-pointer"
      >
        <div className="size-9 rounded-lg bg-primary/10 text-primary grid place-items-center shrink-0">
          <Icono className="size-[18px]" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-[14px] font-semibold tracking-tight">{guia.titulo}</h4>
          <p className="text-[12px] text-muted-foreground line-clamp-2">{guia.resumen}</p>
        </div>
        <ChevronDown className={cn("size-4 text-muted-foreground shrink-0 transition-transform", abierta && "rotate-180")} />
      </button>

      {abierta && (
        <div id={panel} className="border-t px-4 pb-4 pt-3 space-y-4 text-[13px]">
          {guia.tareas.map((t) => (
            <div key={t.titulo} className="space-y-2">
              <p className="font-semibold">{t.titulo}</p>
              <ol className="space-y-1.5">
                {t.pasos.map((paso, i) => (
                  <li key={paso} className="flex gap-2.5">
                    <span className="size-5 rounded-full bg-primary/10 text-primary text-[11px] font-bold grid place-items-center shrink-0 mt-px">
                      {i + 1}
                    </span>
                    <span className="text-muted-foreground leading-relaxed">{paso}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}

          {guia.etiquetas && (
            <div className="space-y-2">
              <p className="font-semibold">Qué significa cada etiqueta</p>
              <dl className="grid gap-1.5 sm:grid-cols-[auto_1fr] sm:gap-x-3 items-baseline">
                {guia.etiquetas.map((e) => (
                  <div key={e.texto} className="contents">
                    <dt>
                      <Badge variant={e.tono}>{e.texto}</Badge>
                    </dt>
                    <dd className="text-muted-foreground text-[12px] mb-1 sm:mb-0">{e.significado}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {guia.automatico && (
            <Nota icono={RefreshCw} titulo="Llega solo desde SALUTEM" tono="info">
              {guia.automatico}
            </Nota>
          )}
          {guia.consejos?.map((c) => (
            <Nota key={c} icono={Lightbulb} titulo="Consejo" tono="warning">
              {c}
            </Nota>
          ))}
          {guia.quienEscribe && (
            <Nota icono={UserCheck} titulo="Quién puede registrar" tono="neutral">
              {guia.quienEscribe}
            </Nota>
          )}

          <Link
            to={guia.ruta}
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-[12px] font-medium hover:bg-muted transition-colors"
          >
            Ir a {guia.titulo} <ArrowRight className="size-3.5" />
          </Link>
        </div>
      )}
    </Card>
  );
}

const TONOS_NOTA = {
  info: "bg-[oklch(0.97_0.03_230)] border-[oklch(0.90_0.05_230)] text-[oklch(0.40_0.14_230)]",
  warning: "bg-[oklch(0.98_0.04_85)] border-[oklch(0.92_0.07_85)] text-[oklch(0.42_0.14_75)]",
  neutral: "bg-muted/60 border-border text-muted-foreground",
};

function Nota({
  icono: Icono,
  titulo,
  tono,
  children,
}: {
  icono: NavItem["icon"];
  titulo: string;
  tono: keyof typeof TONOS_NOTA;
  children: ReactNode;
}) {
  return (
    <div className={cn("flex gap-2.5 rounded-lg border px-3 py-2.5", TONOS_NOTA[tono])}>
      <Icono className="size-4 shrink-0 mt-0.5" />
      <p className="text-[12px] leading-relaxed">
        <strong className="font-semibold">{titulo}.</strong> <span className="text-foreground/80">{children}</span>
      </p>
    </div>
  );
}

function ComoFuncionaSalutem() {
  const pasos = [
    { n: 1, titulo: "Se registra en SALUTEM", texto: "Horas, atenciones, licencias y recetas se ingresan en SALUTEM, como siempre." },
    { n: 2, titulo: "El SIGE copia cada pocos minutos", texto: "Solo lectura: el SIGE nunca modifica SALUTEM. Puede tardar unos 5 minutos." },
    { n: 3, titulo: "Tú revisas y confirmas", texto: "Los controles se crean solos. Licencias, recetas y pacientes nuevos llegan como sugerencia con una alerta." },
  ];
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <RefreshCw className="size-4 text-primary" />
        <h2 className="text-[15px] font-semibold tracking-tight">Cómo trabaja el SIGE con SALUTEM</h2>
      </div>
      <ol className="mt-3 grid gap-3 md:grid-cols-3">
        {pasos.map((p) => (
          <li key={p.n} className="relative rounded-lg bg-muted/50 p-3">
            <span className="text-[11px] font-bold text-primary">PASO {p.n}</span>
            <p className="text-[13px] font-semibold mt-0.5">{p.titulo}</p>
            <p className="text-[12px] text-muted-foreground leading-relaxed mt-1">{p.texto}</p>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function ListaPreguntas({
  preguntas,
  visibles,
  abrirGuia,
}: {
  preguntas: typeof PREGUNTAS;
  visibles: Set<string>;
  abrirGuia: (ruta: string) => void;
}) {
  return (
    <div className="space-y-2">
      {preguntas.map((p) => (
        <details key={p.pregunta} className="group rounded-xl border bg-card open:shadow-sm">
          <summary className="flex items-center gap-3 p-4 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
            <CircleHelp className="size-4 text-primary shrink-0" />
            <span className="flex-1 text-[13px] font-semibold">{p.pregunta}</span>
            <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" />
          </summary>
          <div className="px-4 pb-4 pl-11 space-y-2">
            <p className="text-[13px] text-muted-foreground leading-relaxed">{p.respuesta}</p>
            {p.guia && visibles.has(p.guia) && (
              <button
                type="button"
                onClick={() => abrirGuia(p.guia!)}
                className="inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:underline cursor-pointer"
              >
                Ver la guía <ArrowRight className="size-3" />
              </button>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}

function ListaGlosario({ terminos }: { terminos: typeof GLOSARIO }) {
  return (
    <Card>
      <dl className="divide-y">
      {terminos.map((t) => (
        <div key={t.termino} className="grid gap-1 sm:grid-cols-[140px_1fr] sm:gap-4 px-4 py-3">
          <dt className="text-[13px] font-semibold">{t.termino}</dt>
          <dd className="text-[13px] text-muted-foreground leading-relaxed">{t.definicion}</dd>
        </div>
      ))}
      </dl>
    </Card>
  );
}

function Resultados({
  resultados,
  busqueda,
  iconos,
  abiertas,
  alternar,
  abrirGuia,
}: {
  resultados: { guias: Guia[]; preguntas: typeof PREGUNTAS; terminos: typeof GLOSARIO };
  busqueda: string;
  iconos: Map<string, NavItem["icon"]>;
  abiertas: Set<string>;
  alternar: (ruta: string) => void;
  abrirGuia: (ruta: string) => void;
}) {
  const { guias, preguntas, terminos } = resultados;
  const total = guias.length + preguntas.length + terminos.length;
  if (total === 0) {
    return (
      <Card className="p-8 text-center space-y-2">
        <Search className="size-6 text-muted-foreground mx-auto" />
        <p className="text-[14px] font-semibold">No encontramos nada sobre «{busqueda.trim()}»</p>
        <p className="text-[13px] text-muted-foreground">
          Prueba con otra palabra, o cuéntanos tu duda en el portal de soporte.
        </p>
      </Card>
    );
  }
  const visibles = new Set(iconos.keys());
  return (
    <div className="space-y-5" aria-live="polite">
      <p className="text-[12px] text-muted-foreground">
        {total} resultado{total === 1 ? "" : "s"} para «{busqueda.trim()}»
      </p>
      {guias.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide">Guías</h3>
          {guias.map((g) => (
            <GuiaItem
              key={g.ruta}
              guia={g}
              Icono={iconos.get(g.ruta) ?? BookOpen}
              abierta={abiertas.has(g.ruta)}
              alternar={() => alternar(g.ruta)}
            />
          ))}
        </section>
      )}
      {preguntas.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide">Preguntas frecuentes</h3>
          <ListaPreguntas preguntas={preguntas} visibles={visibles} abrirGuia={abrirGuia} />
        </section>
      )}
      {terminos.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide">Glosario</h3>
          <ListaGlosario terminos={terminos} />
        </section>
      )}
    </div>
  );
}

function Soporte() {
  return (
    <aside className="lg:sticky lg:top-20 space-y-3">
      <Card className="p-5 space-y-3">
        <div className="flex items-center gap-2">
          <LifeBuoy className="size-4 text-primary" />
          <h2 className="text-[15px] font-semibold tracking-tight">¿Algo no funciona?</h2>
        </div>
        <p className="text-[13px] text-muted-foreground">
          Reporta errores o sugerencias en el portal de incidencias. Para resolverlo rápido, cuéntanos:
        </p>
        <ul className="text-[12px] text-muted-foreground space-y-1.5">
          {[
            "En qué pantalla estabas",
            "Qué intentabas hacer y qué pasó",
            "El folio del caso, si aplica",
            "Una captura de pantalla, si puedes",
          ].map((x) => (
            <li key={x} className="flex gap-2">
              <span className="size-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
              {x}
            </li>
          ))}
        </ul>
        <a
          href={URL_PORTAL_INCIDENCIAS}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full inline-flex items-center justify-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-2 text-[13px] font-medium hover:bg-primary/90 transition-colors"
        >
          Reportar un problema
          <ExternalLink className="size-3.5" />
        </a>
        <p className="flex gap-1.5 text-[11px] text-muted-foreground">
          <ShieldCheck className="size-3.5 shrink-0 mt-px" />
          No incluyas nombres, RUT ni datos clínicos: identifica el caso por su folio.
        </p>
      </Card>
      <Card className="p-4 space-y-1.5">
        <p className="text-[13px] font-semibold">Antes de reportar</p>
        <p className="text-[12px] text-muted-foreground leading-relaxed">
          Si falta un dato de SALUTEM, espera unos minutos y recarga la página. Si no ves un botón, puede que tu
          perfil no tenga ese permiso.
        </p>
      </Card>
    </aside>
  );
}
