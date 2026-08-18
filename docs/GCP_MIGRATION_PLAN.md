# SLE — qué permanece, qué migra y qué se reconstruye en Google Cloud

## Resumen ejecutivo

No se debe “duplicar todo y apagar lo viejo” en un solo paso. La migración segura es paralela:

1. preservar el prototipo;
2. crear staging vNext separado;
3. validar Moodle end-to-end;
4. pilotear con contenido mínimo;
5. promover producción;
6. retirar el prototipo sólo después de una ventana de observación y un plan de rollback.

## Inventario de destino

| Elemento actual | Decisión | Destino |
|---|---|---|
| Repo `sle-lti-server` y release funcional | Permanecer como respaldo | GitHub; protegido, sin nuevos despliegues desde la release |
| Código vNext | Reconstruir modularmente | Rama/repo GitHub separado y PRs borrador |
| Cloud Run `sle-lti-server` actual | Permanecer durante desarrollo | Prototipo/legacy hasta cutover aprobado |
| Servicio vNext | Crear | Cloud Run staging con nombre distinto |
| `attempts {}` y `SimpleCache` | Migrar/reconstruir | Firestore |
| Registros Moodle/Canvas en `tool.json` | Migrar | Firestore; secretos separados en Secret Manager |
| Llaves RSA y Flask secret | Permanecer pero mejorar gestión | Secret Manager con versiones fijadas y rotación |
| Pipeline con `GCP_SA_KEY` | Reconstruir | GitHub Actions + Workload Identity Federation; sin llave JSON de larga duración |
| Imagen Docker | Permanecer | Artifact Registry con tags/digests por release |
| HTML workbooks en GitHub Pages | Permanecer para desarrollo; migrar para licencia comercial | GitHub como source; Cloud Storage privado/entrega autorizada como distribución |
| Audios de listening | Migrar cuando se proteja contenido | Cloud Storage versionado; player HTML con velocidad y captions/transcript cuando corresponda |
| FACT Cloud Run y bucket | Permanecer fuera del camino crítico | Servicio separado; integración posterior mediante catálogo/LTI |
| VM de despliegue | Investigar y retirar si no tiene función única | No requerida por Cloud Run/Actions; nunca eliminar sin inventario y snapshot |

## Entornos

### Legacy

- Servicio actual y release preservada.
- Sólo correcciones de emergencia.
- Sin cambios de catálogo ni arquitectura.

### Staging

- Servicio y base de datos separados.
- Llaves y secretos distintos de producción.
- Moodle developer shell conectado aquí.
- Contenido piloto L01/U01.
- Logs con retención corta y sin payloads sensibles.

### Producción futura

- Se crea después de aprobar staging y piloto.
- Despliegue por promoción de imagen/digest, no por cualquier push a `main`.
- Rollback documentado a revisión previa.

Google recomienda separar entornos para aislar IAM, cuotas y secretos. Para la etapa inicial puede usarse un proyecto staging diferente y conservar el proyecto actual como legacy hasta el cutover.

## Orden de implementación

1. Crear proyecto/entorno staging y service account de mínimo privilegio.
2. Crear Firestore en la región elegida y colecciones iniciales.
3. Crear secretos de staging; no copiar secretos históricos.
4. Desplegar health check vNext sin tráfico de usuarios.
5. Registrar el Moodle developer shell contra staging.
6. Cargar catálogo mínimo U01/L01 y un assignment de prueba.
7. Validar Deep Linking, tres categorías, semana, intentos y best/last.
8. Añadir entrega de contenido autorizada.
9. Ejecutar prueba de aislamiento con segundo deployment/institución de prueba.
10. Preparar runbook de producción y rollback.

## Criterios antes de apagar el prototipo

- [ ] Baseline y artefactos de restauración verificados.
- [ ] Staging supera checklist Moodle completo.
- [ ] Segundo tenant/deployment no cruza datos.
- [ ] Grade passback es idempotente y recuperable.
- [ ] Contenido versionado no cambia notas antiguas.
- [ ] Secretos y permisos auditados.
- [ ] Costos y alertas básicas configurados.
- [ ] Ventana de observación completada.
- [ ] Angélica aprueba explícitamente el cutover.
- [ ] Sólo entonces: deshabilitar tráfico del servicio antiguo; conservar repo, release e imagen durante el periodo de retención.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Deploy accidental desde `main` | Quitar producción del trigger automático; protección de rama y promoción manual |
| Pérdida de launch/attempt | Firestore; idempotency keys; reintentos registrados |
| Cruce de instituciones | Clave compuesta deployment/tenant en todas las consultas y pruebas negativas |
| Manipulación de score | Snapshot del assignment y validación server-side |
| Acceso público al contenido | Entrega autorizada y URLs de vida corta |
| Secreto filtrado | Revocación, Secret Manager, WIF y escaneo de secretos |
| Costo inesperado | Budget alerts, límites de concurrencia y métricas por tenant |
| FACT incrementa costo/privacidad | Mantener separado; no almacenar audio; integrar después del MVP |

## Servicios que no hacen falta ahora

- Kubernetes/GKE.
- VM permanente de deploy.
- Cloud SQL, salvo que requisitos relacionales/reportes futuros superen Firestore.
- Cloud Tasks antes de comprobar que los reintentos directos + Firestore no bastan.
- Proyecto GCP por institución mientras SLE ejecuta sólo código propio y el piloto es pequeño.

