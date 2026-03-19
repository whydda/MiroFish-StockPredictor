<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

# MiroFish 주식 예측 서비스

**AI 멀티 에이전트 시뮬레이션 기반 한국 주식(KOSPI/KOSDAQ) 예측 엔진**

[![Based on MiroFish](https://img.shields.io/badge/Based_on-MiroFish-DAA520?style=flat-square)](https://github.com/666ghj/MiroFish)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)
[![License](https://img.shields.io/badge/License-AGPL_3.0-blue?style=flat-square)](./LICENSE)

</div>

---

## 개요

[MiroFish](https://github.com/666ghj/MiroFish)의 멀티 에이전트 시뮬레이션 엔진을 활용하여 **한국 주식 시장을 예측**하는 서비스입니다.

뉴스, 재무 데이터, 시장 센티먼트를 수집한 뒤, 애널리스트·투자자·외국인·언론사 등 다양한 역할의 AI 에이전트가 시뮬레이션을 수행하고, 그 결과를 종합한 **예측 보고서**를 생성합니다.

### 작동 방식

```
종목 선택 → 데이터 수집 → 지식 그래프 구축 → 에이전트 시뮬레이션 → 예측 보고서
```

| 단계 | 설명 | 기술 |
|------|------|------|
| **데이터 수집** | 네이버 금융 뉴스 + KRX 재무 데이터 | BeautifulSoup, pykrx |
| **지식 그래프** | 수집 데이터 기반 GraphRAG 구성 | Zep Cloud |
| **시뮬레이션** | 10종 에이전트가 투자 의사결정 시뮬레이션 | OASIS + LLM |
| **보고서 생성** | 시뮬레이션 합의 기반 예측 보고서 | LLM (GPT, DeepSeek 등) |

---

## 시뮬레이션 에이전트

시뮬레이션에 참여하는 AI 에이전트 역할:

| 에이전트 | 역할 | 행동 패턴 |
|----------|------|-----------|
| **Analyst** | 증권사 애널리스트 | 기술적·기본적 분석 기반 의견 제시 |
| **Investor** | 개인/기관 투자자 | 뉴스와 분석에 반응하여 매수/매도 결정 |
| **ForeignInvestor** | 외국인 투자자 | 글로벌 시각, 대형주 중심 판단 |
| **CompanyExecutive** | 기업 임원 | 내부자 관점의 기업 가치 평가 |
| **Regulator** | 금융감독원 등 | 규제 리스크 평가 |
| **MediaOutlet** | 경제 언론사 | 뉴스 생산 및 여론 형성 |
| **MarketMaker** | 시장조성자 | 유동성 및 수급 분석 |
| **IndustryExpert** | 산업 전문가 | 섹터별 전문 분석 |

---

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- LLM API 키 (OpenAI, DeepSeek 등 OpenAI SDK 호환)
- Zep Cloud API 키 ([getzep.com](https://www.getzep.com/))

### 1. 클론 및 설치

```bash
git clone https://github.com/whydda/MiroFish-StockPredictor.git
cd MiroFish-StockPredictor

# 의존성 설치
npm run setup
npm run setup:backend
```

### 2. 환경 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하세요:

```env
# LLM 설정
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# Zep Cloud 설정
ZEP_API_KEY=your_zep_api_key_here
```

<details>
<summary><b>LLM 선택 가이드</b></summary>

| LLM | BASE_URL | MODEL_NAME | 특징 |
|-----|----------|------------|------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 안정적, 범용 |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 가성비 우수 |
| Alibaba Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 저렴 |

</details>

### 3. 실행

```bash
# 백엔드(5001) + 프론트엔드(3000) 동시 실행
npm run dev
```

브라우저에서 **http://localhost:3000/stock** 접속

### Docker로 실행

```bash
docker-compose up --build
```

---

## 사용 방법

1. `/stock` 페이지에서 **종목 검색** (예: "삼성전자", "005930")
2. 종목을 선택하고 **분석 시작** 클릭
3. 자동으로 뉴스 수집 → 재무 분석 → 그래프 구축 → 시뮬레이션 진행
4. 완료 후 **예측 보고서** 확인 (상승/하락/보합 확률, 투자 의견 등)

---

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/stock/search?query=삼성` | 종목 검색 |
| `POST` | `/api/stock/analyze` | 종목 분석 시작 |
| `GET` | `/api/stock/analyze/:taskId/status` | 분석 진행 상태 |
| `POST` | `/api/stock/simulate` | 시뮬레이션 시작 |
| `GET` | `/api/stock/simulate/:simId/status` | 시뮬레이션 상태 |
| `POST` | `/api/stock/report/:simId` | 보고서 생성 |
| `GET` | `/api/stock/report/:reportId` | 보고서 조회 |

---

## 프로젝트 구조

```
MiroFish-StockPredictor/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── stock.py                      # 주식 예측 API
│       │   ├── graph.py                      # 그래프 API (원본)
│       │   ├── simulation.py                 # 시뮬레이션 API (원본)
│       │   └── report.py                     # 보고서 API (원본)
│       ├── services/
│       │   ├── stock_data_collector.py        # 뉴스/재무 데이터 수집
│       │   ├── stock_ontology.py              # 주식 시장 온톨로지
│       │   ├── stock_simulation_config.py     # 시뮬레이션 설정 생성
│       │   ├── stock_report_agent.py          # 예측 보고서 생성
│       │   ├── graph_builder.py               # 그래프 빌더 (원본)
│       │   ├── simulation_runner.py           # 시뮬레이션 러너 (원본)
│       │   └── report_agent.py                # 보고서 에이전트 (원본)
│       ├── utils/
│       │   ├── llm_client.py                  # LLM 클라이언트
│       │   └── ...
│       └── config.py                          # 설정 관리
├── frontend/
│   └── src/
│       ├── views/
│       │   └── StockPrediction.vue            # 주식 예측 UI
│       ├── api/
│       │   └── stock.js                       # API 클라이언트
│       └── router/
│           └── index.js                       # 라우팅
├── .env.example
├── docker-compose.yml
├── STOCK_PREDICTION_GUIDE.md                  # 상세 실행 가이드
└── README.md
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| **백엔드** | Python 3.11, Flask, OpenAI SDK |
| **프론트엔드** | Vue 3, Vite |
| **데이터 수집** | pykrx (KRX), BeautifulSoup (네이버 금융) |
| **시뮬레이션 엔진** | [OASIS](https://github.com/camel-ai/oasis) (CAMEL-AI) |
| **지식 그래프** | [Zep Cloud](https://www.getzep.com/) |
| **LLM** | OpenAI, DeepSeek, Qwen 등 (OpenAI SDK 호환) |
| **배포** | Docker, docker-compose |

---

## 커스터마이징

- **에이전트 역할 수정**: `stock_ontology.py`에서 에이전트 타입과 속성 변경
- **감성 분석 키워드**: `stock_data_collector.py`의 `POSITIVE_KEYWORDS` / `NEGATIVE_KEYWORDS` 확장
- **시뮬레이션 설정**: `stock_simulation_config.py`에서 라운드 수, 에이전트 수, 활동 패턴 조정
- **보고서 구조**: `stock_report_agent.py`에서 보고서 섹션 및 프롬프트 수정

---

## 향후 계획

- [ ] 실시간 주가 차트 연동 (TradingView 위젯)
- [ ] 뉴스 소스 확장 (한경, 매경, 연합뉴스 등)
- [ ] 시뮬레이션 백테스팅 기능
- [ ] 다중 종목 포트폴리오 분석
- [ ] 시뮬레이션 결과 시각화 개선

---

## ⚠️ 면책 조항

> **본 서비스는 AI 시뮬레이션 기반 실험적 프로젝트이며, 실제 투자 조언이 아닙니다.**
>
> - 시뮬레이션 결과는 참고용이며 투자 판단의 근거가 될 수 없습니다.
> - 모든 투자 결정은 본인의 책임 하에 이루어져야 합니다.
> - 과거 데이터 기반 분석이므로 미래 수익을 보장하지 않습니다.

---

## 감사

- [MiroFish](https://github.com/666ghj/MiroFish) — 원본 멀티 에이전트 시뮬레이션 엔진
- [OASIS](https://github.com/camel-ai/oasis) — 소셜 시뮬레이션 프레임워크 (CAMEL-AI)
- [Zep](https://www.getzep.com/) — 지식 그래프 메모리
- [pykrx](https://github.com/sharebook-kr/pykrx) — 한국거래소 데이터

## 라이선스

[AGPL-3.0](./LICENSE) — 원본 MiroFish 라이선스 준수
