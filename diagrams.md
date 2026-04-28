# Architecture Diagrams

## System of Systems (Global)

```mermaid
graph TD
    data_acquisition_edge[[data_acquisition_edge]]
    s2[[s2]]
    s3[[s3]]
    s4[[s4]]
    externalSystems[[externalSystems]]
    s5[[s5]]

    data_acquisition_edge -- "event_notification (AMQP)" --> s2
    data_acquisition_edge -- "event_notification (AMQP)" --> s5
    data_acquisition_edge -- "data_stream (Http)" --> s2
    data_acquisition_edge -- "data_stream (Http)" --> s5
    s2 -- "event_notification (Tcp)" --> s4
    s5 -- "event_notification (Tcp)" --> s4
    s3 -- "event_notification (Tcp)" --> s4
```

## Subsystem: data_acquisition_edge

```mermaid
graph TD
    edge_node_regional["edge_node_regional<br/>(edge_node)"]
    hydro_sensor["hydro_sensor<br/>(sensor)"]
    seismic_sensor["seismic_sensor<br/>(sensor)"]
    atmo_sensor["atmo_sensor<br/>(sensor)"]
    camera["camera<br/>(sensor)"]
    data_ingestion_ms["data_ingestion_ms<br/>(microservice)"]
    data_standarization_ms["data_standarization_ms<br/>(microservice)"]
    publisher["publisher<br/>(microservice)"]
    db_raw_data_storage["db_raw_data_storage<br/>(database)"]
    bucket_raw_files_storage["bucket_raw_files_storage<br/>(data_lake)"]
    processed_data_db["processed_data_db<br/>(database)"]
    bucket_processing_file_storage["bucket_processing_file_storage<br/>(data_lake)"]
    file_storage_metadata["file_storage_metadata<br/>(database)"]
    processing_unit_ms["processing_unit_ms<br/>(microservice)"]
    topology_status_db["topology_status_db<br/>(database)"]
    report_db["report_db<br/>(database)"]
    operator_frontend["operator_frontend<br/>(web_ui)"]
    interface_gateway["interface_gateway<br/>(api_gateway)"]
    client_web_browser["client_web_browser<br/>(web_ui)"]

    hydro_sensor -- "data_stream (MQTT)" --> data_ingestion_ms
    seismic_sensor -- "data_stream (MQTT)" --> data_ingestion_ms
    atmo_sensor -- "data_stream (MQTT)" --> data_ingestion_ms
    camera -- "data_stream (WebSockets)" --> data_ingestion_ms
    data_ingestion_ms -- "event_notification (AMQP)" --> data_standarization_ms
    data_standarization_ms -- "event_notification (AMQP)" --> publisher
    data_ingestion_ms -- "dependency" --> db_raw_data_storage
    data_ingestion_ms -- "dependency" --> bucket_raw_files_storage
    data_ingestion_ms -- "dependency" --> file_storage_metadata
    data_standarization_ms -- "dependency" --> processed_data_db
    data_standarization_ms -- "dependency" --> bucket_processing_file_storage
    data_standarization_ms -- "dependency" --> file_storage_metadata
    data_standarization_ms -- "dependency" --> db_raw_data_storage
    data_standarization_ms -- "dependency" --> bucket_raw_files_storage
    publisher -- "dependency" --> processed_data_db
    publisher -- "dependency" --> bucket_processing_file_storage
    data_standarization_ms -- "data_stream (Http)" --> interface_gateway
    interface_gateway -- "data_stream (Http)" --> processing_unit_ms
    processing_unit_ms -- "data_stream (Http)" --> interface_gateway
    operator_frontend -- "data_stream (Http)" --> processing_unit_ms
    client_web_browser -- "data_stream (Http)" --> operator_frontend
    processing_unit_ms -- "dependency" --> topology_status_db
    processing_unit_ms -- "dependency" --> report_db
```

## Subsystem: s2

```mermaid
graph TD

```

## Subsystem: s3

```mermaid
graph TD

```

## Subsystem: s4

```mermaid
graph TD
    Gateway["Gateway<br/>(api_gateway)"]
    BrokerIn["BrokerIn<br/>(event_broker)"]
    Controller["Controller<br/>(microservice)"]
    Blackboard["Blackboard<br/>(domain_service)"]
    Audit["Audit<br/>(microservice)"]
    Health["Health<br/>(microservice)"]
    BrokerOut["BrokerOut<br/>(event_broker)"]
    Audit_Db["Audit_Db<br/>(database)"]
    Recovery_Db["Recovery_Db<br/>(database)"]

    Gateway -- "data_stream (AMQP)" --> BrokerIn
    BrokerIn -- "event_notification (AMQP)" --> Controller
    BrokerIn -- "event_notification (AMQP)" --> Audit
    Controller -- "dependency (Http)" --> Blackboard
    Controller -- "control_command (Tcp)" --> BrokerOut
    Blackboard -- "dependency" --> Recovery_Db
    Audit -- "dependency" --> Audit_Db
    BrokerOut -- "event_notification (Tcp)" --> Audit
    BrokerOut -- "event_notification (Tcp)" --> s5
```

## Subsystem: externalSystems

```mermaid
graph TD
    FireFighters["FireFighters<br/>(external_agency)"]
    CivilDefense["CivilDefense<br/>(external_agency)"]
    Medics["Medics<br/>(external_agency)"]
    Rescue["Rescue<br/>(external_agency)"]

    FireFighters -- "data_stream (Http)" --> Gateway
    CivilDefense -- "data_stream (Http)" --> Gateway
    Medics -- "data_stream (Http)" --> Gateway
    Rescue -- "data_stream (Http)" --> Gateway
    BrokerOut -- "event_notification (Tcp)" --> FireFighters
    BrokerOut -- "event_notification (Tcp)" --> CivilDefense
    BrokerOut -- "event_notification (Tcp)" --> Medics
    BrokerOut -- "event_notification (Tcp)" --> Rescue
```

## Subsystem: s5

```mermaid
graph TD

```
