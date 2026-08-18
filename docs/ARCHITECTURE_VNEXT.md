# SLE LTI vNext — arquitectura multiinstitucional

## Resultado recomendado

Construir un solo producto LTI 1.3 multiinstitucional, Moodle-first y compatible con Canvas, con cuatro fronteras claras:

1. **Núcleo LTI:** seguridad, launch, Deep Linking y AGS, sin lógica específica de Moodle/Canvas.
2. **Registro institucional:** cada integración se identifica por `(issuer, client_id, deployment_id)` y se vincula a una licencia/tenant.
3. **Catálogo y asignaciones:** el contenido existe una sola vez; cada curso crea asignaciones versionadas con semana, categoría, ejercicios e intentos.
4. **Ejecución y grade passback:** el servidor autoriza el recurso, registra intentos y calcula qué resultado enviar según la política elegida.

## Flujo objetivo

```text
Instructor en Moodle/Canvas
  -> LTI Deep Linking launch
  -> SLE resuelve tenant + curso + rol
  -> Selector: unidad -> lección -> semana -> máximo 3 categorías
  -> SLE crea assignment snapshot(s) + devuelve ltiResourceLink(s)
  -> LMS crea actividades/line items

Estudiante
  -> LTI Resource Link launch
  -> SLE resuelve assignment_id y versión autorizada
  -> entrega token breve + contenido correspondiente
  -> estudiante completa ejercicios
  -> SLE valida respuestas/resultado contra el manifiesto
  -> guarda intento y recalcula best/last
  -> AGS publica la nota efectiva para esa asignación semanal
```

## Modelo multiinstitucional mínimo

| Entidad | Clave / propósito |
|---|---|
| `tenants` | Institución, licencia, estado, límites y preferencias |
| `platform_registrations` | `issuer + client_id`, URLs OIDC/token/JWKS, plataforma (`moodle`, `canvas`, otra) |
| `deployments` | `registration_id + deployment_id`; vínculo estable a tenant y licencia |
| `contexts` | Curso LMS: `deployment_id + context_id`; nombre opcional y periodo |
| `catalog_items` | Objeto pedagógico canónico y su tipo |
| `catalog_versions` | Versión inmutable, checksum, ubicación y estado de publicación |
| `assignments` | Snapshot creado por Deep Linking: contexto, semana, categoría, versión, ejercicios, puntos, intentos y regla de nota |
| `resource_links` | Relación `resource_link_id -> assignment_id` |
| `launches` | Estado OIDC/LTI de vida corta |
| `attempts` | Intento por usuario seudónimo y assignment |
| `grade_events` | Resultado calculado, resultado enviado, respuesta AGS e idempotency key |

No guardar nombres, correos ni audio para el MVP. Guardar sólo los identificadores LTI necesarios. Aplicar retención explícita a launches, intentos y eventos.

## Servicios en Google Cloud

### Ahora / MVP

- **Cloud Run — `sle-lti-vnext-staging`:** aplicación web y API.
- **Firestore:** registros institucionales, catálogo, asignaciones, launches, intentos y eventos de nota.
- **Secret Manager:** llave privada LTI, secreto de sesión y cualquier credencial externa. Fijar versiones, no `latest`, en despliegues controlados.
- **Artifact Registry:** imágenes de contenedor versionadas.
- **Cloud Logging/Monitoring:** errores de launch, Deep Linking y grade passback sin payloads sensibles.
- **GitHub Actions:** pruebas y build; staging automático desde rama de staging, producción sólo mediante aprobación/promoción.

### Cuando el passback requiera mayor resiliencia

- **Cloud Tasks:** cola idempotente para grade passback y reintentos. No es necesaria para el primer piloto si Firestore registra fallos recuperables.

### Cuando la licencia de contenido sea prioritaria

- **Cloud Storage privado:** assets HTML/JS/audio publicados por versión.
- **Entrega autorizada:** URLs firmadas breves o un gateway Cloud Run que valide el launch. GitHub conserva el código fuente; GitHub Pages deja de ser la distribución comercial.
- **Cloud CDN:** sólo si el volumen lo justifica y el control de acceso queda resuelto.

No se recomienda una VM para este sistema. Cloud Run ya cubre el servicio HTTP y escala a cero. Tampoco se recomienda un proyecto de GCP por institución en la etapa inicial: las instituciones no ejecutan código propio y el costo/operación sería desproporcionado. La separación será lógica por tenant, con posibilidad de aislamiento por proyecto si un contrato futuro lo exige.

## Capas de aplicación

```text
web/routes
  login, launch, deep_link, content, grade, health

lti/core
  claims, OIDC, JWKS, launch validation, AGS, Deep Linking

lti/platform_adapters
  generic.py
  moodle.py    # cookies/iframe y diferencias probadas
  canvas.py    # placements/config y extensiones futuras

domain
  tenants, catalog, assignments, attempts, grading, licensing

repositories
  firestore implementations

workers
  grade_passback (directo primero; Cloud Tasks después)
```

## Cambios respecto al prototipo

| Prototipo | vNext |
|---|---|
| `tool.json` con instituciones | registros en Firestore, validados por clave compuesta |
| `SimpleCache` y diccionario `attempts` | Firestore con expiración lógica y limpieza programada |
| `workbook_url` enviado como parámetro | `assignment_id` opaco; el servidor resuelve una versión autorizada |
| score/max del navegador | resultado validado contra manifiesto y límites del assignment |
| token de un uso sin recuperación | intentos idempotentes y estado `pending/sent/failed` |
| título fijo `L01` | títulos derivados de catálogo + semana + categoría |
| un único dashboard codificado | selector generado desde catálogo |
| push a `main` = producción | staging separado y promoción manual |

## Compatibilidad Canvas desde el diseño

- Mantener estándar LTI 1.3/Advantage como contrato principal.
- No usar URLs, claims ni comportamiento Moodle dentro del dominio.
- Permitir que Deep Linking devuelva uno o varios recursos según lo que acepte la plataforma.
- Probar en Moodle los casos estándar y conservar una matriz Canvas de diferencias: placements, configuración JSON, múltiples items, fechas, intentos y presentación en iframe/nueva ventana.
- No reactivar el Canvas de South College sin autorización formal.

## Fases

1. **Preservación:** baseline, clasificación y restauración verificable.
2. **Staging vNext:** app separada, Firestore, registros multi-tenant y catálogo mínimo de L01.
3. **Moodle piloto:** Deep Linking de una semana, tres categorías, intentos y best/last.
4. **Contenido comercial protegido:** versionado y entrega privada.
5. **Segunda institución:** comprobar aislamiento, onboarding y licencia.
6. **Canvas readiness:** ejecutar checklist en un Canvas autorizado.
7. **FACT:** completion/incomplete; después score numérico validado.

## Fuentes normativas y de plataforma

- LTI Core 1.3: https://www.imsglobal.org/spec/lti/v1p3
- Deep Linking 2.0: https://www.imsglobal.org/spec/lti-dl/v2p0
- Assignment and Grade Services 2.0: https://www.imsglobal.org/spec/lti-ags/v2p0/
- Moodle LTI 1.3 support: https://docs.moodle.org/dev/LTI_1.3_support
- Canvas Assignment Selection: https://developerdocs.instructure.com/services/canvas/external-tools/lti/placements/file.assignment_selection_placement
- Canvas Deep Linking: https://developerdocs.instructure.com/services/canvas/external-tools/lti/file.content_item
- Cloud Run overview: https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- Secret Manager best practices: https://docs.cloud.google.com/secret-manager/docs/best-practices

