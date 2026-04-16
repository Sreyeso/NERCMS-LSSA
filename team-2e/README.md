# team-2e — Sistema 1: Data Acquisition and Edge Computing

Modelo arquitectónico del **Sistema 1** del SoS NERCMS — captura de datos
desde sensores heterogéneos (hidrológicos, sísmicos, atmosféricos, cámaras),
procesamiento en nodos de borde regionales, y consolidación en un nodo
central para auditoría, topología y reportes.

## Archivos

- `model.arch` — instancia del `metamodel.tx` compartido. Describe el
  Sistema 1 como un `subsystem` con todos sus componentes (nodo de borde
  y nodo central) y las interfaces hacia Sistema 2 (Early Warning) y
  Sistema 5 (C4I).

## Responsable

- **Team leader:** Julián Bustos (`@dbustos106`)
- **Miembros:** César Pineda, Daniel Silva, José Alarcón, María Jara, Johan Medina

## Atributo de calidad principal

**Disponibilidad / operación en degraded connectivity.** El Sistema 1 debe
continuar capturando y procesando datos localmente incluso cuando se pierde
conectividad con el resto del SoS. Como consecuencia, el nodo central **no
está en la ruta crítica de alertas**: las alertas a S2 y S5 se publican
directamente desde el nodo de borde en tiempo real a través de un message
broker AMQP asincrónico, y el nodo central sirve funciones de agregación,
auditoría, reportes y consultas históricas a través de un API gateway
(`interface_gateway`).

## Estructura del modelo

El Sistema 1 se organiza en **dos tipos de nodos complementarios**:

### Nodo de borde — captura y procesamiento en tiempo real (13 componentes)

- 1 edge node regional (tier `edge`) — runtime de contenedores
- 4 sensores físicos:
  - `hydro_sensor` → label del SVG: *Sensores hidrológicos*
  - `seismic_sensor` → label del SVG: *Sensores sísmicos*
  - `atmo_sensor` → label del SVG: *Sensores atmosféricos*
  - `camera` → label del SVG: *Cámaras*
- 3 microservicios del pipeline:
  - `data_ingestion_ms` — recibe y buferiza flujos crudos de los sensores
  - `data_standarization_ms` — normaliza formatos al modelo común del SoS
  - `publisher` — publica alertas y streams a S2 y S5 (ruta rápida, AMQP)
- 5 componentes de almacenamiento local:
  - `db_raw_data_storage` + `bucket_raw_files_storage` — datos crudos
  - `processed_data_db` + `bucket_processing_file_storage` — datos procesados
  - `file_storage_metadata` — índice compartido entre raw y processed

### Nodo central — agregación, auditoría y consultas históricas (6 componentes)

- `interface_gateway` (communication / api_gateway) — API gateway del nodo
  central. Recibe datos del pipeline del edge vía `data_standarization_ms`,
  media la comunicación bidireccional con `processing_unit_ms`, y expone
  las interfaces hacia los sistemas externos S2 y S5. Es el único punto de
  entrada y salida del nodo central hacia el exterior.
- `processing_unit_ms` (logic / microservice) — Unidad Principal de
  procesamiento. Recibe datos del edge a través del `interface_gateway`,
  genera reportes consolidados, mantiene estado de topología, y envía
  datos de auditoría y reportes históricos de vuelta al `interface_gateway`
  para su distribución a S2 y S5.
- `topology_status_db` (data / database) — estado actual de los nodos de
  borde activos, cuándo reportaron por última vez, qué sensores tienen
  conectados.
- `report_db` (data / database) — histórico de alertas, trazabilidad de
  eventos, estadísticas agregadas, material para análisis post-evento.
- `operator_frontend` (presentation / web_ui) — interfaz web para que
  operadores humanos consulten topología y reportes (capa T1 del tiered model).
- `client_web_browser` (presentation / web_ui) — navegador web del
  operador, modelado explícitamente como cliente del `operator_frontend`.

### Conectores internos del subsystem `data_acquisition_edge` (23)

- **Ingestión IoT (4):** 3 sensores telemétricos y 1 cámara hacia
  `data_ingestion_ms` — MQTT para telemetría, WebSockets para video.
- **Pipeline asincrónico (2):** `data_ingestion_ms → data_standarization_ms →
  publisher` vía message broker AMQP con `style=MessageQueue`.
- **Persistencia en el edge (10):** escrituras de ingestión y estandarización
  sobre sus almacenamientos propios; dos **lecturas cruzadas** de
  `data_standarization_ms` sobre el storage raw de ingestión; y dos
  **lecturas del publisher** sobre el storage procesado
  (`publisher → processed_data_db` y `publisher → bucket_processing_file_storage`).
  El publisher recibe notificación por broker y lee los datos reales
  directamente del storage procesado (patrón Claim Check), evitando el
  overhead de pasar blobs grandes en base64 a través del broker.
- **Uplink edge → central (1):** `data_standarization_ms → interface_gateway`
  sobre Http con estilo RequestResponse.
- **Internos del nodo central (6):**
  - `interface_gateway → processing_unit_ms` — gateway reenvía datos
    entrantes al procesador central (Http, RequestResponse).
  - `processing_unit_ms → interface_gateway` — el procesador envía datos
    de salida a través del gateway hacia S2/S5 (Http, RequestResponse).
  - `operator_frontend → processing_unit_ms` — frontend consulta al
    procesador (Http, RequestResponse).
  - `client_web_browser → operator_frontend` — navegador del operador
    accede al frontend (Http, RequestResponse).
  - `processing_unit_ms → topology_status_db` — dependencia de datos.
  - `processing_unit_ms → report_db` — dependencia de datos.

### Subsystem `sos_frontier` (2 externos + 4 conectores SoS-level)

- **Componentes externos:**
  - `s2_early_warning` → label del SVG: *Sistema 2*
  - `s5_c4i` → label del SVG: *Sistema 5*
- **Conectores SoS-level:**
  - `publisher → s2_early_warning` (ruta rápida, alertas) — `event_notification` AMQP, `MessageQueue`
  - `publisher → s5_c4i` (ruta rápida, streams operacionales) — `event_notification` AMQP, `MessageQueue`
  - `interface_gateway → s2_early_warning` (ruta lenta, auditoría) — `data_stream` Http, `RequestResponse`
  - `interface_gateway → s5_c4i` (ruta lenta, reportes históricos) — `data_stream` Http, `RequestResponse`

La **ruta rápida** (publisher → S2/S5) usa AMQP asincrónico a través de un
message broker, garantizando entrega desacoplada de alertas y streams
operacionales incluso bajo condiciones de conectividad degradada.
La **ruta lenta** (interface_gateway → S2/S5) usa Http sincrónico desde el
nodo central para consultas históricas y auditoría.

## Decisiones de nomenclatura frente al SVG

La mayoría de los identificadores del modelo coinciden literalmente con los
labels del SVG final (`Vista de componentes y conectores-final-final.drawio.svg`).
En los casos donde los labels del SVG no son compatibles con la sintaxis de
identificadores de textX (espacios, paréntesis, tildes), se aplicaron
conversiones a `snake_case` minúsculo preservando el orden y contenido del
label original:

| Label del SVG | Identificador en el modelo |
|---|---|
| `DB Raw data storage` | `db_raw_data_storage` |
| `Bucket (Raw Files Storage)` | `bucket_raw_files_storage` |
| `Processed data (DB)` | `processed_data_db` |
| `Bucket processing (File Storage)` | `bucket_processing_file_storage` |
| `File Storage Metada` | `file_storage_metadata` (corregido el typo `Metada`) |
| `Processing_unit_ms` | `processing_unit_ms` (minúscula inicial por consistencia snake_case) |
| `Interface` | `interface_gateway` (renombrado para evitar conflicto con keyword genérica) |
| `Client web browser` | `client_web_browser` |

## Puntos abiertos para revisión

- **RTSP/LoRaWAN no están en el enum de protocolos del metamodel.** Las
  cámaras se modelan con `WebSockets` como aproximación y los sensores con
  `MQTT`. Si el equipo considera importante representar RTSP/LoRaWAN, hay
  que abrir un PR al `metamodel.tx` compartido.
- **Atributos de calidad (availability, performance, security)** no están
  en el metamodel actual. Se añadirán en un PR posterior, alineado con la
  extensión que se está haciendo en el Lab 3.
- **Typo en el label del SVG (`File Storage Metada`):** el modelo formal
  usa `file_storage_metadata` (con la `ta` final). Se recomienda corregir
  el SVG en el próximo refinamiento para mantener consistencia visual.

## Estado

- Modelo alineado con la versión final del diagrama del equipo
  (`Vista de componentes y conectores-final-final.drawio.svg`), usando la
  versión actualizada del `metamodel.tx` compartido. Incluye:
  - **Componente `interface_gateway`** — API gateway del nodo central que
    media toda la comunicación externa (T2 Communication).
  - **Componente `client_web_browser`** — navegador del operador (T1 Presentation).
  - **Ruta rápida AMQP** — publisher → S2/S5 vía message broker asincrónico.
  - **Ruta lenta Http** — interface_gateway → S2/S5 vía Http sincrónico.
  - **Patrón Claim Check** del publisher sobre el storage procesado.
  - **Comunicación bidireccional** interface_gateway ↔ processing_unit_ms.
