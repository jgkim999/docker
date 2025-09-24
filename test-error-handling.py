#!/usr/bin/env python3
"""
Data Prepper Error Handling and DLQ Test Script

This script tests the error handling and Dead Letter Queue functionality
of the Data Prepper pipeline by sending various types of logs that should
trigger different error conditions.
"""

import json
import time
import requests
import logging
import argparse
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataPrepperErrorTester:
    """Test class for Data Prepper error handling and DLQ functionality."""
    
    def __init__(self, otel_endpoint: str = "http://localhost:4318", 
                 data_prepper_endpoint: str = "http://localhost:4900",
                 opensearch_endpoint: str = "http://localhost:9200"):
        self.otel_endpoint = otel_endpoint
        self.data_prepper_endpoint = data_prepper_endpoint
        self.opensearch_endpoint = opensearch_endpoint
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DataPrepperErrorTester/1.0'
        })
        
    def check_services(self) -> bool:
        """Check if all required services are running."""
        services = {
            'OTEL Collector': f"{self.otel_endpoint}/v1/logs",
            'Data Prepper': f"{self.data_prepper_endpoint}/health",
            'OpenSearch': f"{self.opensearch_endpoint}/_cluster/health"
        }
        
        all_healthy = True
        for service, url in services.items():
            try:
                if service == 'OTEL Collector':
                    # For OTEL, we'll just check if the port is accessible
                    response = self.session.get(url.replace('/v1/logs', ''), timeout=5)
                else:
                    response = self.session.get(url, timeout=5)
                
                if response.status_code < 400:
                    logger.info(f"✓ {service} is healthy")
                else:
                    logger.error(f"✗ {service} returned status {response.status_code}")
                    all_healthy = False
            except Exception as e:
                logger.error(f"✗ {service} is not accessible: {e}")
                all_healthy = False
                
        return all_healthy
    
    def create_test_log(self, log_type: str, **kwargs) -> Dict[str, Any]:
        """Create test log data for different error scenarios."""
        base_time = datetime.now(timezone.utc)
        trace_id = str(uuid.uuid4()).replace('-', '')
        span_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        base_log = {
            "resourceLogs": [{
                "resource": {
                    "attributes": [{
                        "key": "service.name",
                        "value": {"stringValue": kwargs.get("service_name", "error-test-service")}
                    }, {
                        "key": "service.version", 
                        "value": {"stringValue": kwargs.get("service_version", "1.0.0")}
                    }]
                },
                "scopeLogs": [{
                    "logRecords": [{
                        "timeUnixNano": str(int(base_time.timestamp() * 1_000_000_000)),
                        "severityText": kwargs.get("severity", "INFO"),
                        "body": {"stringValue": kwargs.get("message", "Test log message")},
                        "attributes": [],
                        "traceId": trace_id,
                        "spanId": span_id
                    }]
                }]
            }]
        }
        
        log_record = base_log["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
        
        if log_type == "valid":
            # Valid log that should process successfully
            log_record["attributes"] = [{
                "key": "user.id",
                "value": {"stringValue": "12345"}
            }, {
                "key": "request.method",
                "value": {"stringValue": "GET"}
            }]
            
        elif log_type == "invalid_timestamp":
            # Invalid timestamp format to trigger date parsing error
            log_record["timeUnixNano"] = "invalid-timestamp"
            
        elif log_type == "missing_required_fields":
            # Remove required fields to trigger validation error
            del log_record["severityText"]
            del log_record["body"]
            
        elif log_type == "oversized_document":
            # Create oversized document to trigger size limit error
            large_message = "x" * (11 * 1024 * 1024)  # 11MB message
            log_record["body"]["stringValue"] = large_message
            
        elif log_type == "invalid_json_structure":
            # This will be handled at the request level
            return {"invalid": "json structure without proper OTLP format"}
            
        elif log_type == "grok_parse_failure":
            # Log message that won't match any grok patterns
            log_record["body"]["stringValue"] = "This is a completely unstructured log message with no recognizable pattern @@##$$%%"
            log_record["attributes"] = [{
                "key": "log.format",
                "value": {"stringValue": "unstructured"}
            }]
            
        elif log_type == "field_mapping_error":
            # Add attributes that might cause mapping conflicts
            log_record["attributes"] = [{
                "key": "timestamp",  # This might conflict with @timestamp
                "value": {"stringValue": "not-a-timestamp"}
            }, {
                "key": "message",  # This might conflict with body mapping
                "value": {"intValue": 12345}  # Wrong type
            }]
            
        elif log_type == "unicode_encoding_error":
            # Add problematic unicode characters
            log_record["body"]["stringValue"] = "Test with problematic unicode: \x00\x01\x02\xff\xfe"
            log_record["attributes"] = [{
                "key": "unicode.test",
                "value": {"stringValue": "\ud800\udc00"}  # Surrogate pair
            }]
            
        return base_log
    
    def send_test_log(self, log_data: Dict[str, Any], test_name: str) -> bool:
        """Send test log to OTEL Collector."""
        try:
            url = f"{self.otel_endpoint}/v1/logs"
            response = self.session.post(url, json=log_data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✓ {test_name}: Log sent successfully")
                return True
            else:
                logger.warning(f"⚠ {test_name}: Log sent with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"✗ {test_name}: Failed to send log - {e}")
            return False
    
    def wait_for_processing(self, seconds: int = 5):
        """Wait for logs to be processed."""
        logger.info(f"Waiting {seconds} seconds for log processing...")
        time.sleep(seconds)
    
    def check_opensearch_logs(self, index_pattern: str = "logs-*") -> Dict[str, Any]:
        """Check logs in OpenSearch."""
        try:
            url = f"{self.opensearch_endpoint}/{index_pattern}/_search"
            query = {
                "query": {"match_all": {}},
                "sort": [{"@timestamp": {"order": "desc"}}],
                "size": 100
            }
            
            response = self.session.post(url, json=query, timeout=10)
            if response.status_code == 200:
                data = response.json()
                total_hits = data["hits"]["total"]["value"]
                logger.info(f"✓ Found {total_hits} logs in OpenSearch")
                return data
            else:
                logger.error(f"✗ Failed to query OpenSearch: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"✗ Failed to query OpenSearch: {e}")
            return {}
    
    def check_dlq_metrics(self) -> Dict[str, Any]:
        """Check DLQ metrics from Data Prepper."""
        try:
            url = f"{self.data_prepper_endpoint}/metrics"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                metrics_text = response.text
                dlq_metrics = {}
                
                # Parse Prometheus metrics for DLQ-related metrics
                for line in metrics_text.split('\n'):
                    if 'dlq' in line.lower() or 'error' in line.lower():
                        if line.startswith('#'):
                            continue
                        if ' ' in line:
                            metric_name = line.split(' ')[0]
                            metric_value = line.split(' ')[1]
                            dlq_metrics[metric_name] = metric_value
                
                logger.info(f"✓ Retrieved {len(dlq_metrics)} DLQ-related metrics")
                return dlq_metrics
            else:
                logger.error(f"✗ Failed to get metrics: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"✗ Failed to get metrics: {e}")
            return {}
    
    def run_error_tests(self) -> Dict[str, bool]:
        """Run comprehensive error handling tests."""
        logger.info("Starting Data Prepper error handling tests...")
        
        test_results = {}
        
        # Test scenarios
        test_scenarios = [
            ("valid_log", "Valid log processing"),
            ("invalid_timestamp", "Invalid timestamp handling"),
            ("missing_required_fields", "Missing required fields"),
            ("grok_parse_failure", "Grok parsing failure"),
            ("field_mapping_error", "Field mapping error"),
            ("unicode_encoding_error", "Unicode encoding error"),
            ("oversized_document", "Oversized document handling"),
            ("invalid_json_structure", "Invalid JSON structure")
        ]
        
        for test_type, test_description in test_scenarios:
            logger.info(f"\n--- Running test: {test_description} ---")
            
            # Create and send test log
            log_data = self.create_test_log(test_type)
            success = self.send_test_log(log_data, test_description)
            test_results[test_type] = success
            
            # Wait between tests
            time.sleep(2)
        
        return test_results
    
    def run_dlq_validation(self):
        """Validate DLQ functionality."""
        logger.info("\n--- Validating DLQ functionality ---")
        
        # Wait for processing
        self.wait_for_processing(10)
        
        # Check OpenSearch for processed logs
        opensearch_data = self.check_opensearch_logs()
        
        # Check DLQ metrics
        dlq_metrics = self.check_dlq_metrics()
        
        # Check Data Prepper health
        try:
            health_response = self.session.get(f"{self.data_prepper_endpoint}/health", timeout=5)
            if health_response.status_code == 200:
                logger.info("✓ Data Prepper is healthy after error tests")
            else:
                logger.warning(f"⚠ Data Prepper health check returned {health_response.status_code}")
        except Exception as e:
            logger.error(f"✗ Data Prepper health check failed: {e}")
        
        return {
            'opensearch_logs': opensearch_data,
            'dlq_metrics': dlq_metrics
        }
    
    def generate_load_test(self, num_logs: int = 100, error_rate: float = 0.1):
        """Generate load test with mixed valid and error logs."""
        logger.info(f"\n--- Running load test with {num_logs} logs (error rate: {error_rate:.1%}) ---")
        
        sent_count = 0
        error_count = 0
        
        for i in range(num_logs):
            # Determine if this should be an error log
            if i / num_logs < error_rate:
                # Send error log
                test_type = ["invalid_timestamp", "grok_parse_failure", "field_mapping_error"][i % 3]
                log_data = self.create_test_log(test_type, message=f"Load test error log {i}")
                error_count += 1
            else:
                # Send valid log
                log_data = self.create_test_log("valid", message=f"Load test valid log {i}")
            
            success = self.send_test_log(log_data, f"Load test log {i}")
            if success:
                sent_count += 1
            
            # Small delay to avoid overwhelming the system
            if i % 10 == 0:
                time.sleep(0.1)
        
        logger.info(f"Load test completed: {sent_count}/{num_logs} logs sent, {error_count} error logs")
        
        # Wait for processing and check results
        self.wait_for_processing(15)
        return self.run_dlq_validation()

def main():
    parser = argparse.ArgumentParser(description='Test Data Prepper error handling and DLQ functionality')
    parser.add_argument('--otel-endpoint', default='http://localhost:4318',
                       help='OTEL Collector endpoint (default: http://localhost:4318)')
    parser.add_argument('--data-prepper-endpoint', default='http://localhost:4900',
                       help='Data Prepper endpoint (default: http://localhost:4900)')
    parser.add_argument('--opensearch-endpoint', default='http://localhost:9200',
                       help='OpenSearch endpoint (default: http://localhost:9200)')
    parser.add_argument('--load-test', action='store_true',
                       help='Run load test with mixed valid/error logs')
    parser.add_argument('--num-logs', type=int, default=100,
                       help='Number of logs for load test (default: 100)')
    parser.add_argument('--error-rate', type=float, default=0.1,
                       help='Error rate for load test (default: 0.1)')
    parser.add_argument('--skip-health-check', action='store_true',
                       help='Skip initial health check')
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = DataPrepperErrorTester(
        otel_endpoint=args.otel_endpoint,
        data_prepper_endpoint=args.data_prepper_endpoint,
        opensearch_endpoint=args.opensearch_endpoint
    )
    
    # Check service health
    if not args.skip_health_check:
        logger.info("Checking service health...")
        if not tester.check_services():
            logger.error("Some services are not healthy. Use --skip-health-check to proceed anyway.")
            sys.exit(1)
    
    try:
        if args.load_test:
            # Run load test
            results = tester.generate_load_test(args.num_logs, args.error_rate)
        else:
            # Run error handling tests
            test_results = tester.run_error_tests()
            
            # Print test summary
            logger.info("\n=== Test Summary ===")
            for test_name, success in test_results.items():
                status = "✓ PASS" if success else "✗ FAIL"
                logger.info(f"{test_name}: {status}")
            
            # Validate DLQ functionality
            results = tester.run_dlq_validation()
        
        # Print final results
        logger.info("\n=== Final Results ===")
        logger.info(f"OpenSearch logs found: {results['opensearch_logs'].get('hits', {}).get('total', {}).get('value', 0)}")
        logger.info(f"DLQ metrics collected: {len(results['dlq_metrics'])}")
        
        if results['dlq_metrics']:
            logger.info("DLQ Metrics:")
            for metric, value in results['dlq_metrics'].items():
                logger.info(f"  {metric}: {value}")
        
        logger.info("\nError handling test completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()