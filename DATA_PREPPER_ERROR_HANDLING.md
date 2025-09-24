# Data Prepper Error Handling and Dead Letter Queue Configuration

This document describes the comprehensive error handling and Dead Letter Queue (DLQ) configuration implemented for the OpenSearch Data Prepper pipeline.

## Overview

The error handling system provides robust mechanisms for:
- Processing failures with retry strategies
- Dead Letter Queue management for failed logs
- Circuit breaker patterns to prevent cascading failures
- Comprehensive error monitoring and alerting
- Automatic recovery and reprocessing capabilities

## Architecture

### Error Handling Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OTEL Logs     │───▶│  Data Prepper   │───▶│   OpenSearch    │
│                 │    │   Processing    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼ (on error)
                       ┌─────────────────┐
                       │  Retry Logic    │
                       │  (Exponential   │
                       │   Backoff)      │
                       └─────────────────┘
                                │
                                ▼ (after max retries)
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Dead Letter    │───▶│  DLQ Archive    │
                       │     Queue       │    │   & Cleanup     │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼ (reprocessing)
                       ┌─────────────────┐
                       │ DLQ Reprocessing│
                       │    Pipeline     │
                       └─────────────────┘
```

## Configuration Files

### 1. Enhanced Data Prepper Pipeline (`data-prepper.yaml`)

The main pipeline configuration includes:

#### Global Error Handling
- **Log Level**: INFO with JSON formatting for structured logging
- **Circuit Breaker**: Prevents cascading failures with configurable thresholds
- **Error Categorization**: Different handling strategies for different error types

#### Processor Error Handling
- **Date Processor**: `on_parse_failure: keep_original` - preserves original timestamp on parsing failure
- **Mutate Processor**: `tags_on_failure: ["_mutate_failure"]` - tags failed transformations
- **Grok Processor**: `tags_on_failure: ["_grok_parse_failure"]` - tags parsing failures with timeout protection

#### Enhanced Sink Configuration
- **Retry Strategy**: Exponential backoff with jitter (1s → 30s max delay)
- **Connection Management**: Configurable timeouts and connection pooling
- **DLQ Integration**: Automatic routing to DLQ on persistent failures

### 2. Error Handling Configuration (`data-prepper-error-config.yaml`)

Comprehensive error handling policies including:

#### Error Categories
- **Parsing Errors**: Tag and continue processing
- **Transformation Errors**: Tag and continue processing  
- **Validation Errors**: Route to DLQ
- **Sink Errors**: Retry then route to DLQ
- **Critical Errors**: Stop pipeline and alert

#### DLQ Configuration
- **File Rotation**: 100MB max file size, 10 files per category
- **Retention Policy**: 7 days default, configurable per category
- **Monitoring**: Size and file count alerting
- **Cleanup**: Automatic cleanup based on retention policies

#### Retry Policies
- **Default**: 5 attempts with exponential backoff
- **OpenSearch Indexing**: Retry on specific HTTP status codes (429, 502, 503, 504)
- **Connection Failures**: Linear backoff for connection issues
- **File Operations**: Fixed delay for file system operations

### 3. Environment Configuration (`.env.data-prepper`)

Enhanced environment variables for error handling:

```bash
# Error Handling
ERROR_LOG_LEVEL=INFO
ERROR_LOG_FORMAT=JSON
MAX_ERRORS_THRESHOLD=100
CIRCUIT_BREAKER_TIMEOUT=30s

# DLQ Configuration
DLQ_RETENTION_DAYS=7
DLQ_MAX_SIZE=1gb
DLQ_MAX_FILE_SIZE=100mb
DLQ_CLEANUP_INTERVAL=1h

# Retry Configuration
MAX_RETRIES=5
RETRY_BACKOFF_STRATEGY=exponential
INITIAL_RETRY_DELAY=1s
MAX_RETRY_DELAY=30s

# Alerting
ALERTING_ENABLED=true
ALERT_ERROR_RATE_THRESHOLD=0.05
ALERT_DLQ_SIZE_THRESHOLD=500mb
```

## Dead Letter Queue Management

### DLQ Structure

```
/usr/share/data-prepper/data/dlq/
├── logs-validation-failures-2024-01-15-14.json
├── logs-sink-failures-2024-01-15-14.json
├── logs-critical-failures-2024-01-15-14.json
├── archive/
│   ├── processed-logs-validation-failures-2024-01-14.json
│   └── processed-logs-sink-failures-2024-01-14.json
└── reprocessing/
    └── logs-sink-failures-2024-01-15-13.json
```

### DLQ Management Script (`dlq-management.sh`)

Comprehensive DLQ management utility with commands:

#### Status and Monitoring
```bash
# Check DLQ status
./dlq-management.sh status

# List DLQ files with filters
./dlq-management.sh list --category sink_failures --verbose

# Monitor DLQ in real-time
./dlq-management.sh monitor --verbose
```

#### Maintenance Operations
```bash
# Cleanup old DLQ files
./dlq-management.sh cleanup --retention 3 --dry-run

# Validate DLQ file format
./dlq-management.sh validate

# Reprocess failed logs
./dlq-management.sh reprocess --category validation_failures
```

#### Data Export and Analysis
```bash
# Export DLQ data for analysis
./dlq-management.sh export --date 2024-01-15 --output analysis.json
```

### DLQ Pipelines

#### DLQ Reprocessing Pipeline
- **Source**: Monitors DLQ files for reprocessing
- **Processing**: Adds reprocessing metadata and attempt counting
- **Sink**: Routes to separate reprocessed index with limited retries

#### Error Monitoring Pipeline
- **Source**: Internal Data Prepper metrics
- **Processing**: Filters error metrics and adds alerting metadata
- **Sink**: Routes to error monitoring index and stdout for visibility

## Error Types and Handling

### 1. Parsing Errors
- **Grok Pattern Failures**: Tagged with `_grok_parse_failure`
- **Date Parsing Failures**: Original timestamp preserved
- **Action**: Continue processing with error tags

### 2. Transformation Errors
- **Field Mapping Conflicts**: Tagged with `_mutate_failure`
- **Type Conversion Errors**: Logged and tagged
- **Action**: Continue processing with error tags

### 3. Validation Errors
- **Missing Required Fields**: Routed to DLQ
- **Schema Violations**: Routed to DLQ
- **Action**: Send to validation failures DLQ

### 4. Sink Errors
- **OpenSearch Connection Failures**: Retry with backoff
- **Indexing Failures**: Retry then DLQ
- **Authentication Failures**: Direct to DLQ (no retry)
- **Action**: Retry then route to sink failures DLQ

### 5. Critical Errors
- **Out of Memory**: Heap dump and pipeline stop
- **System Errors**: Alert and pipeline stop
- **Action**: Stop pipeline and send critical alert

## Monitoring and Alerting

### Metrics Collection

Data Prepper exposes error-related metrics on port 9600:

```
# Error rate metrics
data_prepper_error_rate{pipeline="log-pipeline",type="parsing"}
data_prepper_error_rate{pipeline="log-pipeline",type="sink"}

# DLQ metrics
data_prepper_dlq_size_bytes{category="validation_failures"}
data_prepper_dlq_file_count{category="sink_failures"}

# Circuit breaker metrics
data_prepper_circuit_breaker_state{pipeline="log-pipeline"}
data_prepper_circuit_breaker_failure_count{pipeline="log-pipeline"}
```

### Prometheus Configuration

The `prometheus.yml` includes Data Prepper metrics scraping:

```yaml
- job_name: 'data-prepper'
  static_configs:
    - targets: ['data-prepper:9600']
  scrape_interval: 30s
  metrics_path: /metrics
```

### Grafana Dashboard

The error handling dashboard (`grafana-data-prepper-dashboard.json`) includes:

- **Error Rate Panels**: Real-time error rate monitoring
- **DLQ Size Tracking**: DLQ growth and cleanup monitoring  
- **Circuit Breaker Status**: Circuit breaker state visualization
- **Retry Metrics**: Retry attempt and success rate tracking

### Alert Rules

Configured alert thresholds:

- **High Error Rate**: > 5% error rate over 5 minutes
- **DLQ Size Warning**: > 500MB DLQ storage
- **Circuit Breaker Open**: Circuit breaker activation
- **Pipeline Failure**: Complete pipeline failure

## Testing and Validation

### Error Handling Test Script (`test-error-handling.py`)

Comprehensive test suite for validating error handling:

#### Test Scenarios
1. **Valid Log Processing**: Baseline functionality test
2. **Invalid Timestamp**: Date parsing error handling
3. **Missing Required Fields**: Validation error handling
4. **Grok Parse Failure**: Unstructured log handling
5. **Field Mapping Error**: Type conversion error handling
6. **Unicode Encoding Error**: Character encoding issues
7. **Oversized Document**: Size limit error handling
8. **Invalid JSON Structure**: Malformed request handling

#### Usage Examples
```bash
# Run basic error handling tests
python3 test-error-handling.py

# Run load test with mixed valid/error logs
python3 test-error-handling.py --load-test --num-logs 1000 --error-rate 0.1

# Test against custom endpoints
python3 test-error-handling.py --otel-endpoint http://custom:4318
```

### Integration Testing

The test script validates:
- **Service Health**: All components are running
- **Error Processing**: Errors are handled correctly
- **DLQ Functionality**: Failed logs reach DLQ
- **Metrics Collection**: Error metrics are exposed
- **Recovery**: System remains stable after errors

## Operational Procedures

### Daily Operations

1. **Monitor DLQ Size**: Check DLQ growth trends
2. **Review Error Rates**: Monitor error rate dashboards
3. **Check Circuit Breaker**: Ensure no persistent failures
4. **Validate Cleanup**: Confirm DLQ cleanup is working

### Weekly Maintenance

1. **DLQ Analysis**: Review DLQ contents for patterns
2. **Reprocess Failed Logs**: Attempt reprocessing of recoverable failures
3. **Update Retry Policies**: Adjust based on error patterns
4. **Performance Review**: Analyze error handling performance impact

### Incident Response

#### High Error Rate
1. Check Data Prepper health and logs
2. Verify OpenSearch connectivity
3. Review recent configuration changes
4. Check resource utilization

#### DLQ Size Alert
1. Analyze DLQ contents for error patterns
2. Check if errors are recoverable
3. Increase cleanup frequency if needed
4. Investigate root cause of failures

#### Circuit Breaker Activation
1. Check downstream service health (OpenSearch)
2. Review error logs for failure patterns
3. Manually reset circuit breaker if appropriate
4. Address root cause before reset

## Best Practices

### Configuration
- **Start Conservative**: Begin with higher retry counts and longer delays
- **Monitor and Adjust**: Use metrics to optimize retry policies
- **Category-Specific**: Configure different policies for different error types
- **Resource Limits**: Set appropriate DLQ size and retention limits

### Monitoring
- **Proactive Alerting**: Set alerts before issues become critical
- **Trend Analysis**: Monitor error rate trends over time
- **Correlation**: Correlate errors with system changes
- **Documentation**: Document error patterns and resolutions

### Maintenance
- **Regular Cleanup**: Ensure DLQ cleanup is working properly
- **Capacity Planning**: Monitor DLQ growth for capacity planning
- **Testing**: Regularly test error handling with synthetic errors
- **Updates**: Keep error handling configuration updated with system changes

## Troubleshooting

### Common Issues

#### DLQ Files Not Created
- Check DLQ directory permissions
- Verify DLQ configuration in pipeline
- Check Data Prepper logs for errors

#### High Memory Usage
- Review DLQ file sizes and retention
- Check for memory leaks in error handling
- Adjust JVM heap settings if needed

#### Slow Error Recovery
- Review retry delay configuration
- Check OpenSearch performance
- Optimize circuit breaker settings

#### Missing Error Metrics
- Verify Prometheus scraping configuration
- Check Data Prepper metrics endpoint
- Review firewall and network settings

### Log Analysis

Key log patterns to monitor:

```bash
# Error processing logs
grep "ERROR" /var/log/data-prepper/error.log

# DLQ operations
grep "dlq" /var/log/data-prepper/data-prepper.log

# Circuit breaker events
grep "circuit.*breaker" /var/log/data-prepper/data-prepper.log

# Retry attempts
grep "retry" /var/log/data-prepper/data-prepper.log
```

## Security Considerations

### DLQ Data Protection
- **Sensitive Data**: DLQ files may contain sensitive log data
- **Access Control**: Restrict access to DLQ directories
- **Encryption**: Consider encrypting DLQ files at rest
- **Retention**: Implement secure deletion of expired DLQ files

### Error Log Security
- **Log Sanitization**: Ensure error logs don't expose sensitive data
- **Access Logging**: Log access to DLQ management tools
- **Audit Trail**: Maintain audit trail of DLQ operations

## Performance Impact

### Resource Usage
- **Memory**: Error handling adds ~10-15% memory overhead
- **CPU**: Retry logic adds ~5-10% CPU overhead
- **Storage**: DLQ files require additional storage capacity
- **Network**: Retry attempts increase network traffic

### Optimization
- **Batch Processing**: Process DLQ files in batches
- **Compression**: Compress DLQ files to save space
- **Async Processing**: Use async processing for DLQ operations
- **Resource Limits**: Set appropriate resource limits for error handling

This comprehensive error handling and DLQ system ensures robust log processing with graceful failure handling, automatic recovery, and detailed monitoring capabilities.