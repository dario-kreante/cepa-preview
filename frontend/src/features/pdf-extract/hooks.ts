import { useMutation } from "@tanstack/react-query";
import { confirmExtraction, uploadPdf, type ExtractedFieldOut } from "./api";

export function useUploadPdf() {
  return useMutation({ mutationFn: (file: File) => uploadPdf(file) });
}

export function useConfirmExtraction() {
  return useMutation({
    mutationFn: ({
      formKey,
      fields,
    }: {
      formKey: string;
      fields: ExtractedFieldOut[];
    }) => confirmExtraction(formKey, fields),
  });
}
