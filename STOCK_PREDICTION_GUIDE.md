# MiroFish 주식 예측 서비스 - 설치 및 실행 가이드

## 개요

MiroFish의 멀티 에이전트 시뮬레이션 엔진을 활용하여 한국 주식(KOSPI/KOSDAQ)을 예측하는 서비스입니다.

### 작동 방식

1. **데이터 수집** — 네이버 금융 뉴스 + pykrx 재무 데이터
2. **지식 그래프 구축** — Zep Cloud를 통한 GraphRAG 구성
3. **에이전트 시뮬레이션** — 애널리스트, 투자자, 언론사 등 다양한 역할의 AI 에이전트가 시뮬레이션
4. **예측 보고서 생성** — 시뮬레이션 결과를 종합한 투자 예측 보고서

---

## 사전 요구사항

- **Python 3.11+**
- **Node.js 18+**
- **LLM API 키** (OpenAI, Alibaba Qwen 등 OpenAI SDK 호환 API)
- **Zep Cloud API 키** ([zep.ai](https://www.getzep.com/) 에서 발급)

---

## 1. 환경 설정

### .env 파일 생성

프로젝트 루트에 `.env` 파일을 만드세요:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```env
# LLM 설정 (OpenAI SDK 호환 API)
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# Zep Cloud 설정
ZEP_API_KEY=your_zep_api_key_here
```

**LLM 선택 가이드:**

| LLM | BASE_URL | MODEL_NAME | 비고 |
|-----|----------|------------|------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 가장 무난한 선택 |
| Alibaba Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 중국어 성능 우수, 저렴 |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 가성비 좋음 |

> 💡 **추천**: 한국어 주식 분석에는 **GPT-4o-mini** 또는 **DeepSeek**이 가성비가 좋습니다.

---

## 2. 설치

### 방법 A: npm 스크립트 (권장)

```bash
# 프론트엔드 + 백엔드 의존성 한번에 설치
npm run setup
npm run setup:backend
```

### 방법 B: 수동 설치

```bash
# 백엔드
cd backend
pip install -r requirements.txt

# 프론트엔드
cd ../frontend
npm install
```

### 주식 예측 추가 패키지 (자동 설치됨)

- `pykrx` — 한국거래소(KRX) 주가/재무 데이터
- `beautifulsoup4` — 네이버 금융 뉴스 파싱
- `requests` — HTTP 클라이언트

---

## 3. 실행

### 방법 A: 동시 실행 (권장)

```bash
npm run dev
```

백엔드(포트 5001)와 프론트엔드(포트 3000)가 동시에 실행됩니다.

### 방법 B: 개별 실행

```bash
# 터미널 1: 백엔드
npm run backend
# 또는: cd backend && uv run python run.py

# 터미널 2: 프론트엔드
npm run frontend
# 또는: cd frontend && npm run dev
```

### 방법 C: Docker

```bash
docker-compose up --build
```

---

## 4. 사용 방법

1. 브라우저에서 `http://localhost:3000/stock` 접속
2. **종목 검색** — 종목명 또는 종목코드를 검색 (예: "삼성전자" 또는 "005930")
3. **분석 시작** — 뉴스 수집 → 재무 데이터 수집 → 지식 그래프 구축 → 시뮬레이션 실행
4. **예측 보고서 확인** — 에이전트들의 합의 예측, 센티먼트 분석, 투자 의견 등

---

## 5. API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/stock/search?query=삼성` | 종목 검색 |
| POST | `/api/stock/analyze` | 종목 분석 시작 |
| GET | `/api/stock/analyze/<task_id>/status` | 분석 진행 상태 |
| POST | `/api/stock/simulate` | 시뮬레이션 시작 |
| GET | `/api/stock/simulate/<sim_id>/status` | 시뮬레이션 상태 |
| POST | `/api/stock/report/<sim_id>` | 보고서 생성 |
| GET | `/api/stock/report/<report_id>` | 보고서 조회 |

---

## 6. 프로젝트 구조 (추가된 파일)

```
MiroFish/
├── backend/app/
│   ├── api/
│   │   └── stock.py                    # 주식 예측 API 엔드포인트
│   └── services/
│       ├── stock_data_collector.py      # 뉴스/재무 데이터 수집
│       ├── stock_ontology.py            # 주식 시장 온톨로지
│       ├── stock_simulation_config.py   # 시뮬레이션 설정 생성
│       └── stock_report_agent.py        # 예측 보고서 생성
├── frontend/src/
│   ├── api/
│   │   └── stock.js                    # 주식 API 클라이언트
│   └── views/
│       └── StockPrediction.vue         # 주식 예측 UI
└── STOCK_PREDICTION_GUIDE.md           # 이 가이드
```

---

## 7. 커스터마이징

### 시뮬레이션 에이전트 역할

`stock_ontology.py`에서 에이전트 타입을 수정할 수 있습니다:

- **Analyst** — 증권사 애널리스트
- **Investor** — 개인/기관 투자자
- **CompanyExecutive** — 기업 임원
- **Regulator** — 금융감독원 등
- **MediaOutlet** — 경제 언론사
- **ForeignInvestor** — 외국인 투자자
- **MarketMaker** — 시장조성자
- **IndustryExpert** — 산업 전문가

### 감성 분석 키워드

`stock_data_collector.py`의 `POSITIVE_KEYWORDS`, `NEGATIVE_KEYWORDS`를 수정하여 감성 분석 정확도를 높일 수 있습니다.

### 시뮬레이션 라운드 수

`stock_simulation_config.py`에서 시뮬레이션 라운드 수와 에이전트 수를 조정할 수 있습니다.

---

## ⚠️ 면책 조항

> **본 서비스는 AI 시뮬레이션 기반 실험적 프로젝트이며, 실제 투자 조언이 아닙니다.**
> 
> - 시뮬레이션 결과는 참고용이며 투자 판단의 근거가 될 수 없습니다.
> - 모든 투자 결정은 본인의 책임 하에 이루어져야 합니다.
> - 과거 데이터 기반 분석이므로 미래 수익을 보장하지 않습니다.

---

## 라이선스

AGPL-3.0 (원본 MiroFish 라이선스 준수)
