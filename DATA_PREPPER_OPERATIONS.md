# OpenSearch Data Prepper Operations Guide

## Service Management

### Starting Services

#### Full Stack Startup
```bash
# Start all services in correct order
docker-compose up -d opensearch
sleep 30  # Wait for OpenSearch to be ready
docker-compose up -d data-prepper
sleep 10  # Wait for Data Prepper to initialize
docker-compose up -d otel-collector grafana opensearch-dashboards
```

#### Selective Service Startup
```bash
# Core logging pipeline only
docker-compose up -d opensearch data-prepper otel-collector

# Add monitoring
docker-compose up -d prometheus grafana

# Add visualization
docker-compose up -d opensearch-dashboards
```

### Stopping Services

#### Graceful Shutdown
```bash
# Stop log ingestion first
docker-compose stop otel-collector

# Wait for Data Prepper to process remaining logs
sleep 30

# Stop Data Prepper
docker-compose stop data-prepper

# Stop remaining services
docker-compose stop opensearch grafana prometheus
```

#### Emergency Shutdown
```bash
# Immediate stop (may cause data loss)
docker-compose down
```

### Health Checks

#### Automated Health Check Script
```bash
#!/bin/bash
# health-check.sh

echo "=== OpenSearch Data Prepper Stack Health Check ==="

# OpenSearch
echo -n "OpenSearch: "
if curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green"'; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
fi

# Data Prepper
echo -n "Data Prepper: "
if curl -s http://localhost:4900/health | grep -q '"status":"GREEN"'; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
fi

# OTEL Collector
echo -n "OTEL Collector: "
if curl -s http://localhost:13133/ | grep -q "Server available"; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
fi

# Prometheus
echo -n "Prometheus: "
if curl -s http://localhost:9090/-/healthy | grep -q "Prometheus is Healthy"; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
fi

echo "=== End Health Check ==="
```

#### Manual Health Verification
```bash
# Check all service statuses
docker-compose ps

# Verify Data Prepper metrics endpoint
curl -X GET http://localhost:9600/metrics | head -20

# Check OpenSearch cluster health
curl -X GET http://localhost:9200/_cluster/health?pretty

# Verify log indices exist
curl -X GET "http://localhost:9200/_cat/indices/logs-*?v"
```

## Configuration Management

### Data Prepper Configuration Updates

#### Safe Configuration Change Process
```bash
# 1. Backup current configuration
cp data-prepper.yaml data-prepper.yaml.$(date +%Y%m%d_%H%M%S)

# 2. Validate new configuration
docker run --rm \
  -v $(pwd)/data-prepper.yaml:/usr/share/data-prepper/pipelines/pipelines.yaml \
  opensearchproject/data-prepper:2.10.0 \
  /usr/share/data-prepper/bin/data-prepper --validate-pipeline-configuration

# 3. Apply configuration (requires restart)
docker-compose restart data-prepper

# 4. Verify configuration loaded successfully
docker-compose logs data-prepper | tail -50
```

#### Rolling Back Configuration
```bash
# Restore previous configuration
cp data-prepper.yaml.YYYYMMDD_HHMMSS data-prepper.yaml

# Restart service
docker-compose restart data-prepper
```

### Environment Variable Updates

#### Update Data Prepper Environment
```bash
# Edit environment file
nano .env.data-prepper

# Example changes:
# DATA_PREPPER_JAVA_OPTS=-Xms1g -Xmx2g
# LOG_LEVEL=DEBUG

# Apply changes
docker-compose restart data-prepper
```

### OpenSearch Template Management

#### Update Index Template
```bash
# Apply new template
curl -X PUT "localhost:9200/_index_template/logs-template" \
  -H "Content-Type: application/json" \
  -d @opensearch-logs-template.json

# Verify template applied
curl -X GET "localhost:9200/_index_template/logs-template?pretty"

# Check template is used by new indices
curl -X GET "localhost:9200/logs-$(date +%Y.%m.%d)/_mapping?pretty"
```

## Monitoring and Alerting

### Key Performance Indicators

#### Data Prepper Metrics
```bash
# Processing rate (logs per second)
curl -s http://localhost:9600/metrics | grep "dataprepper_logs_received_total" | tail -1

# Processing latency (average time per log)
curl -s http://localhost:9600/metrics | grep "dataprepper_processing_time_seconds_sum"

# Error rate
curl -s http://localhost:9600/metrics | grep "dataprepper_processing_errors_total"

# Memory usage
curl -s http://localhost:9600/metrics | grep "jvm_memory_used_bytes{area=\"heap\"}"

# Buffer utilization
curl -s http://localhost:9600/metrics | grep "dataprepper_buffer_usage_bytes"
```

#### OpenSearch Performance
```bash
# Indexing rate
curl -X GET "localhost:9200/_nodes/stats/indices/indexing?pretty" | jq '.nodes[].indices.indexing.index_total'

# Search performance
curl -X GET "localhost:9200/_nodes/stats/indices/search?pretty" | jq '.nodes[].indices.search'

# Cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Index sizes
curl -X GET "localhost:9200/_cat/indices/logs-*?v&s=store.size:desc"
```

### Automated Monitoring Script

```bash
#!/bin/bash
# monitor-data-prepper.sh

METRICS_FILE="/tmp/data-prepper-metrics.log"
ALERT_THRESHOLD_ERROR_RATE=10  # errors per minute
ALERT_THRESHOLD_LATENCY=5000   # milliseconds

# Collect metrics
echo "$(date): Collecting Data Prepper metrics..." >> $METRICS_FILE

# Get current metrics
LOGS_PROCESSED=$(curl -s http://localhost:9600/metrics | grep "dataprepper_logs_processed_total" | awk '{print $2}')
ERRORS=$(curl -s http://localhost:9600/metrics | grep "dataprepper_processing_errors_total" | awk '{print $2}')
LATENCY=$(curl -s http://localhost:9600/metrics | grep "dataprepper_processing_time_seconds_sum" | awk '{print $2}')

# Log metrics
echo "Logs processed: $LOGS_PROCESSED, Errors: $ERRORS, Latency: $LATENCY" >> $METRICS_FILE

# Check thresholds and alert if needed
if [ "$ERRORS" -gt "$ALERT_THRESHOLD_ERROR_RATE" ]; then
    echo "ALERT: High error rate detected: $ERRORS errors" | logger -t data-prepper-monitor
fi

# Check OpenSearch connectivity
if ! curl -s http://localhost:9200/_cluster/health | grep -q "green\|yellow"; then
    echo "ALERT: OpenSearch cluster unhealthy" | logger -t data-prepper-monitor
fi
```

### Grafana Dashboard Setup

#### Import Data Prepper Dashboard
```bash
# Import the pre-configured dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana-data-prepper-dashboard.json
```

#### Key Dashboard Panels
- **Log Processing Rate**: Rate of logs processed per second
- **Processing Latency**: Average time to process each log
- **Error Rate**: Number of processing errors over time
- **Memory Usage**: JVM heap and non-heap memory consumption
- **Buffer Utilization**: How full the internal buffers are
- **OpenSearch Indexing Rate**: Rate of documents indexed

## Data Management

### Index Lifecycle Management

#### Daily Index Rotation
```bash
# Check current indices
curl -X GET "localhost:9200/_cat/indices/logs-*?v&s=index"

# Create new index for today (automatic via template)
# Indices are created automatically as logs-YYYY.MM.DD

# Close old indices (older than 7 days)
for i in {8..30}; do
    OLD_DATE=$(date -d "$i days ago" +%Y.%m.%d)
    curl -X POST "localhost:9200/logs-$OLD_DATE/_close" 2>/dev/null
done
```

#### Index Cleanup
```bash
# Delete indices older than 30 days
for i in {31..90}; do
    OLD_DATE=$(date -d "$i days ago" +%Y.%m.%d)
    curl -X DELETE "localhost:9200/logs-$OLD_DATE" 2>/dev/null
done

# Verify cleanup
curl -X GET "localhost:9200/_cat/indices/logs-*?v&s=index"
```

### Dead Letter Queue Management

#### Monitor DLQ
```bash
# Check DLQ directory size
du -sh ./data-prepper-data/dlq/

# List DLQ files
ls -la ./data-prepper-data/dlq/

# Count failed logs
wc -l ./data-prepper-data/dlq/*.json 2>/dev/null || echo "No DLQ files"
```

#### Process DLQ Files
```bash
# Examine failed logs
head -5 ./data-prepper-data/dlq/failed-logs-*.json

# Reprocess DLQ files (after fixing issues)
cat ./data-prepper-data/dlq/failed-logs-*.json | \
while read line; do
    echo "$line" | curl -X POST http://localhost:21892/log/ingest \
      -H "Content-Type: application/json" \
      -d @-
done

# Archive processed DLQ files
mkdir -p ./data-prepper-data/dlq/processed
mv ./data-prepper-data/dlq/*.json ./data-prepper-data/dlq/processed/
```

## Backup and Recovery

### Configuration Backup
```bash
# Create configuration backup
mkdir -p backups/$(date +%Y%m%d)
cp data-prepper.yaml backups/$(date +%Y%m%d)/
cp .env.data-prepper backups/$(date +%Y%m%d)/
cp opensearch-logs-template.json backups/$(date +%Y%m%d)/
cp otel-collector.yaml backups/$(date +%Y%m%d)/
```

### Data Backup
```bash
# Backup OpenSearch indices
curl -X PUT "localhost:9200/_snapshot/backup_repo" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/usr/share/opensearch/backup"
    }
  }'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/logs_$(date +%Y%m%d)" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "logs-*",
    "ignore_unavailable": true
  }'
```

### Disaster Recovery
```bash
# Restore from configuration backup
cp backups/YYYYMMDD/data-prepper.yaml ./
cp backups/YYYYMMDD/.env.data-prepper ./

# Restart services
docker-compose restart data-prepper

# Restore OpenSearch snapshot
curl -X POST "localhost:9200/_snapshot/backup_repo/logs_YYYYMMDD/_restore" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "logs-*",
    "ignore_unavailable": true
  }'
```

## Performance Tuning

### Data Prepper Optimization

#### JVM Tuning
```bash
# Edit .env.data-prepper
DATA_PREPPER_JAVA_OPTS="-Xms2g -Xmx4g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
```

#### Pipeline Tuning
```yaml
# In data-prepper.yaml
log-pipeline:
  buffer:
    buffer_size: 10240  # Increase buffer size
    batch_size: 1000    # Increase batch size
  processor:
    - date:
        match:
          - timestamp
          - "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"
        target_key: "@timestamp"
    - mutate:
        rename_keys:
          "attributes.service.name": "service_name"
  sink:
    - opensearch:
        hosts: ["http://opensearch:9200"]
        index: "logs-%{yyyy.MM.dd}"
        bulk_size: 1000      # Increase bulk size
        flush_timeout: 5000  # Increase flush timeout
```

### OpenSearch Optimization

#### Index Settings
```bash
# Optimize index settings for log data
curl -X PUT "localhost:9200/_index_template/logs-template" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["logs-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "30s",
        "index.codec": "best_compression"
      }
    }
  }'
```

## Security Considerations

### Network Security
```bash
# Restrict Data Prepper access to internal network only
# In docker-compose.yml, remove external port mappings for production

# Use TLS for OpenSearch communication
# Configure certificates in data-prepper.yaml
```

### Access Control
```bash
# Enable OpenSearch security plugin
# Configure authentication and authorization
# Set up role-based access control for indices
```

### Log Data Privacy
```bash
# Configure field masking in Data Prepper
# Remove or hash sensitive data before indexing
# Implement data retention policies
```

## Troubleshooting Runbook

### Issue: Data Prepper High CPU Usage

**Investigation Steps:**
1. Check processing metrics: `curl http://localhost:9600/metrics | grep processing_time`
2. Review pipeline configuration for inefficient processors
3. Monitor OpenSearch indexing performance
4. Check for grok pattern complexity

**Resolution:**
- Optimize grok patterns
- Increase buffer sizes to reduce processing frequency
- Scale horizontally if needed

### Issue: Logs Not Appearing in OpenSearch

**Investigation Steps:**
1. Verify OTEL Collector is sending to Data Prepper: `docker-compose logs otel-collector`
2. Check Data Prepper is receiving logs: `curl http://localhost:9600/metrics | grep received`
3. Verify OpenSearch connectivity: `curl http://localhost:9200/_cluster/health`
4. Check for processing errors: `docker-compose logs data-prepper | grep ERROR`

**Resolution:**
- Fix network connectivity issues
- Correct pipeline configuration errors
- Resolve OpenSearch mapping conflicts

### Issue: High Memory Usage

**Investigation Steps:**
1. Check JVM memory metrics: `curl http://localhost:9600/metrics | grep jvm_memory`
2. Review buffer sizes in configuration
3. Monitor garbage collection frequency

**Resolution:**
- Increase JVM heap size
- Tune buffer and batch sizes
- Enable G1 garbage collector for better performance