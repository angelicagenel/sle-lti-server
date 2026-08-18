# SLE — catálogo unificado, empaquetado y calificación

## Principio rector

El contenido pedagógico y la asignación LMS son objetos distintos.

- **Contenido:** vive una vez, se versiona y se puede reutilizar.
- **Asignación:** congela una versión del contenido para un curso, semana, categoría, política de intentos y regla de nota.

Por eso una universidad puede colocar L01 en semanas distintas sin duplicar el contenido y, al mismo tiempo, cada grupo conserva una calificación semanal estable que no cambia cuando se publica otra semana.

## Empaquetado comercial recomendado

La licencia institucional se vende como **SP101 / Elementary Spanish I completo por semestre**, no como compras separadas. Internamente, el producto se publica por unidad para permitir mantenimiento y selección.

| Componente | Empaque de autoría/distribución | Granularidad de catálogo | Calificación predeterminada |
|---|---|---|---|
| eBook Rise | 1 curso Rise por unidad; 4–5 lecciones dentro | Unidad + lección | No calificable por defecto; contenido/actividad de clase |
| Compendio / Claves Rise | 1 curso Rise por unidad; 4–5 secciones/lecciones | Unidad + lección | No calificable; lectura/estudio |
| Cuéntame Rise | 1 lección narrativa por unidad | Unidad | No calificable; ancla de storytelling |
| Trazos | HTML o actividad LMS cuando requiera respuesta; Rise sólo si es demostrativo | Lección + actividad | Práctica o entrega manual según tipo |
| Reto / producción | Rise para instrucciones/media; HTML o Assignment LMS para entrega | Lección + tarea | Rúbrica/manual o completion según actividad |
| Workbooks HTML | Aplicación versionada; ejercicios seleccionables | Lección + categoría + ejercicio | Numérica; passback por assignment semanal |
| Exámenes tradicionales HTML | Objeto de evaluación separado | Unidad + versión | Numérica; intentos restringidos |
| FACT | Aplicación externa compartida | Prompt/actividad | Futuro: completion/incomplete; score numérico después |
| Cards / flashcards / cheat sheets | Recursos HTML compartidos | Tema + nivel + relaciones con unidades/lecciones | No calificable |

No convertir workbooks a Rise/SCORM. Rise conserva el contenido instructivo y multimedia; HTML conserva práctica, evaluación y datos de resultado.

## Identificador canónico

Formato legible recomendado:

`SP101-U01-L01-{TYPE}-{SLUG}`

Ejemplos:

- `SP101-U01-L01-EBOOK-MUCHO-GUSTO`
- `SP101-U01-L01-WB-GRAMMAR-SER`
- `SP101-U01-L01-WB-VOCAB-FERIA`
- `SP101-U01-L01-LISTENING-FERIA`
- `SP101-U01-CUENTAME-01`
- `SP101-U01-FACT-INTRODUCTION`

El ID no contiene semana: la semana pertenece a la asignación del curso, no al contenido.

## Campos mínimos del catálogo

| Campo | Uso |
|---|---|
| `catalog_item_id` | Identidad estable |
| `course_code`, `unit`, `lesson` | Ubicación curricular |
| `type` | `rise_ebook`, `rise_compendium`, `rise_story`, `html_workbook`, `assessment`, `fact`, `study_resource` |
| `category` | `grammar`, `vocabulary`, `listening`, `assessment`, `production`, `study` |
| `title`, `description` | Texto al instructor/estudiante |
| `version` y `status` | Borrador, piloto, publicado, retirado |
| `delivery` | Rise URL, Cloud asset, app route o LMS-native |
| `gradable` y `grading_mode` | Ninguno, numérico, completion, manual |
| `exercise_manifest` | IDs, puntos máximos y respuestas/reglas evaluables |
| `prerequisites` y `related_items` | Relaciones pedagógicas |
| `accessibility_status` | Revisión pendiente/aprobada |
| `license_scope` | Nivel, producto y disponibilidad institucional |

## Selector del instructor

Orden recomendado:

1. Curso/nivel.
2. Unidad.
3. Lección.
4. **Semana del curso**.
5. Hasta **tres categorías** para esa semana.
6. Ejercicios dentro de cada categoría.
7. Puntos, intentos y regla de nota.
8. Vista previa y Assign.

Cada categoría seleccionada crea un assignment/line item separado. No crear una sola columna acumulativa para todo el workbook ni una columna por cada ejercicio. La unidad pedagógica visible en el gradebook es **semana + categoría**.

Ejemplo:

- `Semana 2 · L01 · Grammar & Comprehension`
- `Semana 2 · L01 · Vocabulary`
- `Semana 2 · L01 · Listening`

Si una institución coloca L01 en la semana 3, los títulos y line items pertenecen a semana 3 sin duplicar los objetos del catálogo.

## Esquema de calificaciones

### Workbooks objetivos

- Una selección de ejercicios dentro de una categoría = un assignment.
- Score del intento = suma de puntos validados / máximo del snapshot.
- Regla predeterminada = **mejor intento**.
- Regla alternativa del instructor = **último intento**.
- Intentos predeterminados = **3**.
- Opciones permitidas = 1–5 o ilimitados.
- El instructor puede cambiar la política antes de que existan intentos; después, el cambio requiere confirmación y recalcula explícitamente.
- Cada envío conserva `raw_score`, `max_score`, `effective_score`, número de intento y versión de contenido.
- AGS recibe el score efectivo después de cada intento y puede reemplazar el valor anterior de ese mismo line item.

El promedio de intentos no entra en el MVP. Puede añadirse sólo si una institución lo solicita.

### Estabilidad semanal

La nota de una semana nunca se obtiene de un workbook maestro mutable. Cada asignación guarda un snapshot inmutable:

- `catalog_version_id`
- ejercicios seleccionados
- máximo de puntos
- semana
- categoría
- política de intentos
- política best/last

Una actualización posterior del workbook crea otra versión y no altera assignments ya lanzados.

### Rise y material de estudio

- eBook, Compendio y Cuéntame no generan puntos numéricos por defecto.
- Si una institución exige trazabilidad, puede crearse una actividad completion/incomplete separada, pero no debe mezclarse con las notas objetivas.
- El Compendio es material de consulta; no es el mejor lugar para exigir completion.
- El eBook puede usarse en clase sin crear ruido artificial en el gradebook.

### FACT

Fase futura inicial:

- Resultado LMS: `Complete` cuando el procesamiento termina correctamente; `Incomplete` antes de ello.
- Audio: no se conserva; archivos temporales se eliminan después del procesamiento.
- Intentos: ilimitados por defecto para práctica; el instructor puede limitar a 3–5.
- No enviar score FACT numérico al LMS hasta validar confiabilidad, transparencia y política institucional.
- Fase posterior: score numérico con mejor intento por defecto y último intento como alternativa.

Si el instructor necesita una grabación para revisión humana, el estudiante la sube directamente a Moodle/Canvas; FACT no se convierte en repositorio de audio.

## Decisiones abiertas

1. Nombres definitivos de las tres categorías semanales. Para el piloto pueden conservarse `Grammar`, `Vocabulary` y `Listening`; a futuro podrían consolidarse pedagógicamente.
2. Si los exámenes viven como cuarta familia fuera del selector semanal o sustituyen una de las tres categorías en semana de evaluación.
3. Política exacta de completion para Trazos y producciones no numéricas.
4. Ventana de retención de intentos y grade events por contrato institucional.

