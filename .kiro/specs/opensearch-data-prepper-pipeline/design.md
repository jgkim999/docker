# Design Document

## Overview

OpenSearch Data Prepper를 기존 observability 스택에 통합하여 로그 처리 파이프라인을 구축합니다. 현재 otel-collector → Loki 직접 연결 구조를 otel-collector → Data Prepper → OpenSearch 구조로 확장하여, 로그 데이터의 전처리, 변환, 인덱싱 기능을 향상시킵니다.

Data Prepper는 OpenTelemetry Protocol (OTLP)을 지원하므로 기존 otel-collector와 원활하게 통합할 수 있으며, 플러그인 기반 아키텍처를 통해 유연한 로그 처리 파이프라인을 구성할 수 있습니다.

## Architecture

### 전체 아키텍처 다이어그램

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│  OTEL Collector │───▶│  Data Prepper   │───▶│   OpenSearch    │
│     Logs        │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                                              │
                                │                                              ▼
                                ▼                                    ┌─────────────────┐
                       ┌─────────────────┐                          │ OpenSearch      │
                       │      Loki       │                          │ Dashboards      │
                       │   (기존 유지)    │                          │                 │
                       └─────────────────┘                          └─────────────────┘
                                │                                              │
                                ▼                                              ▼
                       ┌─────────────────┐                          ┌─────────────────┐
                       │    Grafana      │◀─────────────────────────│   Monitoring    │
                       │                 │                          │   & Alerting    │
                       └─────────────────┘                          └─────────────────┘
```

### 네트워크 플로우

1. **로그 수집**: 애플리케이션 → OTEL Collector (OTLP/gRPC, OTLP/HTTP)
2. **로그 라우팅**: OTEL Collector → Data Prepper (OTLP/gRPC) + Loki (OTLP/HTTP)
3. **로그 처리**: Data Prepper → OpenSearch (HTTP/JSON)
4. **시각화**: OpenSearch Dashboards, Grafana

## Components and Interfaces

### 1. Data Prepper 서비스

**컨테이너 사양:**

- 이미지: `opensearchproject/data-prepper:2.10.0`
- 포트: 21892 (OTLP gRPC), 4900 (HTTP API), 9600 (메트릭)
- 볼륨: 설정 파일, 데이터 디렉토리

**주요 기능:**

- OTLP 로그 수신 (otel_logs_source)
- 로그 파싱 및 변환 (grok, mutate processors)
- OpenSearch 인덱싱 (opensearch sink)
- 메트릭 노출 (Prometheus 호환)

### 2. OTEL Collector 설정 업데이트

**새로운 Exporter 추가:**

```yaml
exporters:
  otlp/dataprepper:
    endpoint: data-prepper:21892
    tls:
      insecure: true
```

**파이프라인 수정:**

```yaml
service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [resource/remove_sdk_attributes, batch]
      exporters: [otlphttp, otlp/dataprepper]  # 두 대상으로 전송
```

### 3. Data Prepper 파이프라인 설정

**로그 수집 파이프라인:**

```yaml
log-pipeline:
  source:
    otel_logs_source:
      port: 21892
      health_check_service: true
      proto_reflection_service: true
  processor:
    - date:
        match:
          - timestamp
          - "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"
    - mutate:
        rename_keys:
          "attributes.service.name": "service_name"
          "attributes.service.version": "service_version"
    - grok:
        match:
          message: "%{COMMONAPACHELOG}"
        target_key: "parsed_log"
  sink:
    - opensearch:
        hosts: ["http://opensearch:9200"]
        index: "logs-%{yyyy.MM.dd}"
        template_file: "/usr/share/data-prepper/templates/logs-template.json"
```

### 4. OpenSearch 인덱스 템플릿

**로그 인덱스 매핑:**

- 타임스탬프 필드: `@timestamp`
- 서비스 정보: `service_name`, `service_version`
- 로그 레벨: `severity_text`
- 메시지: `body`, `message`
- 리소스 속성: `resource.*`
- 스팬 정보: `trace_id`, `span_id`

## Data Models

### 입력 데이터 (OTLP Logs)

```json
{
  "resourceLogs": [{
    "resource": {
      "attributes": [{
        "key": "service.name",
        "value": {"stringValue": "my-service"}
      }]
    },
    "scopeLogs": [{
      "logRecords": [{
        "timeUnixNano": "1640995200000000000",
        "severityText": "INFO",
        "body": {"stringValue": "User login successful"},
        "attributes": [{
          "key": "user.id",
          "value": {"stringValue": "12345"}
        }],
        "traceId": "abc123...",
        "spanId": "def456..."
      }]
    }]
  }]
}
```

### 출력 데이터 (OpenSearch Document)

```json
{
  "@timestamp": "2021-12-31T15:00:00.000Z",
  "service_name": "my-service",
  "service_version": "1.0.0",
  "severity_text": "INFO",
  "body": "User login successful",
  "message": "User login successful",
  "resource": {
    "service.name": "my-service",
    "service.version": "1.0.0"
  },
  "attributes": {
    "user.id": "12345"
  },
  "trace_id": "abc123...",
  "span_id": "def456...",
  "parsed_log": {
    "timestamp": "2021-12-31T15:00:00.000Z",
    "level": "INFO"
  }
}
```

## Error Handling

### 1. Data Prepper 오류 처리

**재시도 메커니즘:**

- OpenSearch 연결 실패 시 지수 백오프 재시도
- 최대 재시도 횟수: 5회
- 재시도 간격: 1s, 2s, 4s, 8s, 16s

**Dead Letter Queue:**

- 처리 실패한 로그를 별도 파일에 저장
- 경로: `/usr/share/data-prepper/data/dlq/`
- 포맷: JSON Lines

**오류 로깅:**

- Data Prepper 자체 로그를 stdout으로 출력
- 로그 레벨: INFO (운영), DEBUG (개발)
- 구조화된 JSON 로그 포맷

### 2. 네트워크 오류 처리

**OTEL Collector → Data Prepper:**

- 연결 실패 시 로컬 버퍼에 임시 저장
- 버퍼 크기: 1000개 로그 엔트리
- 타임아웃: 30초

**Data Prepper → OpenSearch:**

- 벌크 인덱싱 실패 시 개별 문서로 재시도
- 인덱스 생성 실패 시 기본 인덱스 사용
- 연결 풀 관리: 최대 10개 연결

### 3. 데이터 검증

**입력 검증:**

- OTLP 스키마 준수 확인
- 필수 필드 존재 여부 검사
- 타임스탬프 유효성 검증

**출력 검증:**

- OpenSearch 매핑 호환성 확인
- 필드 타입 변환 오류 처리
- 문서 크기 제한 (1MB) 확인

## Testing Strategy

### 1. 단위 테스트

**Data Prepper 설정 테스트:**

- 파이프라인 설정 파일 구문 검증
- 프로세서 체인 동작 확인
- 싱크 연결 설정 검증

**변환 로직 테스트:**

- Grok 패턴 매칭 테스트
- 필드 매핑 및 변환 테스트
- 타임스탬프 파싱 테스트

### 2. 통합 테스트

**엔드투엔드 파이프라인 테스트:**

```bash
# 1. 테스트 로그 전송
curl -X POST http://localhost:4318/v1/logs \
  -H "Content-Type: application/json" \
  -d @test-logs.json

# 2. OpenSearch에서 로그 확인
curl -X GET "http://localhost:9200/logs-*/_search?q=service_name:test-service"

# 3. 인덱스 매핑 확인
curl -X GET "http://localhost:9200/logs-*/_mapping"
```

**성능 테스트:**

- 로그 처리량: 1000 logs/sec 목표
- 지연시간: 평균 100ms 이하
- 메모리 사용량: 512MB 이하

### 3. 모니터링 테스트

**헬스체크 테스트:**

```bash
# Data Prepper 상태 확인
curl -X GET http://localhost:4900/health

# 메트릭 확인
curl -X GET http://localhost:9600/metrics
```

**알림 테스트:**

- 로그 처리 실패 알림
- OpenSearch 연결 실패 알림
- 디스크 사용량 임계치 알림

### 4. 장애 복구 테스트

**서비스 재시작 테스트:**

- Data Prepper 재시작 시 로그 손실 방지
- OpenSearch 재시작 시 자동 재연결
- 네트워크 분할 시 복구 동작

**데이터 일관성 테스트:**

- 중복 로그 방지 메커니즘
- 순서 보장 (타임스탬프 기준)
- 부분 실패 시 롤백 동작
