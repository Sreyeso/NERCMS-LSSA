# team-2e — Sistema 1: Data Acquisition and Edge Computing

Modelo arquitectónico del **Sistema 1** del SoS NERCMS — captura de datos
desde sensores heterogéneos (hidrológicos, sísmicos, atmosféricos, cámaras)
y su procesamiento en nodos de borde.

## Archivos

- `model.arch` — instancia del `metamodel.tx` compartido. Describe el
  Sistema 1 como un `subsystem` con todos sus componentes internos y las
  interfaces hacia Sistema 2 (Early Warning) y Sistema 5 (C4I).

## Responsable

- **Team leader:** Julián Bustos (`@dbustos106`)
- **Miembros:** César Pineda, Daniel Silva, José Alarcón, María Jara, Johan Medina

## Atributo de calidad principal

**Disponibilidad / operación en degraded connectivity.** El Sistema 1 debe
continuar capturando y procesando datos localmente incluso cuando se pierde
conectividad con el resto del SoS.

## Estructura del modelo

- **`data_acquisition_edge`** — el Sistema 1 propiamente dicho:
  - 1 edge node regional (tier `edge`)
  - 4 sensores físicos: hidrológico, sísmico, atmosférico, cámara
  - 3 microservicios: `data_ingestion_ms`, `data_standarization_ms`, `publisher`
  - 5 componentes de datos: 2 DBs + 2 data lakes (raw/processed) + 1 metadata index
  - 14 conectores internos (4 data streams de sensores, 2 event notifications del pipeline, 6 dependencies a datos + 2 del standarization)

- **`sos_frontier`** — subsystem de agencias externas para poder modelar
  las conexiones inter-sistema:
  - `s2_early_warning` (Sistema 2)
  - `s5_c4i` (Sistema 5)

- **Conectores SoS-level (2):**
  - `publisher → s2_early_warning` (event_notification, REST)
  - `publisher → s5_c4i` (data_stream, REST)

## Puntos abiertos para revisión

- **RTSP/LoRaWAN no están en el enum de protocolos del metamodel.** Las
  cámaras se modelan con `WebSockets` como aproximación y los sensores con
  `MQTT`. Si el equipo considera importante representar RTSP/LoRaWAN, hay
  que abrir un PR al `metamodel.tx`.
- **Atributos de calidad (availability, performance, security)** no están
  en el metamodel actual. Se añadirán en un PR posterior, alineado con la
  extensión que se está haciendo en el Lab 3.
- **Reportes históricos hacia Sistema 5:** debate pendiente (Julián dice
  que no es responsabilidad de S1; Daniel dice que podría). Por ahora el
  modelo solo publica streams de situación vía `data_stream`, no reportes
  históricos.

## Estado

- Modelo inicial — versión 1. Sujeto a revisión en la reunión del equipo.
