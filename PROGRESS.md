# SLE LTI 1.3 — Progreso del Proyecto
**Spanish Learning Edge LLC · Abril 2026**

---

## 1. Qué se construyó

Servidor LTI 1.3 completo para Spanish Learning Edge (SLE), una plataforma de aprendizaje
de español para instituciones universitarias. El servidor permite que los workbooks HTML
estáticos (en GitHub Pages) reporten calificaciones por ejercicio individual al gradebook
de Canvas mediante el protocolo LTI 1.3 + AGS (Assignment and Grade Services).

---

## 2. Arquitectura

```
Canvas LMS
  │
  │  1. LTI Launch POST (JWT firmado)
  ▼
Flask Server (Cloud Run)
  │  2. Verifica JWT con PyLTI1p3
  │  3. Genera attempt_id + token HS256 (2h, un solo uso)
  │
  │  4. Redirect con ?attempt_id=xxx&token=yyy
  ▼
HTML Workbook (GitHub Pages)
  │  5. Estudiante completa el ejercicio
  │  6. POST /api/grade {attempt_id, token, score, max_score, block_id}
  ▼
Flask Server (Cloud Run)
  │  7. Valida token (firma, expiración, uso único)
  │  8. Llama Canvas AGS → PUT score al lineitem
  ▼
Canvas Gradebook ✓
```

**Stack:**
- Lenguaje: Python 3.11
- Framework: Flask 3.0.3
- Librería LTI: PyLTI1p3 2.0.0
- Hosting: Google Cloud Run (us-central1)
- CI/CD: GitHub Actions → Cloud Run en cada push a `main`
- Llaves RSA: GCP Secret Manager (montadas como env vars en Cloud Run)

---

## 3. URL del Servicio

```
https://sle-lti-server-950105557003.us-central1.run.app
```

Endpoints disponibles:
- `GET  /`             → health check
- `GET  /api/health`   → estado + número de attempts en memoria
- `GET  /jwks/`        → JWKS público (requerido por Canvas)
- `GET/POST /login/`   → OIDC login initiation
- `POST /launch/`      → LTI launch handler
- `POST /api/grade`    → recibe scores desde los HTMLs

---

## 4. Proyecto GCP

| Campo | Valor |
|-------|-------|
| Project ID | `sle-lti-server` |
| Project Number | `950105557003` |
| Region | `us-central1` |
| Servicio Cloud Run | `sle-lti-server` |

---

## 5. Service Account

```
sle-lti-service-for-claude@sle-lti-server.iam.gserviceaccount.com
```

Roles asignados:
- Cloud Run Admin
- Storage Admin
- Cloud Build Editor
- Artifact Registry Writer
- Secret Manager Secret Accessor

---

## 6. Repositorio GitHub

```
https://github.com/angelicagenel/sle-lti-server
```

Estructura:
```
sle-lti-server/
├── app.py                        # Servidor Flask principal
├── requirements.txt              # Dependencias Python
├── Dockerfile                    # Container image
├── index.html                    # Workbook HTML de prueba (verbo SER)
├── configs/tool.json             # Configuración LTI (requiere client_id real)
├── .github/workflows/deploy.yml  # CI/CD → Cloud Run
├── .gitignore
├── .env.example
└── PROGRESS.md                   # Este archivo
```

---

## 7. Imagen en Artifact Registry

```
us-central1-docker.pkg.dev/sle-lti-server/cloud-run-source-deploy/sle-lti-server
```

Repositorio: `cloud-run-source-deploy` (us-central1, formato Docker)

---

## 8. Secrets en GCP Secret Manager

| Nombre del Secret | Contenido |
|-------------------|-----------|
| `RSA_PRIVATE_KEY` | Llave privada RSA 4096-bit (PEM) |
| `RSA_PUBLIC_KEY`  | Llave pública RSA (PEM) |

Montados en Cloud Run como variables de entorno (`--set-secrets`):
- `SECRET_PRIVATE_KEY=RSA_PRIVATE_KEY:latest`
- `SECRET_PUBLIC_KEY=RSA_PUBLIC_KEY:latest`

---

## 9. GitHub Secrets configurados

| Secret | Descripción |
|--------|-------------|
| `GCP_SA_KEY` | JSON del service account para autenticación en GitHub Actions |
| `FLASK_SECRET_KEY` | String aleatorio seguro para firmar tokens JWT de sesión |
| `DEFAULT_WORKBOOK_URL` | URL del HTML de prueba en GitHub Pages |

---

## 10. Pendiente

### Registro en Canvas (Developer Key LTI)

Estos pasos deben hacerse manualmente en Canvas:

1. Ir a **Admin → Developer Keys → + LTI Key**
2. Configurar las URLs del servidor:
   - **Login URL:** `https://sle-lti-server-950105557003.us-central1.run.app/login/`
   - **Launch URL:** `https://sle-lti-server-950105557003.us-central1.run.app/launch/`
   - **JWK URL:** `https://sle-lti-server-950105557003.us-central1.run.app/jwks/`
   - **Redirect URIs:** `https://sle-lti-server-950105557003.us-central1.run.app/launch/`
3. Guardar y copiar el **`client_id`** generado por Canvas
4. Activar el Developer Key y anotar el **`deployment_id`**

### Actualizar configs/tool.json

Reemplazar los placeholders con los valores reales de Canvas:

```json
{
  "https://canvas.instructure.com": [
    {
      "client_id": "CANVAS_CLIENT_ID_REAL",
      "deployment_ids": ["DEPLOYMENT_ID_REAL"],
      ...
    }
  ]
}
```

### Prueba end-to-end

1. Crear un Assignment en Canvas como External Tool
2. Apuntar al Launch URL del servidor
3. Configurar `DEFAULT_WORKBOOK_URL` con la URL del `index.html` en GitHub Pages
4. Abrir la tarea como estudiante → verificar redirección al HTML
5. Responder el ejercicio → verificar que el score aparece en el gradebook de Canvas

---

## 11. Próximos pasos para completar la integración con Canvas

1. **Registrar Developer Key LTI** en Canvas (ver sección 10)
2. **Actualizar `configs/tool.json`** con `client_id` y `deployment_id` reales → commit + push
3. **Publicar `index.html`** en GitHub Pages (repo `sle-workbooks` o Pages del repo actual)
4. **Actualizar secret `DEFAULT_WORKBOOK_URL`** en GitHub con la URL de GitHub Pages
5. **Crear Assignment en Canvas** apuntando al servidor LTI
6. **Prueba end-to-end:** launch → HTML → grade passback → Canvas gradebook
7. **Producción:** migrar `attempts {}` de memoria a Firestore o Cloud SQL para persistencia entre instancias
