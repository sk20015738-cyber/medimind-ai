# MediMind AI - Backend & Clinical AI Engine

MediMind AI의 백엔드 및 임상 의사결정 지원 AI 엔진입니다.
Python 3.14 표준 라이브러리만을 활용하여 **외부 의존성(zero-dependency)** 없이 즉시 실행 가능합니다.

---

## 📁 주요 구성 파일

| 파일 | 설명 |
| :--- | :--- |
| [`db.py`](file:///c:/Users/user/Desktop/홈페이지/backend/db.py) | SQLite3 데이터베이스 관리자 (`medications`, `schedules`, `intake_logs`, `user_profile` 테이블 정의 및 CRUD, 기본 시드 데이터) |
| [`dur_database.py`](file:///c:/Users/user/Desktop/홈페이지/backend/dur_database.py) | 한국 의약품 DUR(의약품안전사용서비스) 지식베이스 (성분 매핑, 성분/계열 중복 검사, 병용금기, 음식 상호작용, 시간생물학 복약 규칙) |
| [`ai_engine.py`](file:///c:/Users/user/Desktop/홈페이지/backend/ai_engine.py) | 처방전 자연어 파서(NLP), DUR 상호작용 분석기, 1/2 황금원칙 및 시니어 친화형 AI 복약 상담 엔진 |
| [`server.py`](file:///c:/Users/user/Desktop/홈페이지/backend/server.py) | 고성능 경량 REST API 서버 및 정적 프론트엔드 서빙 (`http.server` 기반, CORS 및 UTF-8 지원) |
| [`test_backend.py`](file:///c:/Users/user/Desktop/홈페이지/backend/test_backend.py) | 백엔드 전체 기능 및 임상 규칙에 대한 단위/통합 테스트 스위트 |

---

## 🚀 실행 방법

### 서버 구동
```bash
# 기본 8000 포트로 실행
python backend/server.py

# 포트 지정 실행 (예: 8080)
python backend/server.py 8080
```

서버가 실행되면:
- 브라우저에서 `http://localhost:8000` 접속 시 프론트엔드 자동 서빙
- REST API는 `http://localhost:8000/api/*`로 제공

### 테스트 실행
```bash
python backend/test_backend.py
```

---

## 📡 REST API 명세서

### 1. 복용 약물 관리 (Medications)
- `GET /api/medications`: 등록된 모든 약물 및 복용 스케줄 조회
- `GET /api/medications/<id>`: 특정 약물 상세 조회
- `POST /api/medications`: 신규 약물 등록 (등록 즉시 DUR 안전성 자동 분석)
  ```json
  {
    "name": "리피토정",
    "dosage": "10mg",
    "frequency": "1일 1회",
    "meal_timing": "취침 전",
    "category": "고지혈증약",
    "schedules": [
      { "time_slot": "저녁/취침전", "specific_time": "21:00", "is_active": 1 }
    ],
    "instructions": "자몽주스와 함께 드시지 마세요."
  }
  ```
- `DELETE /api/medications/<id>`: 약물 및 관련 스케줄/기록 삭제

### 2. 복약 기록 및 준수율 (Intake Logs)
- `GET /api/logs?days=7`: 7일간의 복약 준수율(%), 연속 복용일(Streak), 오늘 할 일 목록 반환
- `POST /api/logs`: 복약 상태 기록 (`taken`: 복용 완료, `skipped`: 건너뛰기, `snoozed`: 알림 연기)
  ```json
  {
    "medication_id": 1,
    "scheduled_date": "2026-09-10",
    "scheduled_time": "08:00",
    "status": "taken",
    "notes": "정시 복용 완료"
  }
  ```

### 3. AI 임상 지능 엔드포인트
- `POST /api/ai/parse-prescription`: 처방전 자연어/OCR 텍스트 자동 분석
  ```json
  {
    "text": "노바스크정 5mg 1일 1회 아침 식후 30분 30일분 처방"
  }
  ```
- `POST /api/ai/check-interactions`: 현재 약물 목록 DUR 병용금기, 중복 성분, 음식 상호작용 검사
- `POST /api/ai/chat`: AI 복약 상담 (1/2 골든룰, 음주 가이드, 부작용, 시니어 맞춤 상담)
  ```json
  {
    "message": "아침 혈압약을 깜빡했는데 지금 먹어도 될까요?"
  }
  ```
- `GET /api/report`: 종합 복약 리포트 (복약 순응도 통계 + 시간생물학적 점수 + AI 안전 조언)

### 4. 사용자 프로필 및 시스템
- `GET /api/profile`: 사용자 정보 및 시니어 모드 여부 조회
- `POST /api/profile`: 사용자 설정 업데이트
- `POST /api/seed-reset`: 데이터베이스 시드 데이터 초기화 (테스트용)
