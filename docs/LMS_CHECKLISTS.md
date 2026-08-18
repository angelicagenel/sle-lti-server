# SLE LTI — checklists Moodle y Canvas

## Checklist Moodle — plataforma de referencia

### A. Registro institucional (una vez por instancia)

- [ ] Registrar herramienta como LTI 1.3.
- [ ] Capturar Platform ID/issuer, Client ID, Deployment ID, JWKS URL, Access Token URL y Authentication Request URL.
- [ ] Confirmar que la clave compuesta `(issuer, client_id, deployment_id)` resuelve un tenant activo.
- [ ] Configurar Tool URL, Initiate Login URL, Redirect URI y Tool JWKS URL del entorno correcto.
- [ ] Habilitar Deep Linking.
- [ ] Habilitar AGS: score y administración de line items sólo si se utiliza.
- [ ] NRPS queda deshabilitado inicialmente; no se necesitan nombres ni roster para el MVP.
- [ ] Verificar iframe/cookies en Chrome, Edge y Safari; conservar fallback Moodle sólo si es necesario.
- [ ] Probar roles: instructor puede seleccionar; estudiante sólo puede lanzar el recurso asignado.

### B. Onboarding del curso

- [ ] El primer launch crea o vincula `context_id` al tenant correcto.
- [ ] Registrar periodo, nombre interno y licencia sin almacenar PII del estudiante.
- [ ] Confirmar que el curso ve sólo contenido incluido en su licencia.
- [ ] Confirmar zona horaria y convención de semanas.

### C. Deep Linking por asignación

- [ ] Instructor abre External Tool → Select content.
- [ ] Selecciona unidad, lección y semana.
- [ ] Selecciona máximo tres categorías.
- [ ] Selecciona ejercicios dentro de cada categoría.
- [ ] Revisa título, puntos, intentos y best/last.
- [ ] SLE devuelve un `ltiResourceLink` por categoría con `lineItem`.
- [ ] Moodle crea actividades y columnas separadas.
- [ ] El launch estudiantil contiene `deployment_id`, `context.id`, `resource_link.id`, `sub` y AGS endpoint.

### D. Prueba de calificación

- [ ] Intento 1 crea score esperado.
- [ ] Intento 2 actualiza según `best` o `last`.
- [ ] El intento 4 se rechaza cuando el límite es 3.
- [ ] Reintentar el mismo evento no duplica ni corrompe la nota.
- [ ] Un fallo AGS queda `failed` y se puede reenviar.
- [ ] La semana siguiente crea otro line item y no cambia la nota previa.
- [ ] La actualización del catálogo no cambia assignments existentes.

### E. Aislamiento multiinstitucional

- [ ] Un deployment no puede abrir assignments de otro tenant.
- [ ] Un curso no puede enumerar catálogo fuera de su licencia.
- [ ] Un `assignment_id` alterado devuelve 403/404 sin revelar metadatos.
- [ ] Logs no contienen tokens, audio, nombre, email ni JWT completos.

## Checklist Canvas — listo para una institución autorizada

No ejecutar contra South College ni otro Canvas institucional sin autorización.

### A. Registro Developer Key

- [ ] Crear LTI 1.3 Developer Key con URLs de staging.
- [ ] Configurar `assignment_selection` con `LtiDeepLinkingRequest`.
- [ ] Añadir sólo scopes AGS requeridos: score y, si aplica, lineitem.
- [ ] Registrar client ID y deployment ID en el tenant correspondiente.
- [ ] Verificar issuer, OIDC URL, OAuth token URL y JWKS de esa instancia Canvas.
- [ ] Mantener privacy/minimización coherente con los claims realmente necesarios.

### B. Deep Linking

- [ ] Canvas lanza el selector desde Assignment → External Tool → Find.
- [ ] Verificar `accept_multiple` y `accept_lineitem` del request; adaptar la respuesta a lo aceptado.
- [ ] Confirmar título y `scoreMaximum` creados desde `lineItem`.
- [ ] Confirmar comportamiento cuando se devuelve más de un recurso; si `assignment_selection` admite sólo uno en ese contexto, usar flujo por categoría o placement de importación múltiple autorizado.
- [ ] Verificar iframe vs. nueva ventana y controles de tamaño.

### C. AGS y reintentos

- [ ] Score visible como puntos reales y no como acumulado mutable.
- [ ] Best/last coincide con Moodle para los mismos intentos.
- [ ] Confirmar tratamiento Canvas de intentos permitidos y si la restricción debe residir también en SLE.
- [ ] Probar limpieza/reemplazo de score sólo cuando una política lo requiera.

### D. Copia de cursos y versionado

- [ ] Copiar curso y verificar que resource links/line items siguen resolviendo.
- [ ] No reutilizar un assignment snapshot de otro `context_id` sin una operación de copia explícita.
- [ ] Verificar fechas, disponibilidad y semana después de la copia.

## Matriz de equivalencia que debe mantenerse

| Capacidad | Moodle | Canvas | Contrato SLE |
|---|---|---|---|
| Registro | Configuración de external tool | Developer Key + deployment | `platform_registration` + `deployment` |
| Selector | Select content | `assignment_selection` | Deep Linking estándar |
| Recurso | External tool activity | External Tool assignment | `resource_link -> assignment` |
| Nota | Gradebook + AGS | Gradebook + AGS | `grade_event` idempotente |
| Curso | `context.id` | `context.id` | `context` aislado por deployment |
| Semana | Configuración SLE al asignar | Configuración SLE al asignar | Campo de assignment, no de contenido |

