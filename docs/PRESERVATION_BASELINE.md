# SLE LTI — Baseline de preservación del prototipo funcional

**Estado:** baseline histórico verificable  
**Fecha de verificación:** 17 de agosto de 2026  
**Propósito:** conservar suficiente evidencia para restaurar el prototipo LTI funcional sin modificar el código ni la infraestructura que actualmente lo ejecuta.

> Este documento registra identificadores, rutas y dependencias. No contiene valores secretos, llaves privadas, credenciales de estudiantes ni datos educativos.

## 1. Punto de recuperación

| Elemento | Valor verificado |
|---|---|
| Repositorio | `angelicagenel/sle-lti-server` |
| Visibilidad | Público |
| Rama predeterminada | `main` |
| Commit de referencia | `77e327c2dd24c4f54a90532941b27096b5494f3b` |
| Mensaje del commit | `Log has_ags and AGS claim in /launch/ for grade passback diagnosis` |
| Proyecto Google Cloud | `sle-lti-server` |
| Número de proyecto | `950105557003` |
| Región | `us-central1` |
| Servicio Cloud Run | `sle-lti-server` |
| Revisión activa | `sle-lti-server-00058-726` |
| Tráfico | 100% a la revisión activa |
| URL del servicio | `https://sle-lti-server-950105557003.us-central1.run.app` |
| Imagen desplegada | `us-central1-docker.pkg.dev/sle-lti-server/cloud-run-source-deploy/sle-lti-server@sha256:0cddf85c65711f4406cddbce4c6c56c49bc97e14fafd0d1b8e1348ef61d0ec8d` |

La hora del último commit y la hora de creación de la revisión activa son consistentes con el mismo despliegue. Cloud Run no muestra metadatos de fuente suficientes para demostrar por sí solo la relación; por eso deben conservarse tanto el commit como el digest de la imagen.

## 2. Comportamiento funcional que debe preservarse

El prototipo implementa una herramienta LTI 1.3 con Flask y PyLTI1p3. El comportamiento de referencia incluye:

- inicio OIDC;
- lanzamiento LTI;
- publicación JWKS;
- Deep Linking para seleccionar contenido;
- creación de Line Item para el gradebook;
- Assignment and Grade Services (AGS) para grade passback;
- compatibilidad de iframe Moodle mediante almacenamiento auxiliar del estado cuando las cookies de terceros son bloqueadas;
- lanzamiento de un workbook HTML seleccionado;
- token de intento firmado, temporal y de un solo uso;
- recepción del resultado del workbook en `/api/grade`.

### Rutas públicas de referencia

| Ruta | Función |
|---|---|
| `/` | Estado básico del servicio |
| `/login/` | Inicio de autenticación OIDC |
| `/launch/` | Validación del lanzamiento LTI |
| `/jwks/` | Llaves públicas de la herramienta |
| `/deeplink/submit` | Entrega de selección Deep Linking |
| `/api/grade` | Recepción y envío de resultados mediante AGS |

## 3. Registro MoodleCloud verificado

| Campo | Valor |
|---|---|
| Platform ID | `https://spanish-learning-edge.moodlecloud.com` |
| Client ID | `uZ6oryFH9nmofbO` |
| Deployment ID | `1` |
| Public keyset URL | `https://spanish-learning-edge.moodlecloud.com/mod/lti/certs.php` |
| Access token URL | `https://spanish-learning-edge.moodlecloud.com/mod/lti/token.php` |
| Authentication request URL | `https://spanish-learning-edge.moodlecloud.com/mod/lti/auth.php` |

Estos datos identifican la plataforma y el deployment; no sustituyen las llaves privadas de la herramienta. Antes de una restauración debe confirmarse que el registro Moodle siga activo y que sus URL de herramienta todavía apunten al servicio restaurado.

## 4. Configuración de Cloud Run

| Parámetro | Valor verificado |
|---|---|
| Facturación | Por solicitud |
| Instancias mínimas | 0 |
| Instancias máximas del servicio | 20 |
| Concurrencia | 80 |
| Timeout | 300 segundos |
| CPU | 1 |
| Memoria | 512 MiB |
| Puerto | 8080 |
| Startup CPU boost | Activado |
| Acceso | Público para permitir lanzamientos LTI |
| Cuenta de ejecución actual | `sle-lti-service-for-claude@sle-lti-server.iam.gserviceaccount.com` |

La cuenta actual también despliega y posee permisos administrativos amplios. Esto se conserva solamente como característica del baseline; no debe replicarse en staging o producción nuevos.

## 5. Variables y secretos requeridos

### Variables de entorno

- `FLASK_SECRET_KEY` — actualmente configurada como literal; el valor no se documenta.
- `DEFAULT_WORKBOOK_URL` — fallback del workbook de demostración.
- `SECRET_PRIVATE_KEY` — referencia a Secret Manager.
- `SECRET_PUBLIC_KEY` — referencia a Secret Manager.

### Secret Manager

- `RSA_PRIVATE_KEY`
- `RSA_PUBLIC_KEY`

Las dos llaves RSA fueron creadas el 5 de abril de 2026, se replican automáticamente y no tienen vencimiento configurado. Una restauración debe recuperar versiones compatibles entre sí; nunca deben copiarse los valores a este repositorio.

### GitHub Actions

El workflow `.github/workflows/deploy.yml` despliega en cada push a `main`. Utiliza referencias a:

- `GCP_SA_KEY`;
- `FLASK_SECRET_KEY`;
- `DEFAULT_WORKBOOK_URL`.

El baseline preserva los nombres, no los valores. La futura plataforma debe sustituir `GCP_SA_KEY` por Workload Identity Federation.

## 6. Recursos auxiliares de Google Cloud

### Artifact Registry

- Repositorio: `cloud-run-source-deploy`
- Formato: Docker
- Región: `us-central1`
- Digest de restauración: registrado en la sección 1.

### Cloud Storage

Los únicos buckets observados corresponden a compilación y logs:

- `950105557003-global-cloudbuild-logs`
- `sle-lti-server_cloudbuild`

No se encontró contenido educativo alojado en Cloud Storage.

### Firestore

No existe una base de datos Firestore ni colecciones del producto en este baseline. El estado de intentos y parte del estado LTI permanecen en memoria del proceso.

### VM heredada

- Nombre: `instance-20260405-021848`
- Zona: `us-central1-a`
- Tipo: `e2-micro`
- Sistema: Debian 12
- Disco: 10 GB balanced persistent disk
- Estado al auditar: encendida
- IP pública: ninguna
- Cuenta de servicio: la misma cuenta amplia usada por Cloud Run y despliegues

La evidencia histórica indica que pudo crearse como estación de despliegue antes de consolidar GitHub Actions. Debe investigarse antes de detenerla. No forma parte de este procedimiento de restauración salvo que la revisión de `Z01` demuestre lo contrario.

## 7. Dependencias del repositorio

El código de referencia contiene, como mínimo:

- `app.py` — aplicación Flask y flujos LTI;
- `configs/tool.json` — registros de plataforma estáticos;
- `Dockerfile` — imagen de ejecución;
- `requirements.txt` — dependencias Python;
- `.github/workflows/deploy.yml` — CI/CD;
- `index.html` — interfaz/dashboard histórico;
- `PROGRESS.md` — memoria de implementación;
- `.env.example` — nombres de configuración esperados.

Antes de restaurar debe usarse el contenido correspondiente al commit registrado, no necesariamente el estado futuro de `main`.

## 8. Procedimiento de restauración controlada

Este procedimiento es una guía de emergencia. No debe ejecutarse en el proyecto original sin aprobación.

1. Crear un proyecto Cloud de recuperación aislado.
2. Recuperar el repositorio exactamente en el commit de referencia.
3. Construir la imagen desde ese commit o importar el digest preservado cuando siga disponible.
4. Crear un par RSA compatible y almacenarlo en Secret Manager, o restaurar las versiones autorizadas del par original.
5. Configurar una nueva `FLASK_SECRET_KEY`; no reutilizar el literal expuesto del prototipo.
6. Configurar el workbook de prueba autorizado.
7. Crear una cuenta de ejecución mínima con acceso únicamente a las versiones de secretos requeridas.
8. Desplegar Cloud Run con los límites registrados en la sección 4.
9. Confirmar primero `/`, `/jwks/` y la carga de configuración sin registrar todavía un LMS real.
10. Registrar la URL de recuperación en un Moodle autorizado y aislado.
11. Probar OIDC, launch, Deep Linking, creación de Line Item y grade passback.
12. Comparar resultados con los criterios de aceptación de la sección 9.

## 9. Criterios de aceptación del baseline

Una restauración reproduce el prototipo cuando:

- el endpoint de estado responde correctamente;
- Moodle completa el OIDC launch sin depender de cookies de terceros;
- el instructor puede seleccionar un workbook mediante Deep Linking;
- Moodle crea una columna calificable única para la asignación;
- el estudiante abre el workbook correcto;
- un resultado válido se acepta una sola vez;
- AGS actualiza la columna correcta;
- un reintento no crea otra columna accidental;
- no se registran nombres, emails ni valores secretos en logs de aplicación;
- el servicio puede escalar a cero y volver a iniciar.

## 10. Riesgos conocidos preservados, no aprobados para replicación

- estado en memoria incompatible con escalado multiinstancia fiable;
- configuración de instituciones dentro de `tool.json`;
- cuenta de ejecución con permisos administrativos;
- llave descargable de cuenta de servicio para GitHub;
- secreto de Flask como variable literal;
- acceso público amplio requerido por LTI pero sin una capa completa de licenciamiento;
- workbook fallback servido desde GitHub Pages;
- logging diagnóstico de AGS que debe revisarse antes de producción;
- ausencia de staging y promoción controlada;
- ausencia de persistencia multiinstitucional.

Estos elementos explican por qué el prototipo es una referencia funcional, no la infraestructura final.

## 11. Acciones expresamente fuera de este baseline

- no detener ni eliminar la VM;
- no rotar secretos;
- no revocar la llave de GitHub;
- no modificar `tool.json`;
- no cambiar el registro Moodle;
- no desplegar una nueva revisión;
- no mover tráfico;
- no archivar el repositorio;
- no retirar acceso público al prototipo.

Cada una requiere una tarea separada, evidencia previa y el punto de aprobación indicado en el Action Tracker.
