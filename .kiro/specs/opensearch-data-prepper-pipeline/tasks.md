# Implementation Plan

- [x] 1. Data Prepper 환경 변수 파일 생성
  - `.env.data-prepper` 파일을 생성하여 Data Prepper 서비스의 환경 변수를 정의
  - JVM 힙 크기, 로그 레벨, 데이터 디렉토리 경로 등을 설정
  - _Requirements: 2.1, 2.2_

- [x] 2. Data Prepper 파이프라인 설정 파일 작성
  - `data-prepper.yaml` 파일을 생성하여 로그 처리 파이프라인을 정의
  - otel_logs_source, processors (date, mutate, grok), opensearch sink 설정
  - 헬스체크 및 메트릭 엔드포인트 활성화
  - _Requirements: 1.1, 1.2, 3.1, 3.2_

- [x] 3. OpenSearch 인덱스 템플릿 파일 생성
  - `opensearch-logs-template.json` 파일을 생성하여 로그 인덱스 매핑을 정의
  - 타임스탬프, 서비스 정보, 로그 레벨, 메시지 필드 매핑 설정
  - 동적 매핑 및 인덱스 라이프사이클 정책 구성
  - _Requirements: 3.3, 1.3_

- [x] 4. docker-compose.yml에 Data Prepper 서비스 추가
  - Data Prepper 컨테이너 정의를 docker-compose.yml에 추가
  - 포트 매핑 (21892, 4900, 9600), 볼륨 마운트, 의존성 설정
  - 헬스체크 및 재시작 정책 구성
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 5. otel-collector.yaml 설정 업데이트
  - Data Prepper로 로그를 전송하는 새로운 exporter 추가
  - 로그 파이프라인을 수정하여 Loki와 Data Prepper 모두에 전송하도록 설정
  - 배치 처리 및 재시도 정책 구성
  - _Requirements: 1.1, 5.1, 5.2_

- [x] 6. Prometheus 설정에 Data Prepper 메트릭 수집 추가
  - prometheus.yml에 Data Prepper 메트릭 스크래핑 job 추가
  - 메트릭 수집 간격 및 라벨 설정 구성
  - 서비스 디스커버리 설정 (필요시)
  - _Requirements: 4.1, 4.3_

- [x] 7. 통합 테스트 스크립트 작성
  - 엔드투엔드 로그 파이프라인 테스트를 위한 스크립트 생성
  - 테스트 로그 데이터 생성 및 전송 기능 구현
  - OpenSearch에서 로그 검색 및 검증 기능 구현
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 8. 모니터링 대시보드 설정 파일 생성
  - Grafana 대시보드 JSON 파일을 생성하여 Data Prepper 메트릭 시각화
  - 로그 처리량, 지연시간, 오류율 패널 구성
  - 알림 규칙 및 임계값 설정
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 9. 오류 처리 및 Dead Letter Queue 설정
  - Data Prepper 설정에 DLQ 경로 및 정책 추가
  - 재시도 메커니즘 및 백오프 전략 구성
  - 오류 로그 포맷 및 출력 설정 정의
  - _Requirements: 4.2_

- [x] 10. 문서화 및 운영 가이드 작성
  - README.md 업데이트하여 새로운 Data Prepper 파이프라인 설명 추가
  - 서비스 시작/중지 절차 및 트러블슈팅 가이드 작성
  - 로그 쿼리 예제 및 대시보드 사용법 문서화
  - _Requirements: 3.1, 3.2, 3.3_