#!/usr/bin/env python3
"""
Integration Test Script for OpenSearch Data Prepper Pipeline
This script tests the end-to-end log pipeline: otel-collector -> data-prepper -> opensearch
"""

import json
import time
import requests
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import uuid
import random

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class Logger:
    """Simple logger with colored output"""
    
    @staticmethod
    def info(message: str):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")
    
    @staticmethod
    def success(message: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")
    
    @staticmethod
    def warning(message: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")
    
    @staticmethod
    def error(message: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

class DataPrepperIntegrationTest:
    """Integration test suite for Data Prepper pipeline"""
    
    def __init__(self):
        self.otel_collector_endpoint = "http://localhost:4318"
        self.data_prepper_health_endpoint = "http://localhost:4900/health"
        self.data_prepper_metrics_endpoint = "http://localhost:9600/metrics"
        self.opensearch_endpoint = "http://localhost:9200"
        self.test_service_name = "integration-test-service"
        self.test_service_version = "1.0.0"
        self.log_index_pattern = "logs-*"
        self.test_trace_id = None
        
    def wait_for_service(self, url: str, service_name: str, max_attempts: int = 30) -> bool:
        """Wait for a service to become ready"""
        Logger.info(f"Waiting for {service_name} to be ready...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    Logger.success(f"{service_name} is ready")
                    return True
            except requests.RequestException:
                pass
            
            Logger.info(f"Attempt {attempt}/{max_attempts}: {service_name} not ready yet, waiting...")
            time.sleep(2)
        
        Logger.error(f"{service_name} failed to become ready after {max_attempts} attempts")
        return False
    
    def check_services(self) -> bool:
        """Check if all required services are running"""
        Logger.info("Checking if all required services are running...")
        
        services = [
            (f"{self.otel_collector_endpoint}/v1/logs", "OTEL Collector"),
            (self.data_prepper_health_endpoint, "Data Prepper"),
            (self.opensearch_endpoint, "OpenSearch")
        ]
        
        for url, name in services:
            if not self.wait_for_service(url, name):
                return False
        
        Logger.success("All services are running")
        return True
    
    def generate_test_logs(self, num_logs: int = 2) -> Dict:
        """Generate test log data in OTLP format"""
        self.test_trace_id = uuid.uuid4().hex
        current_time_ns = int(time.time() * 1_000_000_000)
        
        log_records = []
        
        # Generate different types of log entries
        log_templates = [
            {
                "severity": (9, "INFO"),
                "message": f"User authentication successful for user_id={random.randint(10000, 99999)}",
                "attributes": {
                    "user.id": str(random.randint(10000, 99999)),
                    "action": "login",
                    "ip_address": f"192.168.1.{random.randint(1, 254)}"
                }
            },
            {
                "severity": (13, "ERROR"),
                "message": "Database connection failed: timeout after 30s",
                "attributes": {
                    "database.name": "user_db",
                    "error.type": "connection_timeout",
                    "retry_count": str(random.randint(1, 5))
                }
            },
            {
                "severity": (5, "DEBUG"),
                "message": f"Processing request with correlation_id={uuid.uuid4().hex[:8]}",
                "attributes": {
                    "correlation_id": uuid.uuid4().hex[:8],
                    "request.method": "POST",
                    "request.path": "/api/v1/users"
                }
            },
            {
                "severity": (17, "FATAL"),
                "message": "Critical system failure: out of memory",
                "attributes": {
                    "memory.used": "95%",
                    "system.component": "application_server"
                }
            }
        ]
        
        for i in range(num_logs):
            template = log_templates[i % len(log_templates)]
            
            # Convert attributes to OTLP format
            otlp_attributes = []
            for key, value in template["attributes"].items():
                otlp_attributes.append({
                    "key": key,
                    "value": {"stringValue": value}
                })
            
            log_record = {
                "timeUnixNano": str(current_time_ns + i * 1000000),  # Add microsecond offset
                "observedTimeUnixNano": str(current_time_ns + i * 1000000),
                "severityNumber": template["severity"][0],
                "severityText": template["severity"][1],
                "body": {"stringValue": template["message"]},
                "attributes": otlp_attributes,
                "traceId": self.test_trace_id,
                "spanId": uuid.uuid4().hex[:16],
                "flags": 1
            }
            
            log_records.append(log_record)
        
        return {
            "resourceLogs": [{
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": self.test_service_name}
                        },
                        {
                            "key": "service.version",
                            "value": {"stringValue": self.test_service_version}
                        },
                        {
                            "key": "host.name",
                            "value": {"stringValue": "test-host-01"}
                        },
                        {
                            "key": "container.name",
                            "value": {"stringValue": "integration-test-container"}
                        }
                    ]
                },
                "scopeLogs": [{
                    "scope": {
                        "name": "test-logger",
                        "version": "1.0.0"
                    },
                    "logRecords": log_records
                }]
            }]
        }
    
    def send_test_logs(self, num_logs: int = 2) -> bool:
        """Send test logs to OTEL Collector"""
        Logger.info(f"Generating and sending {num_logs} test logs to OTEL Collector...")
        
        test_data = self.generate_test_logs(num_logs)
        
        try:
            response = requests.post(
                f"{self.otel_collector_endpoint}/v1/logs",
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                Logger.success("Test logs sent successfully to OTEL Collector")
                return True
            else:
                Logger.error(f"Failed to send logs to OTEL Collector. HTTP code: {response.status_code}")
                Logger.error(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            Logger.error(f"Failed to send logs to OTEL Collector: {e}")
            return False
    
    def wait_for_log_processing(self, wait_time: int = 15):
        """Wait for logs to be processed and indexed"""
        Logger.info(f"Waiting {wait_time} seconds for logs to be processed and indexed...")
        time.sleep(wait_time)
    
    def refresh_opensearch_indices(self) -> bool:
        """Refresh OpenSearch indices to make documents searchable"""
        try:
            response = requests.post(f"{self.opensearch_endpoint}/{self.log_index_pattern}/_refresh")
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def search_logs_in_opensearch(self, service_name: str, expected_count: int = 1) -> Tuple[bool, Dict]:
        """Search for logs in OpenSearch"""
        Logger.info(f"Searching for logs with service_name='{service_name}' in OpenSearch...")
        
        # Refresh indices first
        self.refresh_opensearch_indices()
        
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service_name": service_name}}
                    ]
                }
            },
            "size": 100,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        try:
            response = requests.get(
                f"{self.opensearch_endpoint}/{self.log_index_pattern}/_search",
                json=search_query,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code != 200:
                Logger.error(f"Failed to search logs in OpenSearch. HTTP code: {response.status_code}")
                return False, {}
            
            result = response.json()
            hit_count = result.get("hits", {}).get("total", {})
            
            # Handle different OpenSearch versions
            if isinstance(hit_count, dict):
                hit_count = hit_count.get("value", 0)
            
            if hit_count >= expected_count:
                Logger.success(f"Found {hit_count} logs in OpenSearch (expected at least {expected_count})")
                
                # Display sample log entries
                Logger.info("Sample log entries:")
                for hit in result.get("hits", {}).get("hits", [])[:3]:
                    source = hit.get("_source", {})
                    timestamp = source.get("@timestamp", "N/A")
                    service = source.get("service_name", "N/A")
                    message = source.get("message", source.get("body", "N/A"))
                    severity = source.get("severity_text", "N/A")
                    print(f"  - [{timestamp}] {severity}: {service} - {message}")
                
                return True, result
            else:
                Logger.error(f"Expected at least {expected_count} logs, but found {hit_count}")
                return False, result
                
        except requests.RequestException as e:
            Logger.error(f"Failed to search logs in OpenSearch: {e}")
            return False, {}
    
    def verify_log_transformation(self) -> bool:
        """Verify log field transformation and mapping"""
        Logger.info("Verifying log field transformation and mapping...")
        
        search_query = {
            "query": {"term": {"service_name": self.test_service_name}},
            "size": 1
        }
        
        try:
            response = requests.get(
                f"{self.opensearch_endpoint}/{self.log_index_pattern}/_search",
                json=search_query,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                Logger.error("Failed to retrieve log for transformation verification")
                return False
            
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])
            
            if not hits:
                Logger.error("No logs found for transformation verification")
                return False
            
            log_entry = hits[0].get("_source", {})
            
            # Check required fields
            required_fields = ["@timestamp", "service_name", "service_version", "message", "severity_text"]
            missing_fields = []
            
            for field in required_fields:
                if field not in log_entry or not log_entry[field]:
                    missing_fields.append(field)
                else:
                    Logger.success(f"Field '{field}' found with value: {log_entry[field]}")
            
            # Check for Data Prepper specific transformations
            if "pipeline_processed" in log_entry:
                Logger.success("Data Prepper processing flag found")
            
            if "processed_at" in log_entry:
                Logger.success("Data Prepper processing timestamp found")
            
            if not missing_fields:
                Logger.success("All required fields are present and properly transformed")
                return True
            else:
                Logger.error(f"Missing required fields: {missing_fields}")
                return False
                
        except requests.RequestException as e:
            Logger.error(f"Failed to verify log transformation: {e}")
            return False
    
    def check_data_prepper_metrics(self) -> bool:
        """Check Data Prepper metrics"""
        Logger.info("Checking Data Prepper metrics...")
        
        try:
            response = requests.get(self.data_prepper_metrics_endpoint, timeout=10)
            
            if response.status_code != 200:
                Logger.error("Failed to retrieve Data Prepper metrics")
                return False
            
            metrics_text = response.text
            
            # Check for key metrics
            log_records_in = metrics_text.count("log_pipeline_recordsIn_total")
            log_records_out = metrics_text.count("log_pipeline_recordsOut_total")
            
            if log_records_in > 0 and log_records_out > 0:
                Logger.success("Data Prepper metrics are available and showing log processing activity")
                
                # Extract and show some key metrics
                Logger.info("Key metrics found:")
                for line in metrics_text.split('\n'):
                    if any(metric in line for metric in ["recordsIn_total", "recordsOut_total", "processingTime"]):
                        if not line.startswith('#'):
                            print(f"  {line}")
                
                return True
            else:
                Logger.warning("Data Prepper metrics endpoint is accessible but no log processing metrics found yet")
                return False
                
        except requests.RequestException as e:
            Logger.error(f"Failed to check Data Prepper metrics: {e}")
            return False
    
    def verify_index_template(self) -> bool:
        """Verify OpenSearch index template is applied"""
        Logger.info("Verifying OpenSearch index template is applied...")
        
        try:
            # Check for index template
            response = requests.get(f"{self.opensearch_endpoint}/_index_template")
            
            if response.status_code == 200:
                templates = response.json()
                if "index_templates" in templates and templates["index_templates"]:
                    Logger.success("Index templates are available")
                    return True
            
            # Fallback: check if log indices exist
            response = requests.get(f"{self.opensearch_endpoint}/_cat/indices/logs-*?format=json")
            
            if response.status_code == 200:
                indices = response.json()
                if indices:
                    Logger.success("Log indices exist")
                    return True
            
            Logger.warning("No index templates or log indices found")
            return False
            
        except requests.RequestException as e:
            Logger.error(f"Failed to verify index template: {e}")
            return False
    
    def cleanup_test_data(self) -> bool:
        """Clean up test data"""
        Logger.info("Cleaning up test data...")
        
        delete_query = {
            "query": {
                "term": {"service_name": self.test_service_name}
            }
        }
        
        try:
            response = requests.post(
                f"{self.opensearch_endpoint}/{self.log_index_pattern}/_delete_by_query",
                json=delete_query,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                Logger.success("Test data cleaned up successfully")
                return True
            else:
                Logger.warning(f"Cleanup completed with status: {response.status_code}")
                return True
                
        except requests.RequestException as e:
            Logger.error(f"Failed to cleanup test data: {e}")
            return False
    
    def run_integration_tests(self, cleanup: bool = False, num_logs: int = 4) -> bool:
        """Run the complete integration test suite"""
        Logger.info("Starting OpenSearch Data Prepper Pipeline Integration Tests")
        print("=" * 70)
        
        test_results = []
        
        # Step 1: Check services
        Logger.info("Step 1: Checking services...")
        if not self.check_services():
            Logger.error("Service check failed. Please ensure all services are running with 'docker-compose up -d'")
            return False
        test_results.append(("Service Check", True))
        
        # Step 2: Verify index template
        Logger.info("Step 2: Verifying index template...")
        template_result = self.verify_index_template()
        test_results.append(("Index Template", template_result))
        
        # Step 3: Send test logs
        Logger.info("Step 3: Sending test logs...")
        if not self.send_test_logs(num_logs):
            Logger.error("Failed to send test logs")
            return False
        test_results.append(("Send Test Logs", True))
        
        # Step 4: Wait for processing
        Logger.info("Step 4: Waiting for log processing...")
        self.wait_for_log_processing()
        
        # Step 5: Search and verify logs in OpenSearch
        Logger.info("Step 5: Searching logs in OpenSearch...")
        search_result, _ = self.search_logs_in_opensearch(self.test_service_name, num_logs)
        if not search_result:
            Logger.error("Log search verification failed")
            return False
        test_results.append(("Log Search", True))
        
        # Step 6: Verify log transformation
        Logger.info("Step 6: Verifying log transformation...")
        transform_result = self.verify_log_transformation()
        test_results.append(("Log Transformation", transform_result))
        
        # Step 7: Check Data Prepper metrics
        Logger.info("Step 7: Checking Data Prepper metrics...")
        metrics_result = self.check_data_prepper_metrics()
        test_results.append(("Data Prepper Metrics", metrics_result))
        
        # Step 8: Cleanup (if requested)
        if cleanup:
            Logger.info("Step 8: Cleaning up test data...")
            cleanup_result = self.cleanup_test_data()
            test_results.append(("Cleanup", cleanup_result))
        
        # Print test summary
        print("=" * 70)
        Logger.info("Test Results Summary:")
        all_passed = True
        for test_name, result in test_results:
            status = "PASS" if result else "FAIL"
            color = Colors.GREEN if result else Colors.RED
            print(f"  {color}{status}{Colors.NC} - {test_name}")
            if not result:
                all_passed = False
        
        print("=" * 70)
        if all_passed:
            Logger.success("All integration tests completed successfully!")
            Logger.info("The end-to-end log pipeline is working correctly:")
            Logger.info("  ✓ OTEL Collector receives logs")
            Logger.info("  ✓ Data Prepper processes and transforms logs")
            Logger.info("  ✓ OpenSearch indexes logs with proper mapping")
            Logger.info("  ✓ Logs are searchable and properly formatted")
            return True
        else:
            Logger.error("Some tests failed. Please check the logs above for details.")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="OpenSearch Data Prepper Pipeline Integration Tests")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test data after running tests")
    parser.add_argument("--num-logs", type=int, default=4, help="Number of test logs to generate (default: 4)")
    
    args = parser.parse_args()
    
    test_suite = DataPrepperIntegrationTest()
    
    try:
        success = test_suite.run_integration_tests(cleanup=args.cleanup, num_logs=args.num_logs)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        Logger.warning("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()