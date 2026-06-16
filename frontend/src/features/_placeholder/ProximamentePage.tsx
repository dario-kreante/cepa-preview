export function ProximamentePage({ titulo }: { titulo: string }) {
  return (
    <div className="space-y-2">
      <h1 className="text-lg font-semibold text-foreground">{titulo}</h1>
      <p className="text-sm text-muted-foreground">Módulo en construcción. Disponible en una próxima entrega.</p>
    </div>
  );
}
