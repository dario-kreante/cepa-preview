import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  crearBorrador,
  obtenerPublicada,
  publicar,
  type FieldDefIn,
} from "./api";

export function usePublicada(formKey: string | null) {
  return useQuery({
    queryKey: ["form-def", formKey, "published"],
    queryFn: () => obtenerPublicada(formKey as string),
    enabled: !!formKey,
  });
}

export function useCrearBorrador() {
  return useMutation({
    mutationFn: ({
      formKey,
      fields,
    }: {
      formKey: string;
      fields: FieldDefIn[];
    }) => crearBorrador(formKey, fields),
  });
}

export function usePublicar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      formKey,
      versionId,
    }: {
      formKey: string;
      versionId: number;
    }) => publicar(formKey, versionId),
    onSuccess: (result, { formKey }) => {
      if (result.success)
        qc.invalidateQueries({ queryKey: ["form-def", formKey, "published"] });
    },
  });
}
