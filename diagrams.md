# Architecture Diagrams

## System of Systems (Global)

```mermaid
graph LR
    S1_data_acquisition_edge[[S1_data_acquisition_edge]]
    S2_early_warning_notification[[S2_early_warning_notification]]
    S3_supply_resource_logistics[[S3_supply_resource_logistics]]
    S4_personnel_orchestration[[S4_personnel_orchestration]]
    externalSystems[[externalSystems]]
    S5_central_command_core[[S5_central_command_core]]

    S1_data_acquisition_edge -- "event_notification (AMQP)" --> S2_early_warning_notification
    S1_data_acquisition_edge -- "event_notification (AMQP)" --> S5_central_command_core
    S1_data_acquisition_edge -- "data_stream (REST)" --> S5_central_command_core
    S5_central_command_core -- "data_stream (REST)" --> S1_data_acquisition_edge
    S2_early_warning_notification -- "data_stream (REST)" --> S1_data_acquisition_edge
    S2_early_warning_notification -- "event_notification (Tcp)" --> S4_personnel_orchestration
    S5_central_command_core -- "event_notification (Tcp)" --> S4_personnel_orchestration
    S4_personnel_orchestration -- "event_notification (Tcp)" --> S5_central_command_core
    S3_supply_resource_logistics -- "event_notification (Tcp)" --> S4_personnel_orchestration
    externalSystems -- "data_stream (Http)" --> S4_personnel_orchestration
    externalSystems -- "data_stream (Http)" --> S4_personnel_orchestration
    externalSystems -- "data_stream (Http)" --> S4_personnel_orchestration
    externalSystems -- "data_stream (Http)" --> S4_personnel_orchestration
    S4_personnel_orchestration -- "event_notification (Tcp)" --> externalSystems
    S4_personnel_orchestration -- "event_notification (Tcp)" --> externalSystems
    S4_personnel_orchestration -- "event_notification (Tcp)" --> externalSystems
    S4_personnel_orchestration -- "event_notification (Tcp)" --> externalSystems
```

## Subsystem: S1_data_acquisition_edge

```mermaid
graph LR
    subgraph S1_data_acquisition_edge
        subgraph S1_data_acquisition_edge_sensing[sensing]
            subgraph S1_data_acquisition_edge_sensing_physical[physical]
                hydrological_sensor["hydrological_sensor<br/>[sensing/physical]<br/>(sensor)"]
                seismic_sensor["seismic_sensor<br/>[sensing/physical]<br/>(sensor)"]
                atmospheric_sensor["atmospheric_sensor<br/>[sensing/physical]<br/>(sensor)"]
                camera["camera<br/>[sensing/physical]<br/>(sensor)"]
            end
        end
        subgraph S1_data_acquisition_edge_edge[edge]
            subgraph S1_data_acquisition_edge_edge_communication[communication]
                publisher["publisher<br/>[edge/communication]<br/>(microservice)"]
                edge_ag["edge_ag<br/>[edge/communication]<br/>(api_gateway)"]
            end
            subgraph S1_data_acquisition_edge_edge_logic[logic]
                data_ingestion_ms["data_ingestion_ms<br/>[edge/logic]<br/>(microservice)"]
                notification_mb["notification_mb<br/>[edge/logic]<br/>(event_broker)"]
                data_standardization_ms["data_standardization_ms<br/>[edge/logic]<br/>(microservice)"]
                reporting_ms["reporting_ms<br/>[edge/logic]<br/>(microservice)"]
                logging_mb["logging_mb<br/>[edge/logic]<br/>(event_broker)"]
                logging_ms["logging_ms<br/>[edge/logic]<br/>(microservice)"]
            end
            subgraph S1_data_acquisition_edge_edge_data[data]
                raw_data_db["raw_data_db<br/>[edge/data]<br/>(database)"]
                raw_files["raw_files<br/>[edge/data]<br/>(bucket)"]
                processed_data_db["processed_data_db<br/>[edge/data]<br/>(database)"]
                processed_files["processed_files<br/>[edge/data]<br/>(bucket)"]
                logging_db["logging_db<br/>[edge/data]<br/>(database)"]
            end
        end
        subgraph S1_data_acquisition_edge_central[central]
            subgraph S1_data_acquisition_edge_central_presentation[presentation]
                operator_frontend["operator_frontend<br/>[central/presentation]<br/>(web_ui)"]
            end
            subgraph S1_data_acquisition_edge_central_communication[communication]
                node_ag["node_ag<br/>[central/communication]<br/>(api_gateway)"]
                interface["interface<br/>[central/communication]<br/>(interface)"]
            end
            subgraph S1_data_acquisition_edge_central_logic[logic]
                topology_ms["topology_ms<br/>[central/logic]<br/>(microservice)"]
                reporting_center_ms["reporting_center_ms<br/>[central/logic]<br/>(microservice)"]
                auth_ms["auth_ms<br/>[central/logic]<br/>(microservice)"]
            end
            subgraph S1_data_acquisition_edge_central_data[data]
                topology_status_db["topology_status_db<br/>[central/data]<br/>(database)"]
                reporting_db["reporting_db<br/>[central/data]<br/>(database)"]
                auth_db["auth_db<br/>[central/data]<br/>(database)"]
            end
        end

    hydrological_sensor -- "event_notification (MQTT)" --> data_ingestion_ms
    seismic_sensor -- "event_notification (MQTT)" --> data_ingestion_ms
    atmospheric_sensor -- "event_notification (MQTT)" --> data_ingestion_ms
    camera -- "data_stream (RTSP)" --> data_ingestion_ms
    data_ingestion_ms -- "event_notification (AMQP)" --> notification_mb
    notification_mb -- "event_notification (AMQP)" --> data_standardization_ms
    edge_ag -- "data_stream (REST)" --> reporting_ms
    edge_ag -- "data_stream (REST)" --> logging_ms
    data_ingestion_ms -- "dependency (Tcp)" --> raw_data_db
    data_ingestion_ms -- "dependency (Http)" --> raw_files
    data_standardization_ms -- "dependency (Tcp)" --> raw_data_db
    data_standardization_ms -- "dependency (Http)" --> raw_files
    data_standardization_ms -- "dependency (Tcp)" --> processed_data_db
    data_standardization_ms -- "dependency (Http)" --> processed_files
    publisher -- "dependency (Tcp)" --> processed_data_db
    publisher -- "dependency (Http)" --> processed_files
    reporting_ms -- "dependency (Tcp)" --> processed_data_db
    reporting_ms -- "dependency (Http)" --> processed_files
    logging_mb -- "event_notification (AMQP)" --> logging_ms
    logging_ms -- "dependency (Tcp)" --> logging_db
    edge_ag -- "event_notification (AMQP)" --> logging_mb
    data_ingestion_ms -- "event_notification (AMQP)" --> logging_mb
    data_standardization_ms -- "event_notification (AMQP)" --> logging_mb
    reporting_ms -- "event_notification (AMQP)" --> logging_mb
    publisher -- "event_notification (AMQP)" --> logging_mb
    interface -- "data_stream (REST)" --> edge_ag
    operator_frontend -- "data_stream (REST)" --> node_ag
    interface -- "data_stream (REST)" --> node_ag
    node_ag -- "data_stream (REST)" --> topology_ms
    node_ag -- "data_stream (REST)" --> reporting_center_ms
    node_ag -- "data_stream (REST)" --> auth_ms
    topology_ms -- "dependency (Tcp)" --> topology_status_db
    reporting_center_ms -- "dependency (Tcp)" --> reporting_db
    auth_ms -- "dependency (Tcp)" --> auth_db
    end
```

## Subsystem: S2_early_warning_notification

```mermaid
graph LR
    subgraph S2_early_warning_notification

    end
```

## Subsystem: S3_supply_resource_logistics

```mermaid
graph LR
    subgraph S3_supply_resource_logistics

    end
```

## Subsystem: S4_personnel_orchestration

```mermaid
graph LR
    subgraph S4_personnel_orchestration
        subgraph S4_personnel_orchestration_undefined[undefined]
            subgraph S4_personnel_orchestration_undefined_communication[communication]
                Gateway["Gateway<br/>[undefined/communication]<br/>(api_gateway)"]
                BrokerIn["BrokerIn<br/>[undefined/communication]<br/>(event_broker)"]
                BrokerOut["BrokerOut<br/>[undefined/communication]<br/>(event_broker)"]
            end
            subgraph S4_personnel_orchestration_undefined_logic[logic]
                Controller["Controller<br/>[undefined/logic]<br/>(microservice)"]
                Blackboard["Blackboard<br/>[undefined/logic]<br/>(domain_service)"]
                Audit["Audit<br/>[undefined/logic]<br/>(microservice)"]
                Health["Health<br/>[undefined/logic]<br/>(microservice)"]
            end
            subgraph S4_personnel_orchestration_undefined_data[data]
                Audit_Db["Audit_Db<br/>[undefined/data]<br/>(database)"]
                Recovery_Db["Recovery_Db<br/>[undefined/data]<br/>(database)"]
            end
        end

    Gateway -- "data_stream (AMQP)" --> BrokerIn
    BrokerIn -- "event_notification (AMQP)" --> Controller
    BrokerIn -- "event_notification (AMQP)" --> Audit
    Controller -- "dependency (Http)" --> Blackboard
    Controller -- "control_command (Tcp)" --> BrokerOut
    Blackboard -- "dependency" --> Recovery_Db
    Audit -- "dependency" --> Audit_Db
    BrokerOut -- "event_notification (Tcp)" --> Audit
    end
```

## Subsystem: externalSystems

```mermaid
graph LR
    subgraph externalSystems
        subgraph externalSystems_undefined[undefined]
        end

    end
```

## Subsystem: S5_central_command_core

```mermaid
graph LR
    subgraph S5_central_command_core

    end
```
