#!/usr/bin/env python3
"""
Test Log Data Generator for OpenSearch Data Prepper Pipeline
This script generates various types of test log data in OTLP format
"""

import json
import time
import uuid
import random
import argparse
from datetime import datetime, timezone
from typing import Dict, List

class TestLogGenerator:
    """Generate test log data in OTLP format"""
    
    def __init__(self, service_name: str = "test-service", service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        
    def generate_log_templates(self) -> List[Dict]:
        """Generate various log message templates"""
        return [
            {
                "severity": (9, "INFO"),
                "message_template": "User authentication successful for user_id={user_id}",
                "attributes": {
                    "user.id": lambda: str(random.randint(10000, 99999)),
                    "action": "login",
                    "ip_address": lambda: f"192.168.1.{random.randint(1, 254)}",
                    "user_agent": "Mozilla/5.0 (compatible; TestClient/1.0)"
                }
            },
            {
                "severity": (13, "ERROR"),
                "message_template": "Database connection failed: {error_reason}",
                "attributes": {
                    "database.name": lambda: random.choice(["user_db", "product_db", "order_db"]),
                    "error.type": lambda: random.choice(["connection_timeout", "auth_failed", "network_error"]),
                    "retry_count": lambda: str(random.randint(1, 5)),
                    "error_reason": lambda: random.choice(["timeout after 30s", "authentication failed", "host unreachable"])
                }
            },
            {
                "severity": (5, "DEBUG"),
                "message_template": "Processing request with correlation_id={correlation_id}",
                "attributes": {
                    "correlation_id": lambda: uuid.uuid4().hex[:8],
                    "request.method": lambda: random.choice(["GET", "POST", "PUT", "DELETE"]),
                    "request.path": lambda: random.choice(["/api/v1/users", "/api/v1/orders", "/api/v1/products"]),
                    "response.status_code": lambda: str(random.choice([200, 201, 400, 404, 500]))
                }
            },
            {
                "severity": (17, "FATAL"),
                "message_template": "Critical system failure: {failure_type}",
                "attributes": {
                    "memory.used": lambda: f"{random.randint(85, 99)}%",
                    "system.component": lambda: random.choice(["application_server", "database", "cache_layer"]),
                    "failure_type": lambda: random.choice(["out of memory", "disk full", "service unavailable"])
                }
            },
            {
                "severity": (12, "WARN"),
                "message_template": "High response time detected: {response_time}ms for endpoint {endpoint}",
                "attributes": {
                    "response_time": lambda: str(random.randint(1000, 5000)),
                    "endpoint": lambda: random.choice(["/api/search", "/api/checkout", "/api/report"]),
                    "threshold": "1000ms",
                    "client_id": lambda: f"client_{random.randint(1000, 9999)}"
                }
            },
            {
                "severity": (9, "INFO"),
                "message_template": "Order {order_id} processed successfully for customer {customer_id}",
                "attributes": {
                    "order_id": lambda: f"ORD-{random.randint(100000, 999999)}",
                    "customer_id": lambda: f"CUST-{random.randint(10000, 99999)}",
                    "order_amount": lambda: f"${random.randint(10, 1000)}.{random.randint(10, 99)}",
                    "payment_method": lambda: random.choice(["credit_card", "paypal", "bank_transfer"])
                }
            }
        ]
    
    def resolve_template_values(self, template: Dict) -> Dict:
        """Resolve lambda functions in template to actual values"""
        resolved = template.copy()
        resolved_attributes = {}
        
        # Resolve message template
        format_values = {}
        for key, value in template["attributes"].items():
            if callable(value):
                actual_value = value()
                resolved_attributes[key] = actual_value
                # Check if this value should be used in message formatting
                if f"{{{key}}}" in template["message_template"]:
                    format_values[key] = actual_value
            else:
                resolved_attributes[key] = value
                if f"{{{key}}}" in template["message_template"]:
                    format_values[key] = value
        
        # Format the message
        try:
            resolved["message"] = template["message_template"].format(**format_values)
        except KeyError:
            resolved["message"] = template["message_template"]
        
        resolved["attributes"] = resolved_attributes
        return resolved
    
    def generate_otlp_logs(self, num_logs: int = 5, trace_id: str = None) -> Dict:
        """Generate OTLP format log data"""
        if trace_id is None:
            trace_id = uuid.uuid4().hex
            
        current_time_ns = int(time.time() * 1_000_000_000)
        log_templates = self.generate_log_templates()
        log_records = []
        
        for i in range(num_logs):
            # Select a random template
            template = random.choice(log_templates)
            resolved_template = self.resolve_template_values(template)
            
            # Convert attributes to OTLP format
            otlp_attributes = []
            for key, value in resolved_template["attributes"].items():
                otlp_attributes.append({
                    "key": key,
                    "value": {"stringValue": str(value)}
                })
            
            # Create log record
            log_record = {
                "timeUnixNano": str(current_time_ns + i * 1000000),  # Add microsecond offset
                "observedTimeUnixNano": str(current_time_ns + i * 1000000),
                "severityNumber": resolved_template["severity"][0],
                "severityText": resolved_template["severity"][1],
                "body": {"stringValue": resolved_template["message"]},
                "attributes": otlp_attributes,
                "traceId": trace_id,
                "spanId": uuid.uuid4().hex[:16],
                "flags": 1
            }
            
            log_records.append(log_record)
        
        # Create OTLP resource logs structure
        return {
            "resourceLogs": [{
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": self.service_name}
                        },
                        {
                            "key": "service.version",
                            "value": {"stringValue": self.service_version}
                        },
                        {
                            "key": "host.name",
                            "value": {"stringValue": f"host-{random.randint(1, 10):02d}"}
                        },
                        {
                            "key": "container.name",
                            "value": {"stringValue": f"{self.service_name}-container"}
                        },
                        {
                            "key": "deployment.environment",
                            "value": {"stringValue": random.choice(["development", "staging", "production"])}
                        }
                    ]
                },
                "scopeLogs": [{
                    "scope": {
                        "name": f"{self.service_name}-logger",
                        "version": "1.0.0"
                    },
                    "logRecords": log_records
                }]
            }]
        }
    
    def generate_structured_logs(self, num_logs: int = 5) -> List[Dict]:
        """Generate structured log entries (not OTLP format)"""
        log_templates = self.generate_log_templates()
        logs = []
        
        for i in range(num_logs):
            template = random.choice(log_templates)
            resolved_template = self.resolve_template_values(template)
            
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service_name": self.service_name,
                "service_version": self.service_version,
                "severity_text": resolved_template["severity"][1],
                "severity_number": resolved_template["severity"][0],
                "message": resolved_template["message"],
                "attributes": resolved_template["attributes"],
                "trace_id": uuid.uuid4().hex,
                "span_id": uuid.uuid4().hex[:16]
            }
            
            logs.append(log_entry)
        
        return logs

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate test log data for Data Prepper pipeline")
    parser.add_argument("--format", choices=["otlp", "structured"], default="otlp",
                       help="Output format (default: otlp)")
    parser.add_argument("--num-logs", type=int, default=5,
                       help="Number of log entries to generate (default: 5)")
    parser.add_argument("--service-name", default="test-service",
                       help="Service name for logs (default: test-service)")
    parser.add_argument("--service-version", default="1.0.0",
                       help="Service version for logs (default: 1.0.0)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--pretty", action="store_true",
                       help="Pretty print JSON output")
    
    args = parser.parse_args()
    
    generator = TestLogGenerator(args.service_name, args.service_version)
    
    if args.format == "otlp":
        data = generator.generate_otlp_logs(args.num_logs)
    else:
        data = generator.generate_structured_logs(args.num_logs)
    
    # Format output
    if args.pretty:
        json_output = json.dumps(data, indent=2)
    else:
        json_output = json.dumps(data)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f"Generated {args.num_logs} log entries in {args.format} format -> {args.output}")
    else:
        print(json_output)

if __name__ == "__main__":
    main()