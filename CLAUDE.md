# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 가이드를 제공합니다.

## 저장소 개요

이것은 완전한 관측 가능성 및 인프라 스택을 위한 포괄적인 Docker Compose 설정입니다. 프로덕션 환경에서 일반적으로 사용되는 모니터링, 로깅, 추적, 데이터베이스 및 관리 도구를 포함합니다.

## 핵심 아키텍처

스택은 여러 주요 관측 가능성 기둥을 중심으로 구성됩니다:

- **메트릭**: Prometheus (수집), Grafana (시각화), Node Exporter & cAdvisor (시스템 메트릭)
- **로깅**: Loki (집계), OpenSearch (검색/분석), OpenSearch Dashboards (시각화)
- **추적**: Jaeger (분산 추적), Tempo (추적 저장), OpenTelemetry Collector (텔레메트리 파이프라인)
- **데이터베이스**: MySQL 8.4.6, PostgreSQL 17.5 (한국어 로케일), Valkey (Redis 호환)
- **메시징**: RabbitMQ 4.1 (관리 인터페이스 포함)
- **관리**: Portainer (컨테이너 관리)

## 일반적인 명령어

### 서비스 시작/중지

```bash
# 모든 서비스 시작
docker-compose up -d
# 또는
docker compose up -d

# 모든 서비스 중지
docker-compose down

# 특정 서비스 로그 보기
docker-compose logs -f [service-name]
```

### 환경 설정

- 주요 환경 변수는 `.env` 파일에 있음 (DATA_DIR 설정)
- 각 서비스는 고유한 `.env.[service-name]` 파일을 가짐
- 기본 DATA_DIR: `${HOME}/docker-data` (Windows에서는 `%USERPROFILE%/docker-data`)

## 서비스 포트 및 접근

| 서비스 | 포트 | 기본 인증정보 | 목적 |
|---------|------|-------------|------|
| Grafana | 3000 | admin/admin | 모니터링 대시보드 |
| Prometheus | 9090 | - | 메트릭 수집 |
| Jaeger | 16686 | - | 분산 추적 UI |
| Loki | 3100 | - | 로그 집계 |
| Tempo | 3200 | - | 추적 저장 |
| OpenSearch | 9200 | - | 검색 및 분석 |
| OpenSearch Dashboards | 5601 | - | 데이터 시각화 |
| MySQL | 3306 | root/1234 | 관계형 데이터베이스 |
| PostgreSQL | 5432 | - | 관계형 데이터베이스 (한국어 로케일) |
| RabbitMQ Management | 15672 | user/1234 | 메시지 브로커 UI |
| Portainer | 9000 | - | 컨테이너 관리 |
| Valkey (Redis) | 6379 | - | 인메모리 데이터베이스 |

## 데이터베이스 설정

### MySQL 사용자

```sql
-- 애플리케이션 사용자
CREATE USER 'user1'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON *.* TO 'user1'@'%';

-- 모니터링 익스포터
CREATE USER 'exporter'@'%' IDENTIFIED BY '1234qwer' WITH MAX_USER_CONNECTIONS 3;
GRANT ALL PRIVILEGES ON *.* TO 'exporter'@'%';

-- Keycloak 데이터베이스
CREATE DATABASE IF NOT EXISTS `keycloak`;
CREATE USER 'keycloak'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON keycloak.* TO 'keycloak'@'%';
FLUSH PRIVILEGES;
```

### PostgreSQL

- 한국어 로케일 지원 커스텀 이미지 (`jgkim999/postgres-ko:17.5`)
- 시간대: Asia/Seoul
- 데이터 체크섬 활성화
- `.env.postgres`에서 설정

## 텔레메트리 파이프라인

OpenTelemetry Collector가 텔레메트리 데이터를 처리합니다:

- **추적**: OTLP → Jaeger & Tempo
- **메트릭**: OTLP → Prometheus
- **로그**: OTLP → Loki

엔드포인트:

- OTLP gRPC: 포트 4317
- OTLP HTTP: 포트 4318

## 주요 설정 파일

- `docker-compose.yml`: 주요 서비스 정의
- `prometheus.yml`: Prometheus 스크래핑 설정
- `otel-collector.yaml`: OpenTelemetry 파이프라인 설정
- `loki.yaml`: Loki 로그 집계 설정
- `tempo.yml`: Tempo 추적 저장 설정
- `postgres/Dockerfile`: 한국어 로케일이 포함된 커스텀 PostgreSQL 이미지

## 데이터 영속성

모든 영구 데이터는 `${DATA_DIR}` 하위에 저장됩니다 (기본값: `~/docker-data`):

- 데이터베이스 데이터, 설정 파일 및 서비스별 데이터
- 로그, 메트릭 및 데이터베이스 저장을 위한 충분한 디스크 공간 확보
- 프로덕션 사용 시 정기적인 백업 권장

## 개발 노트

- 서비스는 특정 태그가 있는 최신 안정 버전 사용
- Tempo에 대한 리소스 제한 설정 (2 CPU, 4GB RAM)
- 모든 서비스에 자동 재시작 설정
- 적용 가능한 곳에 헬스 체크 구현
- Prometheus용 로테이션이 설정된 로깅
