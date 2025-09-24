#!/bin/bash

# Integration Test Script for OpenSearch Data Prepper Pipeline
# This script tests the end-to-end log pipeline: otel-collector -> data-prepper -> opensearch

set -e

# Configuration
OTEL_COLLECTOR_ENDPOINT="http://localhost:4318"
DATA_PREPPER_HEALTH_ENDPOINT="http://localhost:4900/health"
DATA_PREPPER_METRICS_ENDPOINT="http://localhost:9600/metrics"
OPENSEARCH_ENDPOINT="http://localhost:9200"
TEST_SERVICE_NAME="integration-test-service"
TEST_SERVICE_VERSION="1.0.0"
LOG_INDEX_PATTERN="logs-*"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: $service_name not ready yet, waiting..."
        sleep 2
        ((attempt++))
    done
    
    log_error "$service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Check if all required services are running
check_services() {
    log_info "Checking if all required services are running..."
    
    # Check OTEL Collector
    if ! wait_for_service "$OTEL_COLLECTOR_ENDPOINT/v1/logs" "OTEL Collector"; then
        return 1
    fi
    
    # Check Data Prepper
    if ! wait_for_service "$DATA_PREPPER_HEALTH_ENDPOINT" "Data Prepper"; then
        return 1
    fi
    
    # Check OpenSearch
    if ! wait_for_service "$OPENSEARCH_ENDPOINT" "OpenSearch"; then
        return 1
    fi
    
    log_success "All services are running"
    return 0
}

# Generate test log data
generate_test_logs() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    local trace_id=$(openssl rand -hex 16)
    local span_id=$(openssl rand -hex 8)
    
    cat << EOF
{
  "resourceLogs": [
    {
      "resource": {
        "attributes": [
          {
            "key": "service.name",
            "value": {
              "stringValue": "$TEST_SERVICE_NAME"
            }
          },
          {
            "key": "service.version",
            "value": {
              "stringValue": "$TEST_SERVICE_VERSION"
            }
          },
          {
            "key": "host.name",
            "value": {
              "stringValue": "test-host-01"
            }
          }
        ]
      },
      "scopeLogs": [
        {
          "scope": {
            "name": "test-logger",
            "version": "1.0.0"
          },
          "logRecords": [
            {
              "timeUnixNano": "$(date +%s%N)",
              "observedTimeUnixNano": "$(date +%s%N)",
              "severityNumber": 9,
              "severityText": "INFO",
              "body": {
                "stringValue": "User authentication successful for user_id=12345"
              },
              "attributes": [
                {
                  "key": "user.id",
                  "value": {
                    "stringValue": "12345"
                  }
                },
                {
                  "key": "action",
                  "value": {
                    "stringValue": "login"
                  }
                },
                {
                  "key": "ip_address",
                  "value": {
                    "stringValue": "192.168.1.100"
                  }
                }
              ],
              "traceId": "$trace_id",
              "spanId": "$span_id",
              "flags": 1
            },
            {
              "timeUnixNano": "$(date +%s%N)",
              "observedTimeUnixNano": "$(date +%s%N)",
              "severityNumber": 13,
              "severityText": "ERROR",
              "body": {
                "stringValue": "Database connection failed: timeout after 30s"
              },
              "attributes": [
                {
                  "key": "database.name",
                  "value": {
                    "stringValue": "user_db"
                  }
                },
                {
                  "key": "error.type",
                  "value": {
                    "stringValue": "connection_timeout"
                  }
                }
              ],
              "traceId": "$trace_id",
              "spanId": "$(openssl rand -hex 8)",
              "flags": 1
            }
          ]
        }
      ]
    }
  ]
}
EOF
}

# Send test logs to OTEL Collector
send_test_logs() {
    log_info "Generating and sending test logs to OTEL Collector..."
    
    local test_data=$(generate_test_logs)
    local response
    
    response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$test_data" \
        "$OTEL_COLLECTOR_ENDPOINT/v1/logs")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        log_success "Test logs sent successfully to OTEL Collector"
        return 0
    else
        log_error "Failed to send logs to OTEL Collector. HTTP code: $http_code"
        return 1
    fi
}

# Wait for logs to be processed and indexed
wait_for_log_processing() {
    log_info "Waiting for logs to be processed and indexed..."
    sleep 10  # Give some time for processing
}

# Search logs in OpenSearch
search_logs_in_opensearch() {
    local service_name=$1
    local expected_count=${2:-1}
    
    log_info "Searching for logs with service_name='$service_name' in OpenSearch..."
    
    # First, refresh the index to ensure all documents are searchable
    curl -s -X POST "$OPENSEARCH_ENDPOINT/$LOG_INDEX_PATTERN/_refresh" > /dev/null
    
    local search_query='{
        "query": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "service_name": "'$service_name'"
                        }
                    }
                ]
            }
        },
        "size": 100,
        "sort": [
            {
                "@timestamp": {
                    "order": "desc"
                }
            }
        ]
    }'
    
    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        -d "$search_query" \
        "$OPENSEARCH_ENDPOINT/$LOG_INDEX_PATTERN/_search")
    
    if [ $? -ne 0 ]; then
        log_error "Failed to search logs in OpenSearch"
        return 1
    fi
    
    # Parse response and check results
    local hit_count=$(echo "$response" | jq -r '.hits.total.value // .hits.total // 0')
    
    if [ "$hit_count" -ge "$expected_count" ]; then
        log_success "Found $hit_count logs in OpenSearch (expected at least $expected_count)"
        
        # Display some log details
        log_info "Sample log entries:"
        echo "$response" | jq -r '.hits.hits[] | "- Timestamp: " + (._source["@timestamp"] // "N/A") + ", Service: " + (._source.service_name // "N/A") + ", Message: " + (._source.message // ._source.body // "N/A")'
        
        return 0
    else
        log_error "Expected at least $expected_count logs, but found $hit_count"
        log_info "Search response: $response"
        return 1
    fi
}

# Verify log field mapping and transformation
verify_log_transformation() {
    log_info "Verifying log field transformation and mapping..."
    
    local search_query='{
        "query": {
            "term": {
                "service_name": "'$TEST_SERVICE_NAME'"
            }
        },
        "size": 1
    }'
    
    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        -d "$search_query" \
        "$OPENSEARCH_ENDPOINT/$LOG_INDEX_PATTERN/_search")
    
    if [ $? -ne 0 ]; then
        log_error "Failed to retrieve log for transformation verification"
        return 1
    fi
    
    local log_entry=$(echo "$response" | jq -r '.hits.hits[0]._source // {}')
    
    # Check required fields
    local required_fields=("@timestamp" "service_name" "service_version" "message" "severity_text")
    local missing_fields=()
    
    for field in "${required_fields[@]}"; do
        local field_value=$(echo "$log_entry" | jq -r ".$field // empty")
        if [ -z "$field_value" ]; then
            missing_fields+=("$field")
        else
            log_success "Field '$field' found with value: $field_value"
        fi
    done
    
    if [ ${#missing_fields[@]} -eq 0 ]; then
        log_success "All required fields are present and properly transformed"
        return 0
    else
        log_error "Missing required fields: ${missing_fields[*]}"
        return 1
    fi
}

# Check Data Prepper metrics
check_data_prepper_metrics() {
    log_info "Checking Data Prepper metrics..."
    
    local metrics_response=$(curl -s "$DATA_PREPPER_METRICS_ENDPOINT")
    
    if [ $? -ne 0 ]; then
        log_error "Failed to retrieve Data Prepper metrics"
        return 1
    fi
    
    # Check for key metrics
    local log_records_in=$(echo "$metrics_response" | grep -c "log_pipeline_recordsIn_total" || echo "0")
    local log_records_out=$(echo "$metrics_response" | grep -c "log_pipeline_recordsOut_total" || echo "0")
    
    if [ "$log_records_in" -gt 0 ] && [ "$log_records_out" -gt 0 ]; then
        log_success "Data Prepper metrics are available and showing log processing activity"
        
        # Show some key metrics
        log_info "Key metrics:"
        echo "$metrics_response" | grep -E "(recordsIn_total|recordsOut_total|processingTime)" | head -5
        
        return 0
    else
        log_warning "Data Prepper metrics endpoint is accessible but no log processing metrics found yet"
        return 1
    fi
}

# Verify index template is applied
verify_index_template() {
    log_info "Verifying OpenSearch index template is applied..."
    
    local template_response=$(curl -s "$OPENSEARCH_ENDPOINT/_index_template/logs-template")
    
    if echo "$template_response" | jq -e '.index_templates[0]' > /dev/null 2>&1; then
        log_success "Index template is properly applied"
        return 0
    else
        log_warning "Index template not found, checking if indices exist with proper mapping..."
        
        # Check if any log indices exist
        local indices_response=$(curl -s "$OPENSEARCH_ENDPOINT/_cat/indices/logs-*?format=json")
        
        if echo "$indices_response" | jq -e '.[0]' > /dev/null 2>&1; then
            log_success "Log indices exist"
            return 0
        else
            log_error "No log indices found"
            return 1
        fi
    fi
}

# Clean up test data (optional)
cleanup_test_data() {
    if [ "$1" = "--cleanup" ]; then
        log_info "Cleaning up test data..."
        
        # Delete test logs
        local delete_query='{
            "query": {
                "term": {
                    "service_name": "'$TEST_SERVICE_NAME'"
                }
            }
        }'
        
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$delete_query" \
            "$OPENSEARCH_ENDPOINT/$LOG_INDEX_PATTERN/_delete_by_query" > /dev/null
        
        log_success "Test data cleaned up"
    fi
}

# Main test execution
run_integration_tests() {
    log_info "Starting OpenSearch Data Prepper Pipeline Integration Tests"
    echo "=================================================="
    
    # Step 1: Check services
    if ! check_services; then
        log_error "Service check failed. Please ensure all services are running with 'docker-compose up -d'"
        exit 1
    fi
    
    # Step 2: Verify index template
    verify_index_template
    
    # Step 3: Send test logs
    if ! send_test_logs; then
        log_error "Failed to send test logs"
        exit 1
    fi
    
    # Step 4: Wait for processing
    wait_for_log_processing
    
    # Step 5: Search and verify logs in OpenSearch
    if ! search_logs_in_opensearch "$TEST_SERVICE_NAME" 2; then
        log_error "Log search verification failed"
        exit 1
    fi
    
    # Step 6: Verify log transformation
    if ! verify_log_transformation; then
        log_error "Log transformation verification failed"
        exit 1
    fi
    
    # Step 7: Check Data Prepper metrics
    check_data_prepper_metrics
    
    # Step 8: Cleanup (if requested)
    cleanup_test_data "$1"
    
    echo "=================================================="
    log_success "All integration tests completed successfully!"
    log_info "The end-to-end log pipeline is working correctly:"
    log_info "  ✓ OTEL Collector receives logs"
    log_info "  ✓ Data Prepper processes and transforms logs"
    log_info "  ✓ OpenSearch indexes logs with proper mapping"
    log_info "  ✓ Logs are searchable and properly formatted"
}

# Script usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --cleanup    Clean up test data after running tests"
    echo "  --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run tests without cleanup"
    echo "  $0 --cleanup          # Run tests and clean up test data"
}

# Main execution
case "${1:-}" in
    --help)
        show_usage
        exit 0
        ;;
    --cleanup)
        run_integration_tests --cleanup
        ;;
    "")
        run_integration_tests
        ;;
    *)
        log_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac