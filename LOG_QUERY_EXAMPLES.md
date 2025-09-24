# OpenSearch Log Query Examples

## Overview

This document provides comprehensive examples for querying logs stored in OpenSearch through the Data Prepper pipeline. Examples cover both REST API queries and OpenSearch Dashboards query syntax.

## Index Structure

Logs are stored in daily indices with the pattern `logs-YYYY.MM.DD` and contain the following key fields:

- `@timestamp`: Log timestamp (ISO 8601 format)
- `service_name`: Name of the service that generated the log
- `service_version`: Version of the service
- `severity_text`: Log level (DEBUG, INFO, WARN, ERROR, FATAL)
- `body`: Original log message
- `message`: Processed log message
- `trace_id`: Distributed tracing ID (if available)
- `span_id`: Span ID within the trace
- `resource.*`: Resource attributes from OTEL
- `attributes.*`: Custom log attributes
- `parsed_log.*`: Fields extracted by grok patterns

## REST API Query Examples

### Basic Queries

#### Search All Recent Logs
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match_all": {}
    },
    "sort": [{"@timestamp": {"order": "desc"}}],
    "size": 100
  }'
```

#### Search by Service Name
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "service_name": "web-api"
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

#### Search by Log Level
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": {
        "severity_text": "ERROR"
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

### Time-Based Queries

#### Last Hour Logs
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "gte": "now-1h"
        }
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

#### Specific Time Range
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "gte": "2024-01-01T00:00:00Z",
          "lte": "2024-01-01T23:59:59Z"
        }
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

#### Business Hours Only
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "range": {
              "@timestamp": {
                "gte": "now-1d"
              }
            }
          }
        ],
        "filter": [
          {
            "script": {
              "script": {
                "source": "def hour = doc[\"@timestamp\"].value.getHour(); hour >= 9 && hour <= 17"
              }
            }
          }
        ]
      }
    }
  }'
```

### Complex Boolean Queries

#### Multiple Conditions (AND)
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"match": {"service_name": "payment-service"}},
          {"term": {"severity_text": "ERROR"}},
          {"range": {"@timestamp": {"gte": "now-24h"}}}
        ]
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

#### Multiple Conditions (OR)
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "should": [
          {"term": {"severity_text": "ERROR"}},
          {"term": {"severity_text": "FATAL"}}
        ],
        "minimum_should_match": 1
      }
    },
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

#### Exclude Conditions (NOT)
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"match": {"service_name": "web-app"}}
        ],
        "must_not": [
          {"term": {"severity_text": "DEBUG"}},
          {"match": {"message": "health check"}}
        ]
      }
    }
  }'
```

### Text Search Queries

#### Full-Text Search in Message
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "message": {
          "query": "database connection failed",
          "operator": "and"
        }
      }
    },
    "highlight": {
      "fields": {
        "message": {}
      }
    }
  }'
```

#### Wildcard Search
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "wildcard": {
        "message": "*exception*"
      }
    }
  }'
```

#### Regex Search
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "regexp": {
        "message": ".*[Ee]rror.*[0-9]{3,4}.*"
      }
    }
  }'
```

#### Fuzzy Search (Typo Tolerance)
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "fuzzy": {
        "message": {
          "value": "conection",
          "fuzziness": "AUTO"
        }
      }
    }
  }'
```

### Field Existence and Missing Data

#### Logs with Trace ID
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "exists": {
        "field": "trace_id"
      }
    }
  }'
```

#### Logs Missing Service Version
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must_not": [
          {"exists": {"field": "service_version"}}
        ]
      }
    }
  }'
```

### Aggregation Queries

#### Log Count by Service
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "aggs": {
      "services": {
        "terms": {
          "field": "service_name.keyword",
          "size": 20
        }
      }
    }
  }'
```

#### Error Rate by Hour
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "aggs": {
      "errors_over_time": {
        "date_histogram": {
          "field": "@timestamp",
          "calendar_interval": "1h"
        },
        "aggs": {
          "error_count": {
            "filter": {
              "term": {"severity_text": "ERROR"}
            }
          }
        }
      }
    }
  }'
```

#### Top Error Messages
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "query": {
      "term": {"severity_text": "ERROR"}
    },
    "aggs": {
      "top_errors": {
        "terms": {
          "field": "message.keyword",
          "size": 10
        }
      }
    }
  }'
```

#### Service Performance Metrics
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "aggs": {
      "services": {
        "terms": {
          "field": "service_name.keyword"
        },
        "aggs": {
          "error_rate": {
            "filter": {
              "terms": {"severity_text": ["ERROR", "FATAL"]}
            }
          },
          "total_logs": {
            "value_count": {
              "field": "@timestamp"
            }
          }
        }
      }
    }
  }'
```

### Distributed Tracing Queries

#### Find All Logs for a Trace
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": {
        "trace_id": "abc123def456789"
      }
    },
    "sort": [{"@timestamp": {"order": "asc"}}]
  }'
```

#### Find Errors in Traces
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"exists": {"field": "trace_id"}},
          {"terms": {"severity_text": ["ERROR", "FATAL"]}}
        ]
      }
    },
    "aggs": {
      "error_traces": {
        "terms": {
          "field": "trace_id.keyword",
          "size": 100
        }
      }
    }
  }'
```

## OpenSearch Dashboards Query Examples

### Discover Tab Queries

#### Basic KQL (Kibana Query Language) Examples

```kql
# Service-specific logs
service_name:"web-api"

# Error logs only
severity_text:"ERROR"

# Multiple services
service_name:("web-api" OR "payment-service")

# Exclude debug logs
NOT severity_text:"DEBUG"

# Time range with text search
@timestamp:[now-1h TO now] AND message:*exception*

# Field existence
_exists_:trace_id

# Wildcard matching
service_name:web-*

# Numeric range (if you have numeric fields)
response_time:[100 TO 500]
```

#### Advanced KQL Queries

```kql
# Complex boolean logic
(service_name:"web-api" AND severity_text:"ERROR") OR (service_name:"payment-service" AND message:*timeout*)

# Nested field queries
attributes.user_id:"12345" AND severity_text:"INFO"

# Regular expressions (limited support)
message:/.*[Ee]rror.*/

# Multiple field search
service_name:"web-api" AND (message:*database* OR message:*connection*)

# Date math
@timestamp:[now-1d/d TO now/d] AND severity_text:"ERROR"
```

### Visualization Queries

#### Line Chart: Log Volume Over Time
- **Index Pattern**: `logs-*`
- **Time Field**: `@timestamp`
- **Metric**: Count
- **Buckets**: Date Histogram on `@timestamp`
- **Split Series**: Terms aggregation on `service_name.keyword`

#### Pie Chart: Log Distribution by Service
- **Metric**: Count
- **Buckets**: Terms aggregation on `service_name.keyword`
- **Size**: 10

#### Data Table: Top Error Messages
- **Metric**: Count
- **Buckets**: Terms aggregation on `message.keyword`
- **Filter**: `severity_text:"ERROR"`
- **Size**: 20

#### Heat Map: Error Rate by Service and Hour
- **Metric**: Count
- **X-Axis**: Date Histogram on `@timestamp` (hourly)
- **Y-Axis**: Terms aggregation on `service_name.keyword`
- **Filter**: `severity_text:"ERROR"`

## Performance Optimization Tips

### Query Performance

#### Use Filters Instead of Queries When Possible
```bash
# Faster (filter context)
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"service_name": "web-api"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}

# Slower (query context)
{
  "query": {
    "bool": {
      "must": [
        {"match": {"service_name": "web-api"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

#### Limit Result Size
```bash
# Always specify size for large datasets
{
  "query": {"match_all": {}},
  "size": 100,
  "from": 0
}
```

#### Use Source Filtering
```bash
# Only return specific fields
{
  "query": {"match_all": {}},
  "_source": ["@timestamp", "service_name", "severity_text", "message"]
}
```

### Index Optimization

#### Use Appropriate Field Types
- Use `keyword` for exact matches and aggregations
- Use `text` for full-text search
- Use `date` for timestamp fields
- Use `long` or `double` for numeric fields

#### Optimize Queries for Daily Indices
```bash
# Query specific date range to limit indices searched
curl -X GET "localhost:9200/logs-2024.01.01,logs-2024.01.02/_search"
```

## Common Use Cases

### Application Monitoring

#### Find Application Errors in Last Hour
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"severity_text": "ERROR"}},
          {"range": {"@timestamp": {"gte": "now-1h"}}}
        ]
      }
    },
    "aggs": {
      "by_service": {
        "terms": {"field": "service_name.keyword"}
      }
    }
  }'
```

#### Track User Journey Through Services
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"trace_id": "your-trace-id"}},
          {"range": {"@timestamp": {"gte": "now-1h"}}}
        ]
      }
    },
    "sort": [{"@timestamp": {"order": "asc"}}],
    "_source": ["@timestamp", "service_name", "message", "span_id"]
  }'
```

### Security Monitoring

#### Find Failed Authentication Attempts
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"match": {"message": "authentication failed"}},
          {"range": {"@timestamp": {"gte": "now-24h"}}}
        ]
      }
    },
    "aggs": {
      "by_ip": {
        "terms": {"field": "attributes.client_ip.keyword"}
      }
    }
  }'
```

### Performance Analysis

#### Find Slow Operations
```bash
curl -X GET "localhost:9200/logs-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"exists": {"field": "attributes.duration_ms"}},
          {"range": {"attributes.duration_ms": {"gte": 1000}}}
        ]
      }
    },
    "sort": [{"attributes.duration_ms": {"order": "desc"}}]
  }'
```

This comprehensive guide should help you effectively query and analyze logs stored in OpenSearch through the Data Prepper pipeline. Remember to adjust field names and values based on your specific log structure and requirements.