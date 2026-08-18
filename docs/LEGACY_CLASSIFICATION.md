# SLE LTI — clasificación del prototipo y documentos históricos

Fecha de corte: 2026-08-17  
Baseline preservado: `legacy-functional-2026-08-17` → commit `77e327c2dd24c4f54a90532941b27096b5494f3b`

## Regla de uso

Cada registro se clasifica como:

- **Vigente:** describe una función comprobada que debe conservarse.
- **Vigente con cambios:** la idea sigue, pero su implementación no escala o ya cambió.
- **Legado de referencia:** explica una etapa anterior; no debe guiar trabajo nuevo.
- **Obsoleto / no reutilizar:** contiene tecnología, configuración o credenciales que no deben copiarse.

## Matriz de clasificación

| Evidencia | Estado | Qué se conserva | Qué cambia o se descarta |
|---|---|---|---|
| Repositorio `sle-lti-server`, commit `77e327c` | Vigente con cambios | LTI 1.3, OIDC, Deep Linking, AGS, PyLTI1p3, endpoints `/login/`, `/launch/`, `/jwks/`, `/deeplink/submit`, `/api/grade`; funcionamiento comprobado con Moodle y grade passback comprobado con Canvas | Configuración monoinstitucional, memoria local, URLs codificadas, confianza en scores enviados por el navegador, CORS abierto y despliegue automático desde `main` |
| Release `legacy-functional-2026-08-17` | Vigente | Punto exacto de restauración del prototipo | No se modifica; no se usa como rama de desarrollo |
| `PROGRESS.md` del repositorio LTI | Vigente con cambios | Inventario inicial de GCP, endpoints y flujo técnico | La narrativa Canvas-only y la lista de pendientes ya no reflejan el estado: Canvas sí llegó a grade passback; Moodle es ahora la plataforma de referencia |
| `Moodle Configuration Checklist — Spanish Learning Edge LTI.txt` | Vigente con cambios | URLs de registro, LTI 1.3, Deep Linking y AGS; flujo “Select content” | Debe dividirse en registro institucional (una vez) y configuración por curso/asignación; debe añadir verificación de `issuer + client_id + deployment_id`, semana, intentos y política de calificación |
| `SLE_LTI_Architecture_v1.docx` | Legado de referencia | Decisión LTI 1.3 + AGS, minimización de datos, idea de `reportScore()` y relación “una calificación estable = un line item” | AWS Lambda/DynamoDB, Canvas como único LMS, Rise vía SCORM y columna por bloque no son la arquitectura objetivo. Sustituir por Google Cloud, Moodle-first y máximo tres categorías semanales |
| `Proceso para activar LTI.txt` y captura SCORM Cloud | Obsoleto / no reutilizar | Sólo la evidencia de que se probó LTI 1.1/BLTI con SCORM Cloud | No usar URL/key/secret de LTI 1.1. El archivo contiene un secreto histórico en texto claro: verificar revocación y eliminarlo de futuras copias/documentación |
| `AI-worksheets/instructor-dashboard.html` | Vigente con cambios | Selector por categoría, selección de ejercicios, preview y Deep Linking | Catálogo codificado en HTML, `L01` fijo, URLs públicas y ausencia de semana, versiones y políticas de intento/calificación |
| Workbooks HTML de `AI-worksheets` | Vigente con cambios | Motor pedagógico, filtrado `?exercises=`, score agregado y `reportScore()` | El navegador no debe decidir la nota definitiva; el servidor debe validar actividad, máximo, versión y política. El contenido no debe depender para siempre de GitHub Pages público |
| `Strawberry-Cupcake` / FACT | Vigente con cambios; futuro | Evaluación FACT C1–C4, procesamiento efímero y ausencia de conservación intencional del audio | No entra al camino crítico del MVP LTI. Primero se integra como práctica completion/incomplete; score numérico y passback quedan para una fase posterior validada |
| Cards, flashcards y grammar cheat sheets | Vigente como estudio no calificable | Recursos suplementarios bajo la misma licencia y catálogo | Eliminar lenguaje de lead magnet/venta; normalizar diseño y metadatos; no convertir a SCORM ni forzar grade passback |
| `sle-dossier` | Vigente como fuente, no como producto terminado | Course outline, mapas y evidencia visual | Revisar lenguaje comercial antiguo, duplicados y recursos pesados; no usarlo como catálogo de ejecución |

## Partes genéricas LTI 1.3 vs. específicas de Moodle

### Genéricas y reutilizables

- Descubrimiento del registro por `issuer`, `client_id` y `deployment_id`.
- OIDC login initiation y validación del `id_token`.
- JWKS del tool y verificación de JWKS de la plataforma.
- `LtiResourceLinkRequest` y `LtiDeepLinkingRequest`.
- Deep Linking Response con `ltiResourceLink`, `custom` y `lineItem`.
- AGS Score Service y Line Item Service.
- Uso de `sub`, `context.id`, `resource_link.id` y `deployment_id` como identificadores técnicos.

### Moodle en el prototipo

- `CacheCookieService` y `NoCookieStorage` se añadieron para sobrevivir restricciones de cookies dentro del iframe de Moodle.
- El registro de Moodle está codificado directamente en `configs/tool.json`.
- El dashboard actual y sus textos describen un flujo Moodle/Canvas mezclado.
- Las pruebas operativas y URLs actuales pertenecen al MoodleCloud developer shell.

Estas adaptaciones no deben contaminar el núcleo. vNext debe conservarlas como comportamiento de compatibilidad detrás de una capa de plataforma.

## Riesgos descubiertos

1. **Persistencia:** `attempts` y `SimpleCache` viven en memoria. Cloud Run es stateless; una nueva instancia o revisión puede perder launches e intentos.
2. **Integridad de calificación:** `/api/grade` acepta `score` y `max_score` del navegador sin cotejarlos con un manifiesto de asignación.
3. **Reintentos:** el token se marca usado antes de confirmar AGS; un fallo de passback puede dejar un intento sin recuperación.
4. **Multiinstitución:** `tool.json` es configuración estática, no un registro dinámico de tenants/deployments.
5. **Licencia:** los workbooks alojados públicamente en GitHub Pages pueden abrirse fuera del LMS.
6. **Contenido:** el dashboard codifica L01 y tres URLs concretas; no existe catálogo versionado.
7. **Privacidad:** `user_sub` es seudónimo, no anónimo. Junto con curso, asignación y score constituye un registro educativo que debe tratarse con controles FERPA.
8. **Secretos:** existe un secreto histórico de SCORM Cloud en un archivo local; no debe migrarse. El pipeline actual usa una llave JSON de service account y conviene migrar a federación de identidad.
9. **Release:** cada push a `main` despliega producción. Debe existir un entorno staging y una promoción explícita.

## Decisión L03

El prototipo queda preservado como evidencia funcional. El trabajo nuevo parte de una rama vNext y no modifica la release preservada. Moodle es la plataforma de referencia; Canvas se mantiene mediante un contrato de adaptador y checklist, sin usar un Canvas institucional sin autorización.

