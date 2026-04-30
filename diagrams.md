# Architecture Diagrams

## System of Systems (Global)

```mermaid
graph LR
    S1_data_acquisition_edge[S1_data_acquisition_edge]
    S2_early_warning_notification[S2_early_warning_notification]
    S3_supply_resource_logistics[S3_supply_resource_logistics]
    S4_personnel_orchestration[S4_personnel_orchestration]
    externalSystems[externalSystems]
    S5_central_command_core[S5_central_command_core]

    S1_data_acquisition_edge -- "event_notification (AMQP)" --> S2_early_warning_notification
    S1_data_acquisition_edge -- "data_stream (REST)" <--> S5_central_command_core
    S1_data_acquisition_edge -- "event_notification (AMQP)" --> S5_central_command_core
    S2_early_warning_notification -- "data_stream (REST)" --> S1_data_acquisition_edge
    S2_early_warning_notification -- "control_command (gRPC)" --> S3_supply_resource_logistics
    S2_early_warning_notification -- "event_notification (Tcp)" --> S4_personnel_orchestration
    S2_early_warning_notification -- "3x data_stream (REST)" --> S5_central_command_core
    S2_early_warning_notification -- "event_notification (AMQP)" --> S5_central_command_core
    S3_supply_resource_logistics -- "event_notification (Tcp)" --> S4_personnel_orchestration
    S3_supply_resource_logistics -- "data_stream (REST)" <--> S5_central_command_core
    S3_supply_resource_logistics -- "event_notification (MQTT)" --> S5_central_command_core
    S4_personnel_orchestration -- "event_notification (Tcp)" <--> S5_central_command_core
    S4_personnel_orchestration -- "event_notification (Tcp)" --> externalSystems
    S5_central_command_core -- "control_command (gRPC)" --> S2_early_warning_notification
    externalSystems -- "data_stream (Http)" --> S4_personnel_orchestration
```

## Subsystem: S1_data_acquisition_edge

```mermaid
graph LR
    subgraph S1_data_acquisition_edge
        subgraph S1_data_acquisition_edge_sensing[sensing]
            subgraph S1_data_acquisition_edge_sensing_physical[physical]
                hydrological_sensor["hydrological_sensor<br/>(sensor)"]
                seismic_sensor["seismic_sensor<br/>(sensor)"]
                atmospheric_sensor["atmospheric_sensor<br/>(sensor)"]
                camera["camera<br/>(sensor)"]
            end
        end
        subgraph S1_data_acquisition_edge_edge[edge]
            subgraph S1_data_acquisition_edge_edge_communication[communication]
                publisher["publisher<br/>(microservice)"]
                edge_ag["edge_ag<br/>(api_gateway)"]
            end
            subgraph S1_data_acquisition_edge_edge_logic[logic]
                data_ingestion_ms["data_ingestion_ms<br/>(microservice)"]
                notification_mb["notification_mb<br/>(event_broker)"]
                data_standardization_ms["data_standardization_ms<br/>(microservice)"]
                reporting_ms["reporting_ms<br/>(microservice)"]
                logging_mb["logging_mb<br/>(event_broker)"]
                logging_ms["logging_ms<br/>(microservice)"]
            end
            subgraph S1_data_acquisition_edge_edge_data[data]
                raw_data_db["raw_data_db<br/>(database)"]
                raw_files["raw_files<br/>(bucket)"]
                processed_data_db["processed_data_db<br/>(database)"]
                processed_files["processed_files<br/>(bucket)"]
                logging_db["logging_db<br/>(database)"]
            end
        end
        subgraph S1_data_acquisition_edge_central[central]
            subgraph S1_data_acquisition_edge_central_presentation[presentation]
                operator_frontend["operator_frontend<br/>(web_ui)"]
            end
            subgraph S1_data_acquisition_edge_central_communication[communication]
                node_ag["node_ag<br/>(api_gateway)"]
                interface["interface<br/>(interface)"]
            end
            subgraph S1_data_acquisition_edge_central_logic[logic]
                topology_ms["topology_ms<br/>(microservice)"]
                reporting_center_ms["reporting_center_ms<br/>(microservice)"]
                auth_ms["auth_ms<br/>(microservice)"]
            end
            subgraph S1_data_acquisition_edge_central_data[data]
                topology_status_db["topology_status_db<br/>(database)"]
                reporting_db["reporting_db<br/>(database)"]
                auth_db["auth_db<br/>(database)"]
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
        subgraph S2_early_warning_notification_undefined_communication[communication]
            Broker_In["Broker_In<br/>(event_broker)"]
            Rec_Alertas["Rec_Alertas<br/>(interface)"]
            Emisor_Alertas["Emisor_Alertas<br/>(interface)"]
            Emisor_Logistica["Emisor_Logistica<br/>(interface)"]
            Emisor_Personal["Emisor_Personal<br/>(interface)"]
            SMS_Worker["SMS_Worker<br/>(microservice)"]
            Mobile_Worker["Mobile_Worker<br/>(microservice)"]
            Radio_TV_Worker["Radio_TV_Worker<br/>(microservice)"]
            Official_Channels_Worker["Official_Channels_Worker<br/>(microservice)"]
            Heartbeat_Monitor["Heartbeat_Monitor<br/>(microservice)"]
        end
        subgraph S2_early_warning_notification_undefined_logic[logic]
            Rules_Evaluator["Rules_Evaluator<br/>(microservice)"]
            Dispatcher["Dispatcher<br/>(microservice)"]
            Journal_Drainer["Journal_Drainer<br/>(microservice)"]
        end
        subgraph S2_early_warning_notification_undefined_data[data]
            Alert_History_DB["Alert_History_DB<br/>(database)"]
            Decision_Journal["Decision_Journal<br/>(database)"]
        end

    Broker_In -- "data_stream (AMQP)" --> Rules_Evaluator
    Rec_Alertas -- "dependency (gRPC)" --> Rules_Evaluator
    Rules_Evaluator -- "data_stream (Http)" --> Dispatcher
    Rules_Evaluator -- "dependency (Http)" --> Alert_History_DB
    Rules_Evaluator -- "dependency (Http)" --> Decision_Journal
    Rules_Evaluator -- "data_stream (AMQP)" --> Emisor_Alertas
    Rules_Evaluator -- "data_stream (AMQP)" --> Emisor_Logistica
    Rules_Evaluator -- "data_stream (AMQP)" --> Emisor_Personal
    Dispatcher -- "data_stream (AMQP)" --> SMS_Worker
    Dispatcher -- "data_stream (AMQP)" --> Mobile_Worker
    Dispatcher -- "data_stream (AMQP)" --> Radio_TV_Worker
    Dispatcher -- "data_stream (AMQP)" --> Official_Channels_Worker
    Heartbeat_Monitor -- "dependency (Http)" --> Rules_Evaluator
    Journal_Drainer -- "dependency (Http)" --> Decision_Journal
    end
```

## Subsystem: S3_supply_resource_logistics

```mermaid
graph LR
    subgraph S3_supply_resource_logistics
        subgraph S3_supply_resource_logistics_undefined_communication[communication]
            api_gateway["api_gateway<br/>(api_gateway)"]
            fifo_queue["fifo_queue<br/>(event_broker)"]
        end
        subgraph S3_supply_resource_logistics_undefined_logic[logic]
            sync_ms["sync_ms<br/>(microservice)"]
            allocation_ms["allocation_ms<br/>(microservice)"]
            stock_ms["stock_ms<br/>(microservice)"]
            concurrence_ms["concurrence_ms<br/>(microservice)"]
        end
        subgraph S3_supply_resource_logistics_undefined_data[data]
            allocation_db["allocation_db<br/>(database)"]
            stock_db["stock_db<br/>(database)"]
        end
        subgraph S3_supply_resource_logistics_undefined_external[external]
            distributed_nodes["distributed_nodes<br/>(external_agency)"]
        end

    api_gateway -- "data_stream (REST)" --> sync_ms
    api_gateway -- "data_stream (REST)" --> allocation_ms
    api_gateway -- "data_stream (REST)" --> stock_ms
    api_gateway -- "data_stream (REST)" --> concurrence_ms
    allocation_ms -- "dependency (Tcp)" --> allocation_db
    stock_ms -- "dependency (Tcp)" --> stock_db
    api_gateway -- "data_stream (AMQP)" --> fifo_queue
    fifo_queue -- "event_notification (AMQP)" --> stock_ms
    fifo_queue -- "event_notification (AMQP)" --> allocation_ms
    distributed_nodes -- "control_command (gRPC)" --> concurrence_ms
    end
```

## Subsystem: S4_personnel_orchestration

```mermaid
graph LR
    subgraph S4_personnel_orchestration
        subgraph S4_personnel_orchestration_undefined_communication[communication]
            Gateway["Gateway<br/>(api_gateway)"]
            BrokerIn["BrokerIn<br/>(event_broker)"]
            BrokerOut["BrokerOut<br/>(event_broker)"]
        end
        subgraph S4_personnel_orchestration_undefined_logic[logic]
            Controller["Controller<br/>(microservice)"]
            Blackboard["Blackboard<br/>(domain_service)"]
            Audit["Audit<br/>(microservice)"]
        end
        subgraph S4_personnel_orchestration_undefined_data[data]
            Audit_Db["Audit_Db<br/>(database)"]
            Recovery_Db["Recovery_Db<br/>(database)"]
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
        subgraph externalSystems_undefined_external[external]
            FireFighters["FireFighters<br/>(external_agency)"]
            CivilDefense["CivilDefense<br/>(external_agency)"]
            Medics["Medics<br/>(external_agency)"]
            Rescue["Rescue<br/>(external_agency)"]
        end

    end
```

## Subsystem: S5_central_command_core

```mermaid
graph LR
    subgraph S5_central_command_core
        subgraph S5_central_command_core_undefined_presentation[presentation]
            Interfaz_Usuario["Interfaz_Usuario<br/>(dashboard)"]
        end
        subgraph S5_central_command_core_undefined_communication[communication]
            Emisor_Sensores["Emisor_Sensores<br/>(interface)"]
            Emisor_Alertas["Emisor_Alertas<br/>(interface)"]
            Emisor_Logistica["Emisor_Logistica<br/>(interface)"]
            Emisor_Personal["Emisor_Personal<br/>(interface)"]
            Rec_Sensores["Rec_Sensores<br/>(interface)"]
            Rec_Alertas["Rec_Alertas<br/>(event_broker)"]
            Rec_Logistica["Rec_Logistica<br/>(interface)"]
            Rec_Personal["Rec_Personal<br/>(interface)"]
            Rec_Alertas_Journal["Rec_Alertas_Journal<br/>(interface)"]
            Rec_Alertas_Journal_Approval["Rec_Alertas_Journal_Approval<br/>(interface)"]
            S1_Message_Queue["S1_Message_Queue<br/>(event_broker)"]
            S3_Message_Queue["S3_Message_Queue<br/>(event_broker)"]
            Health_Probe["Health_Probe<br/>(microservice)"]
        end
        subgraph S5_central_command_core_undefined_logic[logic]
            Procesador_Central["Procesador_Central<br/>(microservice)"]
            Motor_Decisiones["Motor_Decisiones<br/>(domain_service)"]
            Gen_Comandos["Gen_Comandos<br/>(microservice)"]
        end
        subgraph S5_central_command_core_undefined_data[data]
            BD_Operacional["BD_Operacional<br/>(database)"]
            Historial["Historial<br/>(database)"]
        end

    Procesador_Central -- "dependency" --> BD_Operacional
    BD_Operacional -- "dependency" --> Historial
    Procesador_Central -- "control_command" --> Motor_Decisiones
    BD_Operacional -- "data_stream (gRPC)" --> Motor_Decisiones
    Motor_Decisiones -- "data_stream (Http)" --> Interfaz_Usuario
    Motor_Decisiones -- "control_command (gRPC)" --> Gen_Comandos
    Gen_Comandos -- "control_command (gRPC)" --> Emisor_Sensores
    Gen_Comandos -- "control_command (gRPC)" --> Emisor_Alertas
    Gen_Comandos -- "control_command (gRPC)" --> Emisor_Logistica
    Gen_Comandos -- "control_command (gRPC)" --> Emisor_Personal
    S1_Message_Queue -- "event_notification (AMQP)" --> Procesador_Central
    S3_Message_Queue -- "event_notification (AMQP)" --> Procesador_Central
    Rec_Sensores -- "data_stream (gRPC)" --> Procesador_Central
    Rec_Alertas -- "event_notification (AMQP)" --> Procesador_Central
    Rec_Alertas_Journal -- "data_stream (AMQP)" --> Procesador_Central
    Rec_Alertas_Journal_Approval -- "data_stream (AMQP)" --> Procesador_Central
    Rec_Logistica -- "data_stream (gRPC)" --> Procesador_Central
    Rec_Personal -- "data_stream (gRPC)" --> Procesador_Central
    Health_Probe -- "event_notification (REST)" --> Procesador_Central
    Procesador_Central -- "event_notification (REST)" --> Health_Probe
    end
```
