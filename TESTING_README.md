# OpenSearch Data Prepper Pipeline Integration Testing

This directory contains comprehensive integration testing scripts for the OpenSearch Data Prepper pipeline. The tests verify the end-to-end log processing flow: `otel-collector → data-prepper → opensearch`.

## Overview

The testing suite includes:

1. **Integration Test Scripts** - Complete end-to-end pipeline testing
2. **Test Data Generators** - Generate realistic test log data
3. **OpenSearch Verification Tools** - Search and verify logs in OpenSearch
4. **Bash and Python implementations** - Choose your preferred approach

## Prerequisites

Before running the tests, ensure:

1. **Services are running**: Start all services with `docker-compose up -d`
2. **Python dependencies** (for Python scripts): `requests` library

   ```bash
   pip install requests
   ```

3. **Required tools** (for bash script): `curl`, `jq`, `openssl`

## Quick Start

### 1. Run Complete Integration Tests

**Python version (recommended):**

```bash
# Run all tests
./test_integration.py

# Run tests with cleanup
./test_integration.py --cleanup

# Generate more test logs
./test_integration.py --num-logs 10
```

**Bash version:**

```bash
# Run all tests
./test-integration.sh

# Run tests with cleanup
./test-integration.sh --cleanup
```

### 2. Check Test Results

The integration tests will verify:

- ✅ All services are running and healthy
- ✅ Test logs are sent to OTEL Collector
- ✅ Data Prepper processes and transforms logs
- ✅ OpenSearch indexes logs with proper mapping
- ✅ Logs are searchable and contain required fields
- ✅ Data Prepper metrics are available

## Detailed Usage

### Integration Test Scripts

#### `test_integration.py` (Python - Recommended)

**Features:**

- Comprehensive service health checks
- Realistic test log generation with multiple severity levels
- Advanced OpenSearch verification
- Data Prepper metrics validation
- Colored output and detailed reporting
- Cleanup functionality

**Usage:**

```bash
# Basic test run
./test_integration.py

# Options
./test_integration.py --cleanup          # Clean up test data after tests
./test_integration.py --num-logs 20      # Generate 20 test logs
```

**Sample Output:**

```
[INFO] Starting OpenSearch Data Prepper Pipeline Integration Tests
======================================================================
[INFO] Step 1: Checking services...
[SUCCESS] OTEL Collector is ready
[SUCCESS] Data Prepper is ready
[SUCCESS] OpenSearch is ready
[SUCCESS] All services are running
[INFO] Step 2: Verifying index template...
[SUCCESS] Log indices exist
[INFO] Step 3: Sending test logs...
[SUCCESS] Test logs sent successfully to OTEL Collector
...
[SUCCESS] All integration tests completed successfully!
```

#### `test-integration.sh` (Bash)

**Features:**

- Service connectivity checks
- OTLP log generation and sending
- OpenSearch log verification
- Basic metrics checking
- Cross-platform compatibility

**Usage:**

```bash
./test-integration.sh [--cleanup] [--help]
```

### Test Data Generation

#### `generate_test_logs.py`

Generate realistic test log data in various formats.

**Usage:**

```bash
# Generate OTLP format logs (default)
./generate_test_logs.py --num-logs 5

# Generate structured logs
./generate_test_logs.py --format structured --num-logs 10

# Save to file with pretty formatting
./generate_test_logs.py --num-logs 5 --pretty --output test_logs.json

# Custom service information
./generate_test_logs.py --service-name "my-app" --service-version "2.1.0"
```

**Generated Log Types:**

- INFO: User authentication events
- ERROR: Database connection failures
- DEBUG: Request processing logs
- FATAL: Critical system failures
- WARN: Performance warnings
- INFO: Business transaction logs

### OpenSearch Verification

#### `verify_opensearch_logs.py`

Comprehensive OpenSearch log verification and analysis tool.

**Usage:**

**Check OpenSearch status:**

```bash
./verify_opensearch_logs.py status
```

**Search logs by service:**

```bash
./verify_opensearch_logs.py search-service integration-test-service --limit 20
```

**Search logs by severity:**

```bash
./verify_opensearch_logs.py search-severity ERROR --limit 10
```

**Search logs by trace ID:**

```bash
./verify_opensearch_logs.py search-trace abc123def456...
```

**Get log statistics:**

```bash
./verify_opensearch_logs.py stats
```

**Verify required fields:**

```bash
./verify_opensearch_logs.py verify-fields --fields @timestamp service_name message severity_text
```

**Clean up test data:**

```bash
./verify_opensearch_logs.py delete-service integration-test-service --confirm
```

## Test Scenarios Covered

### 1. Service Health Verification

- OTEL Collector HTTP endpoint accessibility
- Data Prepper health check endpoint
- OpenSearch cluster connectivity
- Service startup dependencies

### 2. Log Pipeline Flow

- OTLP log ingestion via OTEL Collector
- Data Prepper log processing and transformation
- OpenSearch indexing with proper mapping
- Field transformation verification

### 3. Data Transformation Verification

- Service name and version extraction
- Severity level mapping
- Timestamp parsing and formatting
- Attribute flattening and renaming
- Message field processing

### 4. OpenSearch Integration

- Index template application
- Document indexing and searchability
- Field mapping verification
- Query performance

### 5. Monitoring and Metrics

- Data Prepper Prometheus metrics
- Processing throughput verification
- Error rate monitoring
- Health check endpoints

## Troubleshooting

### Common Issues

**1. Services not ready:**

```
[ERROR] OTEL Collector failed to become ready after 30 attempts
```

**Solution:** Check if services are running with `docker-compose ps` and ensure ports are not blocked.

**2. No logs found in OpenSearch:**

```
[ERROR] Expected at least 2 logs, but found 0
```

**Solutions:**

- Wait longer for log processing (increase wait time)
- Check Data Prepper logs: `docker-compose logs data-prepper`
- Verify OTEL Collector configuration
- Check OpenSearch indices: `curl http://localhost:9200/_cat/indices/logs-*`

**3. Field transformation issues:**

```
[ERROR] Missing required fields: ['service_name', 'severity_text']
```

**Solutions:**

- Check Data Prepper pipeline configuration in `data-prepper.yaml`
- Verify processor chain is working correctly
- Review OpenSearch index mapping

**4. Python dependencies missing:**

```
ModuleNotFoundError: No module named 'requests'
```

**Solution:** Install required dependencies:

```bash
pip install requests
```

### Debug Commands

**Check service logs:**

```bash
docker-compose logs otel-collector
docker-compose logs data-prepper
docker-compose logs opensearch
```

**Manual log sending:**

```bash
# Generate test data
./generate_test_logs.py --pretty --output test.json

# Send to OTEL Collector
curl -X POST http://localhost:4318/v1/logs \
  -H "Content-Type: application/json" \
  -d @test.json
```

**Check OpenSearch directly:**

```bash
# List indices
curl http://localhost:9200/_cat/indices/logs-*

# Search all logs
curl -X GET "http://localhost:9200/logs-*/_search?size=5&pretty"

# Check index mapping
curl -X GET "http://localhost:9200/logs-*/_mapping?pretty"
```

**Check Data Prepper metrics:**

```bash
curl http://localhost:4900/health
curl http://localhost:9600/metrics
```

## Test Data Cleanup

**Automatic cleanup:**

```bash
./test_integration.py --cleanup
./test-integration.sh --cleanup
```

**Manual cleanup:**

```bash
# Delete specific service logs
./verify_opensearch_logs.py delete-service integration-test-service --confirm

# Delete all log indices (careful!)
curl -X DELETE "http://localhost:9200/logs-*"
```

## Performance Testing

For performance testing, you can generate larger volumes of test data:

```bash
# Generate and send 100 logs
./test_integration.py --num-logs 100

# Generate test data file for repeated testing
./generate_test_logs.py --num-logs 1000 --output large_test_set.json
```

## Integration with CI/CD

The test scripts return appropriate exit codes for CI/CD integration:

```bash
# In CI pipeline
./test_integration.py --cleanup
if [ $? -eq 0 ]; then
    echo "Integration tests passed"
else
    echo "Integration tests failed"
    exit 1
fi
```

## Requirements Verification

This testing suite verifies the following requirements from the specification:

- **Requirement 1.1**: OTEL Collector sends logs to Data Prepper ✅
- **Requirement 1.2**: Data Prepper processes and transforms logs ✅  
- **Requirement 1.3**: Transformed logs are sent to OpenSearch ✅
- **Requirement 2.1-2.3**: Data Prepper service runs in docker-compose ✅
- **Requirement 3.1-3.3**: Pipeline configuration and customization ✅
- **Requirement 4.1-4.3**: Monitoring and metrics availability ✅
- **Requirement 5.1-5.2**: Dual pipeline support (Loki + Data Prepper) ✅

## Next Steps

After successful integration testing:

1. **Monitor in production**: Set up alerts based on Data Prepper metrics
2. **Optimize performance**: Adjust batch sizes and processing parameters
3. **Extend pipeline**: Add additional processors or sinks as needed
4. **Create dashboards**: Build Grafana dashboards for log analytics
5. **Set up alerting**: Configure alerts for pipeline failures or performance issues
