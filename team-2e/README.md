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
directamente desde el nodo de borde en tiempo real, y el nodo central sirve
únicamente funciones no críticas (agregación, auditoría, reportes, frontend
de operadores).

## Estructura del modelo

El Sistema 1 se organiza en **dos tipos de nodos complementarios**:

### Nodo de borde — captura y procesamiento en tiempo real (13 componentes)

- 1 edge node regional (tier `edge`) — runtime de contenedores
- 4 sensores físicos: `hydro_sensor`, `seismic_sensor`, `atmo_sensor`, `camera`
- 3 microservicios del pipeline:
  - `data_ingestion_ms` — recibe y buferiza flujos crudos de los sensores
  - `data_standarization_ms` — normaliza formatos al modelo común del SoS
  - `publisher` — publica alertas y streams a S2 y S5 (ruta rápida)
- 5 componentes de almacenamiento local:
  - `db_raw_data` + `bucket_raw_files` — datos crudos
  - `db_processed_data` + `bucket_processing` — datos procesados
  - `file_storage_metadata` — índice compartido entre raw y processed

### Nodo central — agregación, auditoría y consultas históricas (4 componentes)

- `central_processing_unit` (logic / microservice) — Unidad Principal de
  procesamiento. Recibe datos del pipeline del edge vía `data_standarization_ms`,
  genera reportes consolidados, mantiene estado de topología, y expone la
  información hacia el frontend y hacia los sistemas externos del SoS.
- `topology_status_db` (data / database) — estado actual de los nodos de
  borde activos, cuándo reportaron por última vez, qué sensores tienen
  conectados.
- `report_db` (data / database) — histórico de alertas, trazabilidad de
  eventos, estadísticas agregadas, material para análisis post-evento.
- `operator_frontend` (presentation / web_ui) — interfaz web para que
  operadores humanos consulten topología y reportes.

### Conectores internos del subsystem `data_acquisition_edge` (18)

- **Ingestión IoT (4):** 3 sensores telemétricos y 1 cámara hacia
  `data_ingestion_ms`.
- **Pipeline asincrónico (2):** `data_ingestion_ms → data_standarization_ms →
  publisher` vía message broker AMQP.
- **Persistencia en el edge (8):** escrituras de ingestión y estandarización
  sobre sus almacenamientos propios, más las dos **lecturas cruzadas** de
  `data_standarization_ms` sobre el storage raw de ingestión.
- **Uplink edge → central (1):** `data_standarization_ms → central_processing_unit`
  (REST).
- **Internos del nodo central (3):** frontend → CPU, CPU → topology_db,
  CPU → report_db.

### Subsystem `sos_frontier` (2 externos + 4 conectores SoS-level)

- **Componentes externos:**
  - `s2_early_warning` (Sistema 2)
  - `s5_c4i` (Sistema 5)
- **Conectores SoS-level:**
  - `publisher → s2_early_warning` (ruta rápida, alertas) — event_notification REST
  - `publisher → s5_c4i` (ruta rápida, streams operacionales) — data_stream REST
  - `central_processing_unit → s2_early_warning` (ruta lenta, auditoría) — data_stream REST
  - `central_processing_unit → s5_c4i` (ruta lenta, reportes históricos) — data_stream REST

## Puntos abiertos para revisión

- **RTSP/LoRaWAN no están en el enum de protocolos del metamodel.** Las
  cámaras se modelan con `WebSockets` como aproximación y los sensores con
  `MQTT`. Si el equipo considera importante representar RTSP/LoRaWAN, hay
  que abrir un PR al `metamodel.tx` compartido.
- **Atributos de calidad (availability, performance, security)** no están
  en el metamodel actual. Se añadirán en un PR posterior, alineado con la
  extensión que se está haciendo en el Lab 3.
- **Client web browser del operador:** no se modeló como componente
  explícito para mantener el alcance del modelo dentro del Sistema 1. Si
  el equipo prefiere modelarlo como `external_agency` del subsystem
  `sos_frontier`, es un cambio menor en un PR futuro.

## Estado

- Modelo con nodo de borde + nodo central. Consistente con el diagrama
  refinado del equipo (`Vista de componentes y conectores-new-project.drawio.svg`).
  Sujeto a revisión en la reunión del equipo.
