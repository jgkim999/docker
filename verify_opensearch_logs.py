#!/usr/bin/env python3
"""
OpenSearch Log Verification Script
This script provides utilities to search, verify, and analyze logs in OpenSearch
"""

import json
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class OpenSearchLogVerifier:
    """Utility class for verifying logs in OpenSearch"""
    
    def __init__(self, opensearch_url: str = "http://localhost:9200"):
        self.opensearch_url = opensearch_url.rstrip('/')
        self.log_index_pattern = "logs-*"
    
    def check_opensearch_connection(self) -> bool:
        """Check if OpenSearch is accessible"""
        try:
            response = requests.get(f"{self.opensearch_url}/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_indices_info(self) -> List[Dict]:
        """Get information about log indices"""
        try:
            response = requests.get(f"{self.opensearch_url}/_cat/indices/{self.log_index_pattern}?format=json")
            if response.status_code == 200:
                return response.json()
            return []
        except requests.RequestException:
            return []
    
    def search_logs(self, query: Dict, index_pattern: str = None) -> Tuple[bool, Dict]:
        """Execute a search query against OpenSearch"""
        if index_pattern is None:
            index_pattern = self.log_index_pattern
            
        try:
            response = requests.get(
                f"{self.opensearch_url}/{index_pattern}/_search",
                json=query,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.RequestException as e:
            return False, {"error": str(e)}
    
    def search_by_service(self, service_name: str, limit: int = 10) -> Tuple[bool, List[Dict]]:
        """Search logs by service name"""
        query = {
            "query": {
                "term": {"service_name": service_name}
            },
            "size": limit,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        success, result = self.search_logs(query)
        if success:
            hits = result.get("hits", {}).get("hits", [])
            logs = [hit.get("_source", {}) for hit in hits]
            return True, logs
        else:
            return False, []
    
    def search_by_severity(self, severity: str, limit: int = 10) -> Tuple[bool, List[Dict]]:
        """Search logs by severity level"""
        query = {
            "query": {
                "term": {"severity_text": severity.upper()}
            },
            "size": limit,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        success, result = self.search_logs(query)
        if success:
            hits = result.get("hits", {}).get("hits", [])
            logs = [hit.get("_source", {}) for hit in hits]
            return True, logs
        else:
            return False, []
    
    def search_by_time_range(self, start_time: str, end_time: str = None, limit: int = 10) -> Tuple[bool, List[Dict]]:
        """Search logs within a time range"""
        if end_time is None:
            end_time = datetime.utcnow().isoformat() + "Z"
        
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": start_time,
                        "lte": end_time
                    }
                }
            },
            "size": limit,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        success, result = self.search_logs(query)
        if success:
            hits = result.get("hits", {}).get("hits", [])
            logs = [hit.get("_source", {}) for hit in hits]
            return True, logs
        else:
            return False, []
    
    def search_by_trace_id(self, trace_id: str) -> Tuple[bool, List[Dict]]:
        """Search logs by trace ID"""
        query = {
            "query": {
                "term": {"trace_id": trace_id}
            },
            "size": 100,
            "sort": [{"@timestamp": {"order": "asc"}}]
        }
        
        success, result = self.search_logs(query)
        if success:
            hits = result.get("hits", {}).get("hits", [])
            logs = [hit.get("_source", {}) for hit in hits]
            return True, logs
        else:
            return False, []
    
    def get_log_statistics(self) -> Dict:
        """Get statistics about logs in OpenSearch"""
        # Get total count
        count_query = {"query": {"match_all": {}}}
        success, result = self.search_logs(count_query)
        
        if not success:
            return {"error": "Failed to get log statistics"}
        
        total_logs = result.get("hits", {}).get("total", {})
        if isinstance(total_logs, dict):
            total_count = total_logs.get("value", 0)
        else:
            total_count = total_logs
        
        # Get severity distribution
        severity_agg_query = {
            "size": 0,
            "aggs": {
                "severity_distribution": {
                    "terms": {
                        "field": "severity_text",
                        "size": 10
                    }
                },
                "service_distribution": {
                    "terms": {
                        "field": "service_name",
                        "size": 10
                    }
                }
            }
        }
        
        success, agg_result = self.search_logs(severity_agg_query)
        
        stats = {
            "total_logs": total_count,
            "severity_distribution": {},
            "service_distribution": {}
        }
        
        if success:
            aggs = agg_result.get("aggregations", {})
            
            # Severity distribution
            severity_buckets = aggs.get("severity_distribution", {}).get("buckets", [])
            for bucket in severity_buckets:
                stats["severity_distribution"][bucket["key"]] = bucket["doc_count"]
            
            # Service distribution
            service_buckets = aggs.get("service_distribution", {}).get("buckets", [])
            for bucket in service_buckets:
                stats["service_distribution"][bucket["key"]] = bucket["doc_count"]
        
        return stats
    
    def verify_log_fields(self, required_fields: List[str], sample_size: int = 10) -> Dict:
        """Verify that logs contain required fields"""
        query = {
            "query": {"match_all": {}},
            "size": sample_size
        }
        
        success, result = self.search_logs(query)
        if not success:
            return {"error": "Failed to retrieve logs for field verification"}
        
        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            return {"error": "No logs found for verification"}
        
        field_stats = {}
        for field in required_fields:
            field_stats[field] = {
                "present": 0,
                "missing": 0,
                "sample_values": []
            }
        
        for hit in hits:
            source = hit.get("_source", {})
            for field in required_fields:
                if field in source and source[field] is not None:
                    field_stats[field]["present"] += 1
                    if len(field_stats[field]["sample_values"]) < 3:
                        field_stats[field]["sample_values"].append(str(source[field]))
                else:
                    field_stats[field]["missing"] += 1
        
        return {
            "total_logs_checked": len(hits),
            "field_statistics": field_stats
        }
    
    def delete_logs_by_service(self, service_name: str) -> bool:
        """Delete logs for a specific service"""
        delete_query = {
            "query": {
                "term": {"service_name": service_name}
            }
        }
        
        try:
            response = requests.post(
                f"{self.opensearch_url}/{self.log_index_pattern}/_delete_by_query",
                json=delete_query,
                headers={"Content-Type": "application/json"}
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

def print_logs(logs: List[Dict], max_logs: int = 10):
    """Pretty print log entries"""
    if not logs:
        print("No logs found.")
        return
    
    print(f"Found {len(logs)} log entries:")
    print("-" * 80)
    
    for i, log in enumerate(logs[:max_logs]):
        timestamp = log.get("@timestamp", "N/A")
        service = log.get("service_name", "N/A")
        severity = log.get("severity_text", "N/A")
        message = log.get("message", log.get("body", "N/A"))
        
        print(f"{i+1}. [{timestamp}] {severity} - {service}")
        print(f"   Message: {message}")
        
        # Show trace info if available
        trace_id = log.get("trace_id")
        if trace_id:
            print(f"   Trace ID: {trace_id}")
        
        print()
    
    if len(logs) > max_logs:
        print(f"... and {len(logs) - max_logs} more logs")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Verify and search logs in OpenSearch")
    parser.add_argument("--opensearch-url", default="http://localhost:9200",
                       help="OpenSearch URL (default: http://localhost:9200)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check OpenSearch status and indices")
    
    # Search by service command
    service_parser = subparsers.add_parser("search-service", help="Search logs by service name")
    service_parser.add_argument("service_name", help="Service name to search for")
    service_parser.add_argument("--limit", type=int, default=10, help="Maximum number of logs to return")
    
    # Search by severity command
    severity_parser = subparsers.add_parser("search-severity", help="Search logs by severity level")
    severity_parser.add_argument("severity", choices=["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
                                help="Severity level to search for")
    severity_parser.add_argument("--limit", type=int, default=10, help="Maximum number of logs to return")
    
    # Search by trace ID command
    trace_parser = subparsers.add_parser("search-trace", help="Search logs by trace ID")
    trace_parser.add_argument("trace_id", help="Trace ID to search for")
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Get log statistics")
    
    # Verify fields command
    verify_parser = subparsers.add_parser("verify-fields", help="Verify required fields in logs")
    verify_parser.add_argument("--fields", nargs="+", 
                              default=["@timestamp", "service_name", "severity_text", "message"],
                              help="Required fields to verify")
    verify_parser.add_argument("--sample-size", type=int, default=10,
                              help="Number of logs to sample for verification")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete-service", help="Delete logs for a service")
    delete_parser.add_argument("service_name", help="Service name to delete logs for")
    delete_parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    verifier = OpenSearchLogVerifier(args.opensearch_url)
    
    # Check connection first
    if not verifier.check_opensearch_connection():
        print(f"Error: Cannot connect to OpenSearch at {args.opensearch_url}")
        return
    
    if args.command == "status":
        print(f"OpenSearch connection: OK ({args.opensearch_url})")
        indices = verifier.get_indices_info()
        if indices:
            print(f"\nLog indices ({len(indices)} found):")
            for idx in indices:
                print(f"  - {idx.get('index', 'N/A')}: {idx.get('docs.count', 'N/A')} docs, "
                      f"{idx.get('store.size', 'N/A')} size")
        else:
            print("No log indices found.")
    
    elif args.command == "search-service":
        success, logs = verifier.search_by_service(args.service_name, args.limit)
        if success:
            print_logs(logs, args.limit)
        else:
            print("Error: Failed to search logs by service")
    
    elif args.command == "search-severity":
        success, logs = verifier.search_by_severity(args.severity, args.limit)
        if success:
            print_logs(logs, args.limit)
        else:
            print("Error: Failed to search logs by severity")
    
    elif args.command == "search-trace":
        success, logs = verifier.search_by_trace_id(args.trace_id)
        if success:
            print_logs(logs)
        else:
            print("Error: Failed to search logs by trace ID")
    
    elif args.command == "stats":
        stats = verifier.get_log_statistics()
        if "error" in stats:
            print(f"Error: {stats['error']}")
        else:
            print(f"Total logs: {stats['total_logs']}")
            
            if stats["severity_distribution"]:
                print("\nSeverity distribution:")
                for severity, count in stats["severity_distribution"].items():
                    print(f"  {severity}: {count}")
            
            if stats["service_distribution"]:
                print("\nService distribution:")
                for service, count in stats["service_distribution"].items():
                    print(f"  {service}: {count}")
    
    elif args.command == "verify-fields":
        result = verifier.verify_log_fields(args.fields, args.sample_size)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Verified {result['total_logs_checked']} log entries:")
            print()
            
            for field, stats in result["field_statistics"].items():
                present = stats["present"]
                missing = stats["missing"]
                total = present + missing
                percentage = (present / total * 100) if total > 0 else 0
                
                print(f"Field '{field}': {present}/{total} ({percentage:.1f}%) present")
                if stats["sample_values"]:
                    print(f"  Sample values: {', '.join(stats['sample_values'])}")
                print()
    
    elif args.command == "delete-service":
        if not args.confirm:
            print(f"This will delete all logs for service '{args.service_name}'.")
            print("Use --confirm to proceed with deletion.")
            return
        
        success = verifier.delete_logs_by_service(args.service_name)
        if success:
            print(f"Successfully deleted logs for service '{args.service_name}'")
        else:
            print(f"Failed to delete logs for service '{args.service_name}'")

if __name__ == "__main__":
    main()