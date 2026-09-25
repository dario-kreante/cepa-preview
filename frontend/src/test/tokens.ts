/**
 * JWT falsos por rol para tests de componentes. La firma no se valida en el cliente:
 * AuthContext solo decodifica el payload para leer `role` y `username`.
 */
const HEADER = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9";
const FIRMA = "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

export const TOKENS = {
  // {"sub":"1","username":"test","role":"Coordinacion","type":"access","exp":9999999999}
  Coordinacion: `${HEADER}.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9.${FIRMA}`,
  // {"sub":"3","username":"administrativo","role":"Administrativo","type":"access","exp":9999999999}
  Administrativo: `${HEADER}.eyJzdWIiOiIzIiwidXNlcm5hbWUiOiJhZG1pbmlzdHJhdGl2byIsInJvbGUiOiJBZG1pbmlzdHJhdGl2byIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9.${FIRMA}`,
  // {"sub":"2","username":"auditor","role":"Auditor","type":"access","exp":9999999999}
  Auditor: `${HEADER}.eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ.${FIRMA}`,
} as const;
