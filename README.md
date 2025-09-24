# Observability Stack with OpenSearch Data Prepper

This project provides a comprehensive observability stack using Docker Compose, featuring log processing through OpenSearch Data Prepper, metrics collection with Prometheus, and visualization through Grafana and OpenSearch Dashboards.

## Architecture Overview

The stack includes:

- **Log Processing**: OTEL Collector → Data Prepper → OpenSearch (+ Loki for legacy support)
- **Metrics**: Prometheus → Grafana
- **Tracing**: Jaeger/Tempo
- **Databases**: MySQL, PostgreSQL, RabbitMQ
- **Visualization**: Grafana, OpenSearch Dashboards

## Quick Start

### Prerequisites

[Install Docker](https://docs.docker.com/engine/install/)

### Starting the Stack

```bash
# Start all services
docker-compose up -d

# Or using newer Docker Compose syntax
docker compose up -d

# Start specific services
docker-compose up -d opensearch data-prepper otel-collector grafana
```

### Stopping the Stack

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: This will delete all data)
docker-compose down -v
```

## MySQL

[MySql](https://www.mysql.com/)

Password

- root / 1234

```sql
CREATE USER 'user1'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON *.* TO 'user1'@'%';
FLUSH PRIVILEGES;
```

For MySQL Exporter

```sql
CREATE USER 'exporter'@'%' IDENTIFIED BY '1234qwer' WITH MAX_USER_CONNECTIONS 3;
GRANT ALL PRIVILEGES ON *.* TO 'exporter'@'%';
FLUSH PRIVILEGES;
```

Keycloak

```sql
CREATE DATABASE IF NOT EXISTS `keycloak`
USE `keycloak`;

CREATE USER 'keycloak'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON *.* TO 'keycloak'@'%';
FLUSH PRIVILEGES;
```

## RabbitMQ

[RabbitMQ](https://www.rabbitmq.com/)

User/Password

- user/1234

## OpenSearch Data Prepper Pipeline

### Overview

OpenSearch Data Prepper processes logs from OTEL Collector, transforms them, and indexes them into OpenSearch for advanced search and analytics capabilities.

### Pipeline Flow

```
Applications → OTEL Collector → Data Prepper → OpenSearch → OpenSearch Dashboards
                     ↓
                   Loki → Grafana (Legacy)
```

### Configuration Files

- `data-prepper.yaml` - Main pipeline configuration
- `opensearch-logs-template.json` - Index template for log mapping
- `.env.data-prepper` - Environment variables

### Service Endpoints

- **Data Prepper OTLP**: `localhost:21892` (gRPC)
- **Data Prepper API**: `localhost:4900` (HTTP)
- **Data Prepper Metrics**: `localhost:9600` (Prometheus)
- **OpenSearch**: `localhost:9200`
- **OpenSearch Dashboards**: `localhost:5601`

### Sending Logs to Data Prepper

#### Using OTEL Collector (Automatic)

Logs are automatically routed from OTEL Collector to Data Prepper when the stack is running.

#### Direct OTLP Submission

```bash
# Example: Send test logs directly
curl -X POST http://localhost:4318/v1/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resourceLogs": [{
      "resource": {
        "attributes": [{
          "key": "service.name",
          "value": {"stringValue": "test-service"}
        }]
      },
      "scopeLogs": [{
        "logRecords": [{
          "timeUnixNano": "'$(date +%s%N)'",
          "severityText": "INFO",
          "body": {"stringValue": "Test log message"}
        }]
      }]
    }]
  }'
```

### Log Query Examples

#### OpenSearch REST API

```bash
# Search all logs
curl -X GET "localhost:9200/logs-*/_search?pretty"

# Search by service name
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "service_name": "my-service"
      }
    }
  }'

# Search by log level
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "severity_text": "ERROR"
      }
    }
  }'

# Time range query (last 1 hour)
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "gte": "now-1h"
        }
      }
    }
  }'

# Complex query with filters
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"match": {"service_name": "web-app"}},
          {"range": {"@timestamp": {"gte": "now-24h"}}}
        ],
        "filter": [
          {"term": {"severity_text": "ERROR"}}
        ]
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}],
    "size": 100
  }'
```

#### OpenSearch Dashboards Queries

Access OpenSearch Dashboards at `http://localhost:5601` and use these query examples in Discover:

```
# Basic text search
service_name:"web-app" AND severity_text:"ERROR"

# Time range with wildcard
@timestamp:[now-1h TO now] AND message:*exception*

# Field existence
_exists_:trace_id AND service_name:"api-service"

# Range queries
response_time:[100 TO 500] AND status_code:>=400
```

### Dashboard Usage

#### OpenSearch Dashboards

1. **Access**: Navigate to `http://localhost:5601`
2. **Index Pattern**: Create index pattern `logs-*` to view all log indices
3. **Discover**: Use the Discover tab to search and filter logs
4. **Visualizations**: Create charts and graphs from log data
5. **Dashboards**: Combine visualizations into comprehensive dashboards

#### Grafana Dashboards

1. **Access**: Navigate to `http://localhost:3000` (admin/admin)
2. **Data Prepper Metrics**: Import the dashboard from `grafana-data-prepper-dashboard.json`
3. **Key Metrics**:
   - Log processing rate
   - Processing latency
   - Error rates
   - Memory and CPU usage

### Monitoring and Alerting

#### Data Prepper Health Check

```bash
# Check Data Prepper health
curl -X GET http://localhost:4900/health

# Expected response
{
  "status": "GREEN",
  "statusReason": "All components are healthy"
}
```

#### Prometheus Metrics

```bash
# View all Data Prepper metrics
curl -X GET http://localhost:9600/metrics

# Key metrics to monitor:
# - dataprepper_logs_received_total
# - dataprepper_logs_processed_total
# - dataprepper_processing_errors_total
# - dataprepper_processing_time_seconds
```

#### Log Processing Verification

```bash
# Check if logs are being processed
./verify_opensearch_logs.py

# Generate test logs for verification
python3 generate_test_logs.py
```

## Service Configuration

### OpenSearch

- **URL**: `http://localhost:9200`
- **Dashboards**: `http://localhost:5601`
- **Default Index Pattern**: `logs-YYYY.MM.dd`

### Data Prepper

- **Config**: `data-prepper.yaml`
- **Environment**: `.env.data-prepper`
- **Data Directory**: `./data-prepper-data`
- **DLQ Directory**: `./data-prepper-data/dlq`

## Grafana

[Grafana](https://grafana.com/)

User/Password

- admin/admin

## Troubleshooting Guide

### Common Issues and Solutions

#### Data Prepper Not Starting

**Symptoms**: Data Prepper container exits or fails to start

**Solutions**:

```bash
# Check container logs
docker-compose logs data-prepper

# Verify configuration syntax
docker run --rm -v $(pwd)/data-prepper.yaml:/usr/share/data-prepper/pipelines/pipelines.yaml \
  opensearchproject/data-prepper:2.10.0 \
  /usr/share/data-prepper/bin/data-prepper --validate-pipeline-configuration

# Check file permissions
ls -la data-prepper.yaml
chmod 644 data-prepper.yaml

# Restart with fresh configuration
docker-compose restart data-prepper
```

#### No Logs Appearing in OpenSearch

**Symptoms**: Logs sent to OTEL Collector but not visible in OpenSearch

**Diagnosis Steps**:

```bash
# 1. Check OTEL Collector logs
docker-compose logs otel-collector

# 2. Check Data Prepper logs
docker-compose logs data-prepper

# 3. Verify Data Prepper is receiving logs
curl -X GET http://localhost:9600/metrics | grep dataprepper_logs_received_total

# 4. Check OpenSearch indices
curl -X GET "localhost:9200/_cat/indices/logs-*?v"

# 5. Test direct log submission
curl -X POST http://localhost:21892/log/ingest \
  -H "Content-Type: application/json" \
  -d '{"message": "test log", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"}'
```

**Common Fixes**:

- Verify network connectivity between services
- Check Data Prepper pipeline configuration
- Ensure OpenSearch is healthy and accepting connections
- Verify index template is properly applied

#### High Memory Usage

**Symptoms**: Data Prepper consuming excessive memory

**Solutions**:

```bash
# Check current memory usage
docker stats data-prepper

# Adjust JVM heap size in .env.data-prepper
echo "DATA_PREPPER_JAVA_OPTS=-Xms512m -Xmx1g" >> .env.data-prepper

# Tune buffer sizes in data-prepper.yaml
# Reduce buffer_size and batch_size in processors

# Restart with new settings
docker-compose restart data-prepper
```

#### Processing Delays

**Symptoms**: Logs appearing in OpenSearch with significant delay

**Diagnosis**:

```bash
# Check processing metrics
curl -X GET http://localhost:9600/metrics | grep processing_time

# Monitor queue sizes
curl -X GET http://localhost:9600/metrics | grep queue_size

# Check OpenSearch bulk indexing performance
curl -X GET "localhost:9200/_nodes/stats/indices/indexing"
```

**Optimizations**:

- Increase batch_size in OpenSearch sink
- Adjust flush_timeout settings
- Scale Data Prepper horizontally if needed
- Optimize OpenSearch cluster settings

#### Dead Letter Queue Issues

**Symptoms**: Logs appearing in DLQ instead of OpenSearch

**Investigation**:

```bash
# Check DLQ directory
ls -la ./data-prepper-data/dlq/

# Examine failed logs
cat ./data-prepper-data/dlq/failed-logs-*.json

# Check Data Prepper error logs
docker-compose logs data-prepper | grep ERROR
```

**Resolution**:

- Fix data format issues in source logs
- Adjust grok patterns for log parsing
- Verify OpenSearch mapping compatibility
- Increase retry limits if transient failures

#### OpenSearch Connection Issues

**Symptoms**: Data Prepper cannot connect to OpenSearch

**Checks**:

```bash
# Test OpenSearch connectivity from Data Prepper container
docker-compose exec data-prepper curl -X GET http://opensearch:9200/_cluster/health

# Check OpenSearch logs
docker-compose logs opensearch

# Verify network configuration
docker network ls
docker network inspect $(docker-compose ps -q opensearch | head -1)
```

#### Performance Monitoring

**Key Metrics to Monitor**:

```bash
# Log processing rate (logs/second)
curl -s http://localhost:9600/metrics | grep "dataprepper_logs_processed_total"

# Processing latency (milliseconds)
curl -s http://localhost:9600/metrics | grep "dataprepper_processing_time_seconds"

# Error rate
curl -s http://localhost:9600/metrics | grep "dataprepper_processing_errors_total"

# Memory usage
curl -s http://localhost:9600/metrics | grep "jvm_memory_used_bytes"

# OpenSearch indexing rate
curl -X GET "localhost:9200/_nodes/stats/indices/indexing" | jq '.nodes[].indices.indexing.index_total'
```

### Service Management Commands

#### Start/Stop Individual Services

```bash
# Start only core logging services
docker-compose up -d opensearch data-prepper otel-collector

# Stop Data Prepper for maintenance
docker-compose stop data-prepper

# Restart with configuration changes
docker-compose restart data-prepper

# View service status
docker-compose ps
```

#### Configuration Reload

```bash
# Reload Data Prepper configuration (requires restart)
docker-compose restart data-prepper

# Reload OTEL Collector configuration
docker-compose restart otel-collector

# Apply new OpenSearch template
curl -X PUT "localhost:9200/_index_template/logs-template" \
  -H "Content-Type: application/json" \
  -d @opensearch-logs-template.json
```

#### Data Management

```bash
# Clean old log indices (older than 30 days)
curl -X DELETE "localhost:9200/logs-$(date -d '30 days ago' +%Y.%m.%d)"

# Check index sizes
curl -X GET "localhost:9200/_cat/indices/logs-*?v&s=store.size:desc"

# Force index refresh
curl -X POST "localhost:9200/logs-*/_refresh"

# Clear DLQ files
rm -f ./data-prepper-data/dlq/*
```

### Emergency Procedures

#### Complete Stack Reset

```bash
# Stop all services
docker-compose down

# Remove all data (WARNING: This deletes all logs and metrics)
docker-compose down -v
rm -rf ./data-prepper-data/*

# Start fresh
docker-compose up -d
```

#### Data Prepper Recovery

```bash
# Backup current configuration
cp data-prepper.yaml data-prepper.yaml.backup

# Reset to minimal configuration
cat > data-prepper-minimal.yaml << EOF
log-pipeline:
  source:
    otel_logs_source:
      port: 21892
  sink:
    - stdout:
EOF

# Test with minimal config
docker run --rm -p 21892:21892 \
  -v $(pwd)/data-prepper-minimal.yaml:/usr/share/data-prepper/pipelines/pipelines.yaml \
  opensearchproject/data-prepper:2.10.0

# Gradually add back features once basic functionality works
```

### Getting Help

- **Data Prepper Documentation**: <https://opensearch.org/docs/latest/data-prepper/>
- **OpenSearch Documentation**: <https://opensearch.org/docs/latest/>
- **OTEL Collector Documentation**: <https://opentelemetry.io/docs/collector/>
- **Issue Tracking**: Check container logs and metrics endpoints for detailed error information
