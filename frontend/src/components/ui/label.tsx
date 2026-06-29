import * as React from "react"
import { Label as LabelPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Label({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      className={cn(
        // DS: espaciado por defecto label→control. Los campos usan el patrón
        // <Label/> seguido de <Input/>/<select> sin wrapper; mb-1.5 (6px) da un
        // gap consistente en toda la app. Para usos inline (checkbox/switch),
        // pasar `mb-0` en className para neutralizarlo.
        "mb-1.5 flex items-center gap-2 text-sm leading-none font-medium select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Label }
