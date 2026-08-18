# SLE LTI vNext — registro de decisiones y riesgos

## Decisiones tomadas

| ID | Decisión | Estado |
|---|---|---|
| D01 | Moodle es la plataforma de referencia; Canvas se mantiene listo por adaptador/checklist | Aprobada |
| D02 | El prototipo original no se modifica ni se apaga durante vNext | Aprobada |
| D03 | vNext usa LTI 1.3 + Deep Linking 2.0 + AGS 2.0 | Aprobada |
| D04 | Multiinstitución se identifica por `issuer + client_id + deployment_id` | Aprobada |
| D05 | Semana es propiedad de la asignación, no del contenido | Aprobada |
| D06 | Máximo tres categorías por operación/asignación semanal | Aprobada para diseño; nombres por cerrar |
| D07 | Cada categoría semanal produce una nota estable independiente | Aprobada |
| D08 | Workbooks permanecen HTML; Rise no sustituye su función | Aprobada |
| D09 | eBook/Compendio/Cuéntame no son numéricos por defecto | Recomendada |
| D10 | Workbooks: 3 intentos y mejor intento por defecto; instructor elige 1–5/ilimitados y best/last | Recomendada |
| D11 | FACT queda fuera del MVP; futuro completion/incomplete sin conservar audio | Aprobada |
| D12 | GitHub es source control; Google Cloud es runtime/datos/distribución protegida | Aprobada |
| D13 | Firestore sustituye memoria local para el MVP multiinstitucional | Recomendada |

## Riesgos priorizados

| ID | Riesgo | Prob. | Impacto | Prioridad | Evidencia / acción |
|---|---|---:|---:|---:|---|
| R01 | Pérdida de estado por memoria efímera | Alta | Alta | P0 | `SimpleCache` + `attempts {}`; migrar antes del piloto |
| R02 | Score manipulable desde cliente | Media | Alta | P0 | Validar contra assignment snapshot y manifest |
| R03 | Cruce multi-tenant | Media | Crítico | P0 | Clave compuesta, reglas de repositorio y pruebas negativas |
| R04 | Deploy accidental a producción | Alta | Alta | P0 | `deploy.yml` se activa con push a `main`; separar staging/promoción |
| R05 | Credencial histórica expuesta | Desconocida | Alta | P0 | Verificar/revocar SCORM Cloud key/secret; no migrar |
| R06 | Contenido comercial público | Alta | Media/Alta | P1 | Migrar distribución a Cloud Storage/entrega autorizada |
| R07 | Divergencia Moodle/Canvas | Media | Media | P1 | Adaptadores y checklist de compatibilidad |
| R08 | Notas semanales inestables | Alta si se usa workbook maestro | Alta | P0 | Snapshot por assignment + semana + categoría |
| R09 | Costos de FACT y servicios AI | Media | Media | P2 | Mantener FACT separado y observar consumo |
| R10 | Retención/FERPA mal definida | Media | Alta | P1 | Política de datos y DPA antes de producción institucional |

## Decisiones abiertas que requieren a Angélica

1. Nombres finales de las tres categorías semanales.
2. Si el examen sustituye una categoría o vive fuera del límite semanal.
3. Cuándo eBook/Trazos/Reto producen completion y cuándo son sólo contenido.
4. Retención contractual de intentos y grade events.
5. Momento y criterios comerciales para proteger/migrar los HTML públicos.

