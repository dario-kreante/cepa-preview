import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="p-6 text-brand-700">Sistema CEPA — base</div>
  </StrictMode>,
);
