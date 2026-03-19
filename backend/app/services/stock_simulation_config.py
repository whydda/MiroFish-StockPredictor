"""
주식 시장 시뮬레이션 설정 생성기

MiroFish의 SimulationConfigGenerator 패턴을 참고하여,
KOSPI/KOSDAQ 주식 시장 시뮬레이션에 특화된 설정을 생성한다.

주요 기능:
  - 주식 에이전트별 행동 패턴 설정 (투자자 성향, 반응 속도 등)
  - 한국 주식 시장 시간대 기반 활동 패턴 (09:00~15:30 장중 활성)
  - 뉴스 이벤트에 따른 에이전트 반응 시뮬레이션
  - MiroFish 기존 데이터클래스 및 Config 패턴 재활용
"""

import json
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..config import Config

logger = logging.getLogger('mirofish.stock_simulation_config')


# ============================================================
# 한국 주식 시장 시간대 상수
# ============================================================

# 정규 장: 09:00 ~ 15:30 (KST)
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 15

# 시간대별 활동 계수 (한국 주식 투자자 기준)
STOCK_ACTIVITY_MULTIPLIERS: Dict[str, float] = {
    "pre_market":   0.3,   # 08:00~08:59 장전 시간외
    "market_open":  1.5,   # 09:00~09:59 장 시작 (변동성 최대)
    "mid_morning":  1.0,   # 10:00~11:59 오전 장중
    "lunch":        0.6,   # 12:00~12:59 점심 시간 (거래 감소)
    "afternoon":    1.1,   # 13:00~15:29 오후 장중
    "close_rush":   1.4,   # 15:00~15:29 장 마감 전 (호가 집중)
    "after_market": 0.8,   # 15:30~17:59 장후 시간외 / 실적 발표
    "evening":      0.5,   # 18:00~22:59 미국 장 개장 전 분석
    "night":        0.2,   # 23:00~07:59 심야 및 새벽 (저활동)
}

# 에이전트 타입별 기본 활동 시간대
AGENT_ACTIVE_HOURS: Dict[str, List[int]] = {
    "Analyst":         list(range(8, 18)),           # 업무 시간 + 장전/장후 분석
    "Investor":        list(range(8, 16)) + [19, 20, 21],  # 장중 + 저녁 뉴스 확인
    "CompanyExecutive": list(range(9, 18)),          # 업무 시간
    "Regulator":       list(range(9, 17)),           # 공공기관 업무 시간
    "MediaOutlet":     list(range(7, 23)),           # 기사 작성 시간 (새벽~밤)
    "ForeignInvestor": list(range(8, 17)) + [22, 23],  # 한국 시장 + 미국 개장 시간
    "MarketMaker":     list(range(8, 16)),           # 장 운영 시간
    "IndustryExpert":  list(range(9, 22)),           # 강연·인터뷰 포함
    "Person":          list(range(9, 16)) + [19, 20, 21, 22],  # 장중 + 저녁
    "Organization":    list(range(9, 18)),           # 업무 시간
}

# 에이전트 타입별 영향력 가중치
AGENT_INFLUENCE_WEIGHTS: Dict[str, float] = {
    "Analyst":          2.5,   # 리포트가 시장 여론에 큰 영향
    "Investor":         1.0,   # 일반 개인투자자
    "CompanyExecutive": 3.0,   # IR·공시 발표로 강한 영향
    "Regulator":        3.5,   # 규제 발표가 즉각 주가에 반영
    "MediaOutlet":      2.0,   # 뉴스 보도 영향
    "ForeignInvestor":  2.8,   # 외국인 수급은 주가 방향성에 영향
    "MarketMaker":      1.5,   # 유동성 제공자
    "IndustryExpert":   1.8,   # 산업 전망 발언 영향
    "Person":           0.8,   # 개인 커뮤니티 의견
    "Organization":     1.2,   # 협회·단체 의견
}

# 에이전트 타입별 반응 속도 (분, 최소~최대)
AGENT_RESPONSE_DELAYS: Dict[str, tuple] = {
    "Analyst":          (30, 120),   # 분석 보고서 작성 시간 필요
    "Investor":         (1, 10),     # 즉각적 매수/매도 반응
    "CompanyExecutive": (60, 480),   # 공시·IR 준비 시간
    "Regulator":        (120, 720),  # 규제 검토 및 발표 준비
    "MediaOutlet":      (5, 30),     # 빠른 기사 발행
    "ForeignInvestor":  (15, 60),    # 글로벌 정보 분석 후 대응
    "MarketMaker":      (1, 5),      # 즉각적 호가 조정
    "IndustryExpert":   (60, 240),   # 논문/보고서 작성 시간
    "Person":           (1, 15),     # SNS 즉각 반응
    "Organization":     (60, 360),   # 공식 성명 준비
}


# ============================================================
# 데이터클래스 정의
# ============================================================

@dataclass
class StockAgentConfig:
    """
    주식 시뮬레이션 에이전트 개별 설정

    MiroFish의 AgentActivityConfig와 동일한 구조이나
    주식 투자 맥락에 맞게 필드를 확장한다.
    """
    # 기본 식별자
    agent_id: int
    entity_name: str         # 에이전트 이름 (예: "미래에셋 반도체 애널리스트")
    entity_type: str         # 온톨로지 엔티티 타입
    entity_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ---- 활동 패턴 ----
    activity_level: float = 0.5       # 전체 활성도 (0.0~1.0)
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 16)))

    # ---- 발언/거래 빈도 ----
    posts_per_hour: float = 0.5       # 시간당 발언(포스트) 횟수
    comments_per_hour: float = 1.0    # 시간당 댓글/반응 횟수

    # ---- 반응 속도 ----
    response_delay_min: int = 5       # 최소 반응 지연 (분)
    response_delay_max: int = 60      # 최대 반응 지연 (분)

    # ---- 투자 성향 ----
    investment_stance: str = "neutral"  # buy / sell / hold / neutral / observer
    risk_appetite: str = "moderate"     # aggressive / moderate / conservative
    sentiment_bias: float = 0.0         # -1.0(극단 부정) ~ 1.0(극단 긍정)

    # ---- 영향력 ----
    influence_weight: float = 1.0     # 다른 에이전트에 미치는 영향력

    # ---- 정보 접근성 ----
    information_access: str = "public"  # public / insider / premium


@dataclass
class StockMarketTimeConfig:
    """
    주식 시장 시뮬레이션 시간 설정

    한국 주식 시장의 정규 거래 시간(09:00~15:30)과
    투자자 활동 패턴을 반영한 시간 구성
    """
    # 시뮬레이션 총 기간 (시간 단위)
    # 기본값: 72시간 = 3거래일 (단기 뉴스 이벤트 시뮬레이션)
    total_simulation_hours: int = 72

    # 1라운드 = 실제 시장 몇 분에 해당하는지
    # 기본값: 30분 → 1거래일(6.5시간) = 13라운드
    minutes_per_round: int = 30

    # 시간당 활성화되는 에이전트 수 범위
    agents_per_hour_min: int = 3
    agents_per_hour_max: int = 20

    # 장중 고활동 시간대
    peak_hours: List[int] = field(
        default_factory=lambda: [9, 14, 15]
    )
    peak_activity_multiplier: float = 1.5

    # 장외 저활동 시간대
    off_peak_hours: List[int] = field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5, 6, 7]
    )
    off_peak_activity_multiplier: float = 0.1

    # 장 시작 전 (오전 준비 시간)
    morning_hours: List[int] = field(default_factory=lambda: [8])
    morning_activity_multiplier: float = 0.3

    # 정규 장중 시간
    market_hours: List[int] = field(
        default_factory=lambda: list(range(9, 16))
    )
    market_activity_multiplier: float = 1.0


@dataclass
class StockEventConfig:
    """
    주식 시뮬레이션 이벤트 설정

    시뮬레이션 초기에 투입되는 뉴스/이벤트와
    에이전트들이 반응해야 할 핵심 이슈 정의
    """
    # 초기 뉴스 이벤트 (에이전트들의 반응 트리거)
    initial_news_events: List[Dict[str, Any]] = field(default_factory=list)

    # 정기 이벤트 (특정 시뮬레이션 라운드에서 발생)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)

    # 시뮬레이션 핵심 키워드 (에이전트들이 집중하는 주제)
    hot_topics: List[str] = field(default_factory=list)

    # 시장 분위기 방향 (시뮬레이션 목표 시나리오)
    market_narrative: str = ""

    # 대상 종목 정보
    target_ticker: str = ""
    target_company: str = ""


@dataclass
class StockSimulationParameters:
    """
    주식 시뮬레이션 전체 설정 컨테이너

    MiroFish의 SimulationParameters 패턴을 따르며
    주식 시장 특화 필드를 추가한다.
    """
    # 기본 식별자
    simulation_id: str
    ticker: str
    company_name: str
    sector: str
    simulation_requirement: str

    # 하위 설정
    time_config: StockMarketTimeConfig = field(
        default_factory=StockMarketTimeConfig
    )
    agent_configs: List[StockAgentConfig] = field(default_factory=list)
    event_config: StockEventConfig = field(default_factory=StockEventConfig)

    # LLM 설정
    llm_model: str = field(default_factory=lambda: Config.LLM_MODEL_NAME or "gpt-4o-mini")
    llm_base_url: str = field(default_factory=lambda: Config.LLM_BASE_URL or "")

    # 메타데이터
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    generation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 직렬화"""
        return {
            "simulation_id": self.simulation_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "simulation_requirement": self.simulation_requirement,
            "time_config": asdict(self.time_config),
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_notes": self.generation_notes,
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열로 직렬화 (한국어 유지)"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ============================================================
# 시뮬레이션 설정 생성기
# ============================================================

class StockSimulationConfigGenerator:
    """
    주식 시장 시뮬레이션 설정 생성기

    MiroFish의 SimulationConfigGenerator와 동일한 인터페이스를 유지하면서
    주식 시장 도메인에 맞게 커스터마이징된다.

    에이전트 설정 생성 전략:
      1. 에이전트 타입별 기본값(규칙 기반)으로 초기 설정 생성
      2. 수집된 뉴스 데이터와 감성 분석 결과를 반영하여 투자 성향 조정
      3. 종목 섹터에 따라 전문 에이전트(IndustryExpert) 비중 조정
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Args:
            api_key:    LLM API 키 (미입력 시 Config에서 로드)
            base_url:   LLM API Base URL
            model_name: 사용할 LLM 모델명
        """
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME

    # ----------------------------------------------------------
    # 메인 진입점
    # ----------------------------------------------------------

    def generate_config(
        self,
        ticker: str,
        company_name: str,
        sector: str,
        simulation_requirement: str,
        simulation_input_text: str,
        sentiment_data: Optional[Dict[str, Any]] = None,
        financial_data: Optional[Dict[str, Any]] = None,
        num_agents: int = 20,
    ) -> StockSimulationParameters:
        """
        주식 시뮬레이션 전체 설정을 생성한다.

        Args:
            ticker:                종목 코드 (예: "005930")
            company_name:          기업명 (예: "삼성전자")
            sector:                산업 섹터 (예: "반도체")
            simulation_requirement: 시뮬레이션 목적/요구사항 기술
            simulation_input_text: StockDataCollector.prepare_simulation_input() 결과
            sentiment_data:        StockDataCollector.collect_market_sentiment() 결과
            financial_data:        StockDataCollector.collect_financial_data() 결과
            num_agents:            생성할 에이전트 수 (기본값: 20)

        Returns:
            StockSimulationParameters: 완성된 시뮬레이션 설정
        """
        simulation_id = f"stock_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(
            f"주식 시뮬레이션 설정 생성 시작: ticker={ticker}, "
            f"company={company_name}, sector={sector}, "
            f"agents={num_agents}"
        )

        # ---- 1. 시간 설정 생성 ----
        time_config = self._generate_time_config(num_agents)
        logger.info("시간 설정 생성 완료")

        # ---- 2. 이벤트 설정 생성 ----
        event_config = self._generate_event_config(
            ticker=ticker,
            company_name=company_name,
            simulation_input_text=simulation_input_text,
            sentiment_data=sentiment_data,
            financial_data=financial_data,
        )
        logger.info("이벤트 설정 생성 완료")

        # ---- 3. 에이전트 설정 생성 ----
        agent_configs = self._generate_agent_configs(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            num_agents=num_agents,
            sentiment_data=sentiment_data,
        )
        logger.info(f"에이전트 설정 생성 완료: {len(agent_configs)}개")

        # ---- 4. 최종 파라미터 조립 ----
        params = StockSimulationParameters(
            simulation_id=simulation_id,
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=agent_configs,
            event_config=event_config,
            llm_model=self.model_name or "",
            llm_base_url=self.base_url or "",
            generation_notes=(
                f"자동 생성 시뮬레이션 설정 | "
                f"에이전트 {len(agent_configs)}개 | "
                f"섹터: {sector}"
            ),
        )

        logger.info(
            f"주식 시뮬레이션 설정 생성 완료: simulation_id={simulation_id}"
        )
        return params

    # ----------------------------------------------------------
    # 시간 설정 생성
    # ----------------------------------------------------------

    def _generate_time_config(self, num_agents: int) -> StockMarketTimeConfig:
        """
        에이전트 수를 고려한 주식 시장 시간 설정 생성

        한국 주식 시장 특성:
          - 정규 장: 09:00~15:30 → 가장 활동적인 시간대
          - 1라운드 = 30분 (장중 세밀한 시뮬레이션)
          - 총 72시간 (약 3거래일) 시뮬레이션
        """
        # 에이전트 수에 비례하는 시간당 활성 에이전트 수 계산
        agents_min = max(2, num_agents // 10)
        agents_max = max(agents_min + 1, num_agents // 3)

        return StockMarketTimeConfig(
            total_simulation_hours=72,
            minutes_per_round=30,
            agents_per_hour_min=agents_min,
            agents_per_hour_max=agents_max,
            # 장 시작(09:00)과 마감 직전(14:00~15:00)이 가장 활발
            peak_hours=[9, 14, 15],
            peak_activity_multiplier=1.5,
            # 새벽~아침 개장 전은 거의 비활성
            off_peak_hours=list(range(0, 8)),
            off_peak_activity_multiplier=0.1,
            morning_hours=[8],
            morning_activity_multiplier=0.3,
            market_hours=list(range(9, 16)),
            market_activity_multiplier=1.0,
        )

    # ----------------------------------------------------------
    # 이벤트 설정 생성
    # ----------------------------------------------------------

    def _generate_event_config(
        self,
        ticker: str,
        company_name: str,
        simulation_input_text: str,
        sentiment_data: Optional[Dict[str, Any]],
        financial_data: Optional[Dict[str, Any]],
    ) -> StockEventConfig:
        """
        뉴스/재무 데이터를 바탕으로 초기 이벤트와 핵심 주제를 설정한다.

        초기 뉴스 이벤트는 각 에이전트 타입이 시뮬레이션 시작 시
        어떤 정보에 반응하는지 결정하는 트리거 역할을 한다.
        """
        hot_topics: List[str] = [company_name, ticker]
        initial_events: List[Dict[str, Any]] = []
        market_narrative = ""

        # 감성 데이터가 있으면 키워드 추출
        if sentiment_data:
            hot_topics.extend(sentiment_data.get("top_positive_words", []))
            hot_topics.extend(sentiment_data.get("top_negative_words", []))

            overall = sentiment_data.get("overall_sentiment", "neutral")
            score = sentiment_data.get("sentiment_score", 0.0)

            if overall == "positive":
                market_narrative = (
                    f"{company_name}에 대한 시장 분위기가 긍정적입니다 "
                    f"(감성 점수: {score:.2f}). "
                    "애널리스트들은 매수 의견을 강화하고, "
                    "개인투자자들의 관심이 높아지고 있습니다."
                )
                initial_events.append(
                    self._make_news_event(
                        content=(
                            f"{company_name} 주가 상승 모멘텀 지속. "
                            f"주요 긍정 요인: "
                            f"{', '.join(sentiment_data.get('top_positive_words', [])[:3])}"
                        ),
                        poster_type="MediaOutlet",
                    )
                )

            elif overall == "negative":
                market_narrative = (
                    f"{company_name}에 대한 시장 우려가 높습니다 "
                    f"(감성 점수: {score:.2f}). "
                    "일부 기관투자자들이 비중을 축소하고, "
                    "외국인 매도세가 관찰되고 있습니다."
                )
                initial_events.append(
                    self._make_news_event(
                        content=(
                            f"{company_name} 단기 조정 가능성 제기. "
                            f"주요 부정 요인: "
                            f"{', '.join(sentiment_data.get('top_negative_words', [])[:3])}"
                        ),
                        poster_type="Analyst",
                    )
                )

            else:
                market_narrative = (
                    f"{company_name}에 대한 시장 의견이 엇갈리고 있습니다. "
                    "방향성 탐색 구간에서 에이전트들의 정보 분석이 활발합니다."
                )

        # 재무 데이터가 있으면 주가 변동 이벤트 추가
        if financial_data and financial_data.get("price_change") is not None:
            price_change = financial_data["price_change"]
            current_price = financial_data.get("current_price", 0)

            if abs(price_change) >= 3.0:
                direction = "급등" if price_change > 0 else "급락"
                initial_events.append(
                    self._make_news_event(
                        content=(
                            f"{company_name} 주가 {direction} "
                            f"({price_change:+.2f}%). "
                            f"현재가: {current_price:,.0f}원. "
                            "투자자들의 즉각적인 반응이 예상됩니다."
                        ),
                        poster_type="MediaOutlet",
                    )
                )
                hot_topics.append(direction)

        # 중복 제거
        seen = set()
        unique_topics = []
        for t in hot_topics:
            if t and t not in seen:
                seen.add(t)
                unique_topics.append(t)

        return StockEventConfig(
            initial_news_events=initial_events,
            scheduled_events=[],
            hot_topics=unique_topics[:10],  # 최대 10개
            market_narrative=market_narrative,
            target_ticker=ticker,
            target_company=company_name,
        )

    @staticmethod
    def _make_news_event(
        content: str,
        poster_type: str,
        round_offset: int = 0,
    ) -> Dict[str, Any]:
        """뉴스 이벤트 딕셔너리를 생성한다."""
        return {
            "content": content,
            "poster_type": poster_type,
            "round": round_offset,  # 0 = 시뮬레이션 시작 시 즉시 발행
        }

    # ----------------------------------------------------------
    # 에이전트 설정 생성
    # ----------------------------------------------------------

    def _generate_agent_configs(
        self,
        ticker: str,
        company_name: str,
        sector: str,
        num_agents: int,
        sentiment_data: Optional[Dict[str, Any]],
    ) -> List[StockAgentConfig]:
        """
        종목 특성과 시장 감성에 맞는 에이전트 목록을 생성한다.

        에이전트 구성 비율 (기본값):
          - Investor (개인투자자):     30% → 즉각 반응, 낮은 영향력
          - Analyst (애널리스트):      15% → 리포트 기반, 높은 영향력
          - MediaOutlet (언론):        10% → 빠른 보도, 높은 전파력
          - ForeignInvestor (외국인):  10% → 대규모 수급, 높은 영향력
          - MarketMaker (시장조성자):   5% → 유동성 공급
          - IndustryExpert (산업전문가): 10% → 섹터 분석
          - CompanyExecutive (임원):    5% → IR/공시
          - Regulator (규제기관):       5% → 모니터링
          - Person (일반인):           10% → SNS 참여
        """
        # 전체 감성 점수 (에이전트 성향 bias 조정에 사용)
        global_sentiment_score = 0.0
        if sentiment_data:
            global_sentiment_score = float(
                sentiment_data.get("sentiment_score", 0.0)
            )

        # 에이전트 타입별 배분 계산
        agent_distribution = self._compute_agent_distribution(num_agents)

        configs: List[StockAgentConfig] = []
        agent_id = 0

        for entity_type, count in agent_distribution.items():
            for i in range(count):
                config = self._build_agent_config(
                    agent_id=agent_id,
                    entity_type=entity_type,
                    index=i,
                    company_name=company_name,
                    sector=sector,
                    global_sentiment_score=global_sentiment_score,
                )
                configs.append(config)
                agent_id += 1

        logger.info(
            f"에이전트 배분: "
            + ", ".join(f"{k}={v}" for k, v in agent_distribution.items())
        )
        return configs

    @staticmethod
    def _compute_agent_distribution(num_agents: int) -> Dict[str, int]:
        """
        전체 에이전트 수를 타입별로 배분한다.

        소수점은 반올림하여 합계가 num_agents에 최대한 근접하도록 조정한다.
        """
        # 타입별 비율 (합계 = 1.0)
        ratios = {
            "Investor":          0.30,
            "Analyst":           0.15,
            "MediaOutlet":       0.10,
            "ForeignInvestor":   0.10,
            "IndustryExpert":    0.10,
            "Person":            0.10,
            "MarketMaker":       0.05,
            "CompanyExecutive":  0.05,
            "Regulator":         0.03,
            "Organization":      0.02,
        }

        distribution: Dict[str, int] = {}

        sorted_types = sorted(ratios.items(), key=lambda x: x[1], reverse=True)

        # 1단계: 각 타입에 비율 기반 초기 할당량 (0으로 시작, floor 적용)
        for etype, ratio in sorted_types:
            distribution[etype] = int(num_agents * ratio)

        # 2단계: 현재 합계와 목표의 차이 조정 (남은 슬롯은 비율 높은 순서로 배분)
        current_total = sum(distribution.values())
        diff = num_agents - current_total

        # 부족분: 비율이 높은 타입부터 1씩 추가
        if diff > 0:
            for etype, _ in sorted_types:
                if diff <= 0:
                    break
                distribution[etype] += 1
                diff -= 1

        # 초과분: 비율이 낮은 타입부터 1씩 제거 (단, 0 이하로는 내리지 않음)
        elif diff < 0:
            for etype, _ in reversed(sorted_types):
                if diff >= 0:
                    break
                if distribution[etype] > 0:
                    distribution[etype] -= 1
                    diff += 1

        # 3단계: 할당량이 0인 타입 제거 (에이전트가 없는 타입은 불필요)
        distribution = {k: v for k, v in distribution.items() if v > 0}

        return distribution

    def _build_agent_config(
        self,
        agent_id: int,
        entity_type: str,
        index: int,
        company_name: str,
        sector: str,
        global_sentiment_score: float,
    ) -> StockAgentConfig:
        """
        단일 에이전트 설정을 규칙 기반으로 생성한다.

        전역 감성 점수(global_sentiment_score)를 통해
        시장 분위기가 긍정적일 때 매수 성향 에이전트 비중을 높인다.
        """
        # 반응 지연 설정
        delay_min, delay_max = AGENT_RESPONSE_DELAYS.get(entity_type, (5, 60))

        # 활성 시간대
        active_hours = AGENT_ACTIVE_HOURS.get(entity_type, list(range(9, 16)))

        # 영향력 가중치
        influence = AGENT_INFLUENCE_WEIGHTS.get(entity_type, 1.0)

        # 에이전트 이름 생성
        entity_name = self._generate_agent_name(entity_type, index, company_name, sector)

        # 투자 성향 결정 (타입 + 감성 점수 기반)
        investment_stance, sentiment_bias = self._determine_stance(
            entity_type=entity_type,
            index=index,
            global_sentiment_score=global_sentiment_score,
        )

        # 활동 수준 및 발언 빈도 (타입별 기본값)
        activity_level, posts_ph, comments_ph = self._get_activity_params(entity_type)

        return StockAgentConfig(
            agent_id=agent_id,
            entity_name=entity_name,
            entity_type=entity_type,
            activity_level=activity_level,
            active_hours=active_hours,
            posts_per_hour=posts_ph,
            comments_per_hour=comments_ph,
            response_delay_min=delay_min,
            response_delay_max=delay_max,
            investment_stance=investment_stance,
            risk_appetite=self._get_risk_appetite(entity_type),
            sentiment_bias=round(sentiment_bias, 2),
            influence_weight=influence,
            information_access=self._get_info_access(entity_type),
        )

    @staticmethod
    def _generate_agent_name(
        entity_type: str,
        index: int,
        company_name: str,
        sector: str,
    ) -> str:
        """에이전트 타입과 인덱스를 기반으로 사람이 읽을 수 있는 이름을 생성한다."""
        name_templates: Dict[str, List[str]] = {
            "Analyst": [
                f"미래에셋 {sector} 담당 애널리스트",
                f"삼성증권 {company_name} 리서치 애널리스트",
                f"NH투자증권 {sector} 섹터 분석가",
                f"키움증권 {company_name} 기업 분석가",
                f"한국투자증권 {sector} 전담 애널리스트",
            ],
            "Investor": [
                f"{company_name} 주주 개인투자자 {index+1}",
                f"{sector} 섹터 집중 투자자 {index+1}",
                f"국내 주식 가치투자자 {index+1}",
            ],
            "CompanyExecutive": [
                f"{company_name} CEO",
                f"{company_name} CFO",
                f"{company_name} IR 담당 임원",
            ],
            "Regulator": [
                "금융감독원 증권감독국",
                "금융위원회 자본시장과",
                "한국은행 금융안정국",
            ],
            "MediaOutlet": [
                "한국경제신문 증권팀",
                "매일경제 시장부",
                "조선비즈 주식팀",
                "이데일리 마켓팀",
                "연합인포맥스",
            ],
            "ForeignInvestor": [
                f"블랙록(BlackRock) {sector} 펀드",
                "뱅가드 코리아 이머징 펀드",
                "싱가포르 GIC 한국주식팀",
                "골드만삭스 서울 주식팀",
            ],
            "MarketMaker": [
                "한국투자증권 트레이딩팀",
                "KB증권 시장조성팀",
                "NH투자증권 ELW 운용팀",
            ],
            "IndustryExpert": [
                f"한국전자통신연구원 {sector} 전문가",
                f"{sector} 산업 연구원 수석 연구원",
                f"연세대학교 {sector} 전공 교수",
            ],
            "Person": [
                f"{company_name} 주주 {index+1}",
                f"주식 투자 블로거 {index+1}",
                f"유튜브 주식 채널 구독자 {index+1}",
            ],
            "Organization": [
                "한국거래소(KRX)",
                f"한국 {sector} 협회",
            ],
        }

        templates = name_templates.get(entity_type, [f"{entity_type} {index+1}"])
        return templates[index % len(templates)]

    @staticmethod
    def _determine_stance(
        entity_type: str,
        index: int,
        global_sentiment_score: float,
    ) -> tuple:
        """
        에이전트의 투자 성향과 감성 편향을 결정한다.

        전역 감성 점수가 양수이면 매수 성향 에이전트가 많고,
        음수이면 매도 성향 에이전트가 늘어난다.

        Returns:
            (investment_stance: str, sentiment_bias: float)
        """
        # 규제기관, 시장조성자, 언론사는 항상 중립/관찰자
        neutral_types = {"Regulator", "MarketMaker", "MediaOutlet", "Organization"}
        if entity_type in neutral_types:
            return "observer", 0.0

        # 기업 임원은 항상 긍정적 (자사 홍보)
        if entity_type == "CompanyExecutive":
            return "buy", 0.3

        # 나머지는 전역 감성에 따라 확률적으로 성향 부여
        import random
        # 재현 가능한 랜덤 (에이전트 인덱스 기반 시드)
        rng = random.Random(index * 1000 + hash(entity_type) % 1000)

        # 감성 점수에 따른 매수 비율 (0.2~0.8 범위)
        buy_prob = min(0.8, max(0.2, 0.5 + global_sentiment_score * 0.3))
        roll = rng.random()

        if roll < buy_prob * 0.6:
            stance = "buy"
            bias = round(rng.uniform(0.1, 0.5) + global_sentiment_score * 0.2, 2)
        elif roll < buy_prob * 0.6 + (1 - buy_prob) * 0.4:
            stance = "hold"
            bias = round(rng.uniform(-0.1, 0.1), 2)
        elif roll < buy_prob * 0.6 + (1 - buy_prob) * 0.7:
            stance = "sell"
            bias = round(rng.uniform(-0.5, -0.1) + global_sentiment_score * 0.2, 2)
        else:
            stance = "neutral"
            bias = round(rng.uniform(-0.05, 0.05), 2)

        # bias 범위 클리핑
        bias = max(-1.0, min(1.0, bias))
        return stance, bias

    @staticmethod
    def _get_activity_params(entity_type: str) -> tuple:
        """
        에이전트 타입별 활동 파라미터를 반환한다.

        Returns:
            (activity_level, posts_per_hour, comments_per_hour)
        """
        params: Dict[str, tuple] = {
            "Analyst":          (0.4, 0.3, 0.5),   # 분석 보고서 중심
            "Investor":         (0.8, 0.8, 2.0),   # 활발한 매수/매도 행동
            "CompanyExecutive": (0.2, 0.1, 0.1),   # 신중한 공식 발언
            "Regulator":        (0.1, 0.05, 0.05), # 공식 성명 최소화
            "MediaOutlet":      (0.7, 1.2, 0.5),   # 빠른 기사 발행
            "ForeignInvestor":  (0.5, 0.4, 0.8),   # 중간 수준 활동
            "MarketMaker":      (0.3, 0.2, 0.3),   # 유동성 공급에 집중
            "IndustryExpert":   (0.4, 0.3, 0.6),   # 인터뷰·분석 활동
            "Person":           (0.9, 1.0, 2.5),   # 가장 활발한 SNS 활동
            "Organization":     (0.2, 0.1, 0.2),   # 공식 발표 위주
        }
        return params.get(entity_type, (0.5, 0.5, 1.0))

    @staticmethod
    def _get_risk_appetite(entity_type: str) -> str:
        """에이전트 타입별 위험 선호도를 반환한다."""
        appetites: Dict[str, str] = {
            "Analyst":          "moderate",
            "Investor":         "moderate",
            "CompanyExecutive": "conservative",
            "Regulator":        "conservative",
            "MediaOutlet":      "moderate",
            "ForeignInvestor":  "aggressive",
            "MarketMaker":      "moderate",
            "IndustryExpert":   "moderate",
            "Person":           "aggressive",
            "Organization":     "conservative",
        }
        return appetites.get(entity_type, "moderate")

    @staticmethod
    def _get_info_access(entity_type: str) -> str:
        """에이전트 타입별 정보 접근 수준을 반환한다."""
        access_levels: Dict[str, str] = {
            "Analyst":          "premium",   # 기업 IR 직접 접촉
            "Investor":         "public",
            "CompanyExecutive": "insider",   # 내부 정보 (모니터링 필요)
            "Regulator":        "premium",   # 규제 당국 접근권
            "MediaOutlet":      "premium",   # 취재 네트워크
            "ForeignInvestor":  "premium",   # 글로벌 리서치 구독
            "MarketMaker":      "premium",   # 호가 데이터 실시간 접근
            "IndustryExpert":   "premium",   # 산업 협회 정보
            "Person":           "public",
            "Organization":     "public",
        }
        return access_levels.get(entity_type, "public")
