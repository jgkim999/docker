# Data Prepper 모니터링 가이드

이 문서는 Data Prepper 로그 파이프라인의 모니터링 대시보드와 알림 시스템 사용법을 설명합니다.

## 개요

Data Prepper 모니터링 시스템은 다음 구성 요소로 이루어져 있습니다:

- **Grafana 대시보드**: 실시간 메트릭 시각화
- **Prometheus 알림 규칙**: 자동화된 알림 및 임계값 모니터링
- **메트릭 수집**: Data Prepper에서 노출되는 Prometheus 메트릭

## 파일 구성

### 1. `grafana-data-prepper-dashboard.json`
Grafana에서 가져올 수 있는 대시보드 정의 파일입니다.

### 2. `data-prepper-alerts.yml`
Prometheus 알림 규칙을 정의한 파일입니다.

### 3. `prometheus.yml` (업데이트됨)
Data Prepper 메트릭 수집 및 알림 규칙 로드 설정이 추가되었습니다.

## 대시보드 설치 및 설정

### 1. Grafana 대시보드 가져오기

1. Grafana 웹 인터페이스에 접속 (기본: http://localhost:3000)
2. 좌측 메뉴에서 "+" → "Import" 선택
3. "Upload JSON file" 버튼을 클릭하고 `grafana-data-prepper-dashboard.json` 파일 선택
4. 대시보드 설정 확인 후 "Import" 클릭

### 2. 데이터 소스 설정 확인

대시보드가 올바르게 작동하려면 Prometheus 데이터 소스가 설정되어 있어야 합니다:

1. Grafana에서 Configuration → Data Sources 이동
2. Prometheus 데이터 소스 확인 (URL: http://prometheus:9090)
3. "Test" 버튼으로 연결 확인

## 모니터링 메트릭

### 주요 메트릭 패널

#### 1. 서비스 상태
- **메트릭**: `up{job="data-prepper"}`
- **설명**: Data Prepper 서비스의 가동 상태
- **임계값**: 0 (DOWN), 1 (UP)

#### 2. 로그 처리량
- **메트릭**: 
  - `rate(dataprepper_records_in_total[5m])` - 입력 레코드/초
  - `rate(dataprepper_records_out_total[5m])` - 출력 레코드/초
- **설명**: 초당 처리되는 로그 레코드 수
- **목표**: 1000+ records/sec

#### 3. 처리 지연시간
- **메트릭**: `histogram_quantile(0.95, rate(dataprepper_processing_time_seconds_bucket[5m]))`
- **설명**: 95th percentile 처리 시간
- **목표**: < 100ms (평균), < 1000ms (P95)

#### 4. 오류율
- **메트릭**: `rate(dataprepper_records_errors_total[5m])`
- **설명**: 초당 오류 발생 수
- **목표**: < 1 error/sec

#### 5. 메모리 사용률
- **메트릭**: `(jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}) * 100`
- **설명**: JVM 힙 메모리 사용률
- **임계값**: 
  - 경고: 80%
  - 위험: 95%

#### 6. OpenSearch 싱크 성능
- **메트릭**:
  - `rate(dataprepper_opensearch_documents_success_total[5m])` - 성공한 인덱싱/초
  - `rate(dataprepper_opensearch_documents_errors_total[5m])` - 인덱싱 오류/초
- **설명**: OpenSearch로의 문서 인덱싱 성능

## 알림 규칙

### 심각도 레벨

#### Critical (심각)
- **DataPrepperDown**: 서비스 다운 (1분)
- **DataPrepperCriticalErrorRate**: 초당 50+ 오류 (1분)
- **DataPrepperCriticalLatency**: P95 지연시간 > 5초 (2분)
- **DataPrepperCriticalMemoryUsage**: 메모리 사용률 > 95% (2분)
- **DataPrepperNoThroughput**: 처리량 없음 (5분)

#### Warning (경고)
- **DataPrepperHighErrorRate**: 초당 10+ 오류 (2분)
- **DataPrepperHighLatency**: P95 지연시간 > 1초 (5분)
- **DataPrepperHighMemoryUsage**: 메모리 사용률 > 80% (5분)
- **DataPrepperLowThroughput**: 처리량 < 10 records/sec (10분)

### 알림 설정 방법

1. **Prometheus 설정 확인**
   ```bash
   # Prometheus 설정 리로드
   curl -X POST http://localhost:9090/-/reload
   
   # 알림 규칙 확인
   curl http://localhost:9090/api/v1/rules
   ```

2. **Alertmanager 설정** (선택사항)
   ```yaml
   # alertmanager.yml 예시
   global:
     smtp_smarthost: 'localhost:587'
     smtp_from: 'alerts@company.com'
   
   route:
     group_by: ['alertname']
     group_wait: 10s
     group_interval: 10s
     repeat_interval: 1h
     receiver: 'web.hook'
   
   receivers:
   - name: 'web.hook'
     email_configs:
     - to: 'admin@company.com'
       subject: 'Data Prepper Alert: {{ .GroupLabels.alertname }}'
       body: |
         {{ range .Alerts }}
         Alert: {{ .Annotations.summary }}
         Description: {{ .Annotations.description }}
         {{ end }}
   ```

## 성능 최적화 가이드

### 1. 처리량 최적화

**증상**: 낮은 처리량 (< 100 records/sec)

**해결책**:
```yaml
# data-prepper.yaml 설정 조정
log-pipeline:
  sink:
    - opensearch:
        bulk_size: 500  # 기본값에서 증가
        flush_timeout: 2s  # 기본값에서 감소
        max_retries: 3
```

### 2. 지연시간 최적화

**증상**: 높은 P95 지연시간 (> 1초)

**해결책**:
```yaml
# 프로세서 체인 최적화
log-pipeline:
  processor:
    - date:
        match:
          - timestamp: "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"
    # grok 프로세서 제거 또는 단순화
    - mutate:
        rename_keys:
          "attributes.service.name": "service_name"
```

### 3. 메모리 사용량 최적화

**증상**: 높은 메모리 사용률 (> 80%)

**해결책**:
```bash
# docker-compose.yml에서 JVM 힙 크기 조정
environment:
  - JAVA_OPTS=-Xms512m -Xmx1024m
```

## 트러블슈팅

### 1. 메트릭이 표시되지 않는 경우

1. **Data Prepper 메트릭 엔드포인트 확인**:
   ```bash
   curl http://localhost:9600/metrics
   ```

2. **Prometheus 타겟 상태 확인**:
   - http://localhost:9090/targets 접속
   - data-prepper 타겟이 UP 상태인지 확인

3. **네트워크 연결 확인**:
   ```bash
   docker exec prometheus ping data-prepper
   ```

### 2. 알림이 발생하지 않는 경우

1. **알림 규칙 로드 확인**:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```

2. **알림 상태 확인**:
   - http://localhost:9090/alerts 접속
   - 알림 규칙 상태 확인

### 3. 대시보드 데이터가 없는 경우

1. **시간 범위 확인**: 대시보드 상단의 시간 선택기 확인
2. **데이터 소스 확인**: Prometheus 연결 상태 확인
3. **메트릭 이름 확인**: Data Prepper 버전에 따른 메트릭 이름 차이 확인

## 모니터링 베스트 프랙티스

### 1. 정기적인 성능 검토
- 주간 처리량 및 지연시간 트렌드 분석
- 월간 오류율 및 가용성 리포트 생성
- 분기별 용량 계획 및 확장성 검토

### 2. 알림 임계값 조정
- 운영 환경에 맞는 임계값 설정
- False positive 최소화를 위한 지속 시간 조정
- 비즈니스 시간 기반 알림 스케줄링

### 3. 대시보드 커스터마이징
- 팀별 관심 메트릭에 따른 패널 추가/제거
- 비즈니스 KPI와 연결된 메트릭 추가
- 드릴다운 링크를 통한 상세 분석 지원

## 추가 리소스

- [Data Prepper 공식 문서](https://opensearch.org/docs/latest/data-prepper/)
- [Prometheus 메트릭 가이드](https://prometheus.io/docs/concepts/metric_types/)
- [Grafana 대시보드 가이드](https://grafana.com/docs/grafana/latest/dashboards/)
- [OpenSearch 모니터링](https://opensearch.org/docs/latest/monitoring-your-cluster/)