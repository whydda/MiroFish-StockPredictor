"""
주식 예측 보고서 생성 에이전트
시뮬레이션 결과를 분석하여 투자 예측 보고서를 생성

기존 report_agent.py 패턴을 참고하여 한국 주식 예측에 맞게 커스터마이징.

보고서 구조:
    1. 종목 개요 (회사 기본 정보, 현재 주가)
    2. 시뮬레이션 결과 요약 (에이전트들의 투자 결정 분포)
    3. 뉴스 센티먼트 분석 결과
    4. 기술적 분석 요약 (주가 추세, 거래량)
    5. 에이전트 합의 예측 (상승/하락/보합 확률)
    6. 리스크 요인
    7. 종합 투자 의견

면책 조항:
    본 보고서는 AI 시뮬레이션 결과이며 투자 조언이 아닙니다.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.stock_report_agent')


class StockReportStatus(str, Enum):
    """주식 보고서 상태"""
    GENERATING = "generating"   # 생성 중
    COMPLETED = "completed"     # 완료
    FAILED = "failed"           # 실패


class StockReportAgent:
    """
    주식 예측 보고서 생성 에이전트

    시뮬레이션 결과와 재무 데이터를 분석하여 구조화된 투자 예측 보고서를 생성합니다.
    LLMClient를 사용하여 각 섹션을 자동 생성하며, 에이전트 행동 집계를 통해 예측을 도출합니다.
    """

    # 보고서 섹션 정의
    REPORT_SECTIONS = [
        ("overview", "종목 개요"),
        ("simulation_summary", "시뮬레이션 결과 요약"),
        ("sentiment_analysis", "뉴스 센티먼트 분석"),
        ("technical_analysis", "기술적 분석 요약"),
        ("consensus_forecast", "에이전트 합의 예측"),
        ("risk_factors", "리스크 요인"),
        ("investment_opinion", "종합 투자 의견"),
    ]

    def __init__(self):
        """StockReportAgent 초기화"""
        try:
            self.llm = LLMClient()
            self._llm_available = True
            logger.info("StockReportAgent 초기화 완료 (LLM 활성화)")
        except Exception as e:
            logger.warning(f"LLMClient 초기화 실패 - LLM 없이 동작: {str(e)}")
            self.llm = None
            self._llm_available = False

    def generate_report(
        self,
        simulation_id: str,
        ticker: str,
        company_name: str,
        simulation_data: Dict[str, Any],
        financial_data: Dict[str, Any],
        report_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        주식 예측 보고서 생성

        Args:
            simulation_id: 시뮬레이션 ID
            ticker: 종목 코드 (예: "005930")
            company_name: 회사명 (예: "삼성전자")
            simulation_data: 시뮬레이션 결과 데이터
            financial_data: 재무 및 주가 데이터
            report_id: 보고서 ID (None이면 자동 생성)
            progress_callback: 진행 콜백 함수 (stage, progress, message)

        Returns:
            보고서 딕셔너리
        """
        import uuid

        if not report_id:
            report_id = f"stock_report_{uuid.uuid4().hex[:12]}"

        start_time = datetime.now()
        logger.info(f"[{report_id}] 보고서 생성 시작: {ticker} ({company_name})")

        # 기본 보고서 구조 초기화
        report = {
            "report_id": report_id,
            "simulation_id": simulation_id,
            "ticker": ticker,
            "company_name": company_name,
            "status": StockReportStatus.GENERATING.value,
            "sections": {},
            "markdown_content": "",
            "created_at": start_time.isoformat(),
            "completed_at": None,
            "error": None,
            "disclaimer": (
                "⚠️ 본 보고서는 AI 시뮬레이션 결과이며 투자 조언이 아닙니다. "
                "투자 결정은 반드시 전문가의 조언과 개인의 판단에 따라 이루어져야 합니다. "
                "본 보고서의 내용으로 인한 투자 손실에 대해 어떠한 책임도 지지 않습니다."
            )
        }

        try:
            total_sections = len(self.REPORT_SECTIONS)

            # 시뮬레이션 데이터 집계
            if progress_callback:
                progress_callback("preparing", 5, "시뮬레이션 데이터 집계 중...")

            aggregated = self._aggregate_simulation_data(simulation_data)
            market_context = self._extract_market_context(financial_data)

            # 각 섹션 생성
            for i, (section_key, section_title) in enumerate(self.REPORT_SECTIONS):
                section_progress = int(10 + (i / total_sections) * 80)
                if progress_callback:
                    progress_callback(
                        "generating",
                        section_progress,
                        f"섹션 생성 중: {section_title} ({i+1}/{total_sections})"
                    )

                logger.info(f"[{report_id}] 섹션 생성: {section_title}")

                try:
                    section_content = self._generate_section(
                        section_key=section_key,
                        section_title=section_title,
                        ticker=ticker,
                        company_name=company_name,
                        aggregated=aggregated,
                        market_context=market_context,
                        financial_data=financial_data,
                        simulation_data=simulation_data
                    )
                    report["sections"][section_key] = {
                        "title": section_title,
                        "content": section_content
                    }
                    logger.info(f"[{report_id}] 섹션 완료: {section_title} ({len(section_content)}자)")

                except Exception as section_error:
                    # 섹션 생성 실패 시 기본 내용으로 대체 (전체 실패 방지)
                    logger.warning(f"[{report_id}] 섹션 생성 실패 ({section_title}): {str(section_error)}")
                    report["sections"][section_key] = {
                        "title": section_title,
                        "content": f"[섹션 생성 중 오류 발생: {str(section_error)}]"
                    }

            # Markdown 전체 보고서 조합
            if progress_callback:
                progress_callback("assembling", 92, "보고서 최종 조합 중...")

            report["markdown_content"] = self._assemble_markdown(
                report_id=report_id,
                ticker=ticker,
                company_name=company_name,
                sections=report["sections"],
                aggregated=aggregated,
                market_context=market_context,
                disclaimer=report["disclaimer"]
            )

            # 완료 상태 업데이트
            completed_at = datetime.now()
            report["status"] = StockReportStatus.COMPLETED.value
            report["completed_at"] = completed_at.isoformat()
            report["generation_time_seconds"] = (completed_at - start_time).total_seconds()

            if progress_callback:
                progress_callback("completed", 100, "보고서 생성 완료")

            logger.info(
                f"[{report_id}] 보고서 생성 완료: {ticker}, "
                f"소요 시간: {report['generation_time_seconds']:.1f}초"
            )

        except Exception as e:
            report["status"] = StockReportStatus.FAILED.value
            report["error"] = str(e)
            logger.error(f"[{report_id}] 보고서 생성 실패: {str(e)}")

            if progress_callback:
                progress_callback("failed", 0, f"보고서 생성 실패: {str(e)}")

        return report

    def _aggregate_simulation_data(self, simulation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        시뮬레이션 데이터에서 에이전트들의 투자 결정을 집계합니다.

        Args:
            simulation_data: 시뮬레이션 결과 데이터

        Returns:
            집계된 통계 딕셔너리
        """
        agents_decisions = simulation_data.get('agents_decisions', [])
        summary = simulation_data.get('summary', {})
        num_agents = simulation_data.get('num_agents', len(agents_decisions))

        # 행동별 집계
        buy_count = summary.get('buy_count', 0)
        sell_count = summary.get('sell_count', 0)
        hold_count = summary.get('hold_count', 0)

        # 직접 집계 (summary가 없는 경우)
        if not summary and agents_decisions:
            buy_count = sum(1 for d in agents_decisions if d.get('decision') == 'buy')
            sell_count = sum(1 for d in agents_decisions if d.get('decision') == 'sell')
            hold_count = sum(1 for d in agents_decisions if d.get('decision') == 'hold')

        total = max(1, buy_count + sell_count + hold_count)

        # 에이전트 유형별 분포
        type_distribution = {}
        avg_confidence = 0.0
        if agents_decisions:
            for d in agents_decisions:
                agent_type = d.get('agent_type', 'unknown')
                type_distribution[agent_type] = type_distribution.get(agent_type, 0) + 1
            confidences = [d.get('confidence', 0) for d in agents_decisions if d.get('confidence')]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # 전체 신호 결정
        buy_pct = buy_count / total * 100
        sell_pct = sell_count / total * 100
        hold_pct = hold_count / total * 100

        if buy_pct >= 50:
            consensus_signal = "강한 매수"
        elif buy_pct >= 40:
            consensus_signal = "약한 매수"
        elif sell_pct >= 50:
            consensus_signal = "강한 매도"
        elif sell_pct >= 40:
            consensus_signal = "약한 매도"
        else:
            consensus_signal = "보합/관망"

        return {
            "num_agents": num_agents,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "buy_pct": round(buy_pct, 1),
            "sell_pct": round(sell_pct, 1),
            "hold_pct": round(hold_pct, 1),
            "consensus_signal": consensus_signal,
            "type_distribution": type_distribution,
            "avg_confidence": round(avg_confidence, 2),
            "simulation_rounds": simulation_data.get('simulation_rounds', 10)
        }

    def _extract_market_context(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        재무 데이터에서 시장 컨텍스트 정보를 추출합니다.

        Args:
            financial_data: 재무 및 주가 데이터

        Returns:
            시장 컨텍스트 딕셔너리
        """
        ohlcv = financial_data.get('ohlcv', [])
        context = {
            "has_data": bool(ohlcv),
            "data_points": len(ohlcv),
            "period": financial_data.get('period', '1y'),
            "current_price": None,
            "price_change_pct": None,
            "avg_volume": None,
            "price_trend": "데이터 없음",
            "volatility": "데이터 없음"
        }

        if not ohlcv:
            return context

        try:
            # 날짜 키 처리 (pykrx는 한국어 또는 영어 컬럼명 사용)
            close_key = None
            volume_key = None
            for possible_close in ['종가', 'close', 'Close']:
                if possible_close in ohlcv[0]:
                    close_key = possible_close
                    break
            for possible_vol in ['거래량', 'volume', 'Volume']:
                if possible_vol in ohlcv[0]:
                    volume_key = possible_vol
                    break

            if close_key:
                prices = [float(row[close_key] or 0) for row in ohlcv if row.get(close_key)]
                if prices:
                    context["current_price"] = prices[-1]
                    if len(prices) >= 2:
                        context["price_change_pct"] = round(
                            (prices[-1] - prices[0]) / prices[0] * 100, 2
                        )

                    # 추세 판단 (최근 20일 이동평균 기준)
                    if len(prices) >= 20:
                        ma20 = sum(prices[-20:]) / 20
                        if prices[-1] > ma20 * 1.03:
                            context["price_trend"] = "강한 상승 추세"
                        elif prices[-1] > ma20:
                            context["price_trend"] = "약한 상승 추세"
                        elif prices[-1] < ma20 * 0.97:
                            context["price_trend"] = "강한 하락 추세"
                        else:
                            context["price_trend"] = "약한 하락 추세"
                    else:
                        pct = context.get("price_change_pct", 0) or 0
                        if pct > 5:
                            context["price_trend"] = "상승 추세"
                        elif pct < -5:
                            context["price_trend"] = "하락 추세"
                        else:
                            context["price_trend"] = "횡보 추세"

                    # 변동성 (최근 20일 표준편차)
                    if len(prices) >= 5:
                        recent = prices[-min(20, len(prices)):]
                        avg = sum(recent) / len(recent)
                        variance = sum((p - avg) ** 2 for p in recent) / len(recent)
                        std_pct = (variance ** 0.5) / avg * 100 if avg > 0 else 0
                        if std_pct > 5:
                            context["volatility"] = f"고변동성 ({std_pct:.1f}%)"
                        elif std_pct > 2:
                            context["volatility"] = f"중변동성 ({std_pct:.1f}%)"
                        else:
                            context["volatility"] = f"저변동성 ({std_pct:.1f}%)"

            if volume_key:
                volumes = [float(row[volume_key] or 0) for row in ohlcv if row.get(volume_key)]
                if volumes:
                    context["avg_volume"] = int(sum(volumes) / len(volumes))

        except Exception as e:
            logger.warning(f"시장 컨텍스트 추출 중 오류: {str(e)}")

        return context

    def _generate_section(
        self,
        section_key: str,
        section_title: str,
        ticker: str,
        company_name: str,
        aggregated: Dict[str, Any],
        market_context: Dict[str, Any],
        financial_data: Dict[str, Any],
        simulation_data: Dict[str, Any]
    ) -> str:
        """
        개별 섹션 콘텐츠를 생성합니다.
        LLM이 사용 가능하면 LLM을 통해 생성하고, 그렇지 않으면 규칙 기반으로 생성합니다.

        Args:
            section_key: 섹션 식별자
            section_title: 섹션 제목
            ticker: 종목 코드
            company_name: 회사명
            aggregated: 집계된 시뮬레이션 통계
            market_context: 시장 컨텍스트
            financial_data: 재무 데이터
            simulation_data: 전체 시뮬레이션 데이터

        Returns:
            섹션 내용 문자열
        """
        if self._llm_available and self.llm:
            return self._generate_section_with_llm(
                section_key=section_key,
                section_title=section_title,
                ticker=ticker,
                company_name=company_name,
                aggregated=aggregated,
                market_context=market_context,
                financial_data=financial_data,
                simulation_data=simulation_data
            )
        else:
            return self._generate_section_rule_based(
                section_key=section_key,
                ticker=ticker,
                company_name=company_name,
                aggregated=aggregated,
                market_context=market_context
            )

    def _generate_section_with_llm(
        self,
        section_key: str,
        section_title: str,
        ticker: str,
        company_name: str,
        aggregated: Dict[str, Any],
        market_context: Dict[str, Any],
        financial_data: Dict[str, Any],
        simulation_data: Dict[str, Any]
    ) -> str:
        """LLM을 사용하여 섹션을 생성합니다."""

        # 섹션별 프롬프트 구성
        prompts = {
            "overview": f"""
종목 개요 섹션을 작성하세요.

종목 정보:
- 종목 코드: {ticker}
- 회사명: {company_name}
- 분석 기간: {financial_data.get('period', '1y')}
- 현재 주가: {market_context.get('current_price', 'N/A')}원
- 기간 수익률: {market_context.get('price_change_pct', 'N/A')}%
- 주가 추세: {market_context.get('price_trend', 'N/A')}
- 변동성: {market_context.get('volatility', 'N/A')}

200자 내외로 회사의 현황과 주가 상태를 간략히 서술하세요. 마크다운 없이 순수 텍스트로 작성하세요.
""",
            "simulation_summary": f"""
시뮬레이션 결과 요약 섹션을 작성하세요.

시뮬레이션 통계:
- 참여 에이전트 수: {aggregated['num_agents']}명
- 매수 결정: {aggregated['buy_count']}명 ({aggregated['buy_pct']}%)
- 매도 결정: {aggregated['sell_count']}명 ({aggregated['sell_pct']}%)
- 보합/관망: {aggregated['hold_count']}명 ({aggregated['hold_pct']}%)
- 평균 신뢰도: {aggregated['avg_confidence']}
- 에이전트 유형 분포: {aggregated['type_distribution']}

시뮬레이션 라운드: {aggregated['simulation_rounds']}회

에이전트들의 투자 결정 분포와 그 의미를 250자 내외로 분석하세요. 마크다운 없이 순수 텍스트로 작성하세요.
""",
            "sentiment_analysis": f"""
뉴스 센티먼트 분석 섹션을 작성하세요.

종목: {company_name}({ticker})
시뮬레이션 결과 신호: {aggregated['consensus_signal']}
에이전트 매수 비율: {aggregated['buy_pct']}%

주식 시장에서의 일반적인 {company_name}에 대한 시장 감성(센티먼트)을 분석하고,
뉴스 및 시장 분위기가 에이전트 결정에 미친 영향을 200자 내외로 서술하세요.
마크다운 없이 순수 텍스트로 작성하세요.
""",
            "technical_analysis": f"""
기술적 분석 요약 섹션을 작성하세요.

주가 데이터:
- 현재 주가: {market_context.get('current_price', 'N/A')}원
- 기간 수익률: {market_context.get('price_change_pct', 'N/A')}%
- 주가 추세: {market_context.get('price_trend', '데이터 없음')}
- 변동성: {market_context.get('volatility', '데이터 없음')}
- 평균 거래량: {market_context.get('avg_volume', 'N/A')}주
- 데이터 포인트: {market_context.get('data_points', 0)}일

이동평균, 추세, 거래량 등 기술적 지표를 바탕으로 250자 내외로 분석하세요.
마크다운 없이 순수 텍스트로 작성하세요.
""",
            "consensus_forecast": f"""
에이전트 합의 예측 섹션을 작성하세요.

집계 결과:
- 상승(매수) 확률: {aggregated['buy_pct']}%
- 하락(매도) 확률: {aggregated['sell_pct']}%
- 보합 확률: {aggregated['hold_pct']}%
- 합의 신호: {aggregated['consensus_signal']}
- 평균 신뢰도: {aggregated['avg_confidence']}

에이전트 합의에 기반한 {company_name}({ticker}) 주가 예측을 200자 내외로 서술하세요.
확률과 합의 신호를 명확하게 포함시키세요. 마크다운 없이 순수 텍스트로 작성하세요.
""",
            "risk_factors": f"""
리스크 요인 섹션을 작성하세요.

종목: {company_name}({ticker})
현재 추세: {market_context.get('price_trend', '데이터 없음')}
변동성: {market_context.get('volatility', '데이터 없음')}
매도 에이전트 비율: {aggregated['sell_pct']}%

{company_name}({ticker}) 투자 시 고려해야 할 주요 리스크 요인 3~5가지를 250자 내외로 작성하세요.
시장 리스크, 산업 리스크, 기업 고유 리스크 등을 포함하세요. 마크다운 없이 순수 텍스트로 작성하세요.
""",
            "investment_opinion": f"""
종합 투자 의견 섹션을 작성하세요.

분석 요약:
- 종목: {company_name}({ticker})
- 합의 신호: {aggregated['consensus_signal']}
- 매수 에이전트: {aggregated['buy_pct']}%
- 주가 추세: {market_context.get('price_trend', '데이터 없음')}
- 변동성: {market_context.get('volatility', '데이터 없음')}

위 분석을 종합하여 투자 의견을 250자 내외로 작성하세요.
반드시 "본 보고서는 AI 시뮬레이션 결과이며 투자 조언이 아닙니다"라는 문구를 포함하세요.
마크다운 없이 순수 텍스트로 작성하세요.
"""
        }

        prompt = prompts.get(section_key, f"{section_title} 섹션 내용을 200자 내외로 작성하세요.")

        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 한국 주식 시장 전문 분석가입니다. "
                    "AI 시뮬레이션 데이터를 바탕으로 객관적이고 간결한 보고서 섹션을 작성합니다. "
                    "과장하지 말고 데이터에 근거하여 작성하세요."
                )
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]

        response = self.llm.chat(
            messages=messages,
            temperature=Config.REPORT_AGENT_TEMPERATURE,
            max_tokens=512
        )

        return response.strip()

    def _generate_section_rule_based(
        self,
        section_key: str,
        ticker: str,
        company_name: str,
        aggregated: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> str:
        """
        LLM 없이 규칙 기반으로 섹션을 생성합니다.
        LLMClient가 사용 불가능할 때 폴백으로 사용됩니다.

        Args:
            section_key: 섹션 식별자
            ticker: 종목 코드
            company_name: 회사명
            aggregated: 집계 통계
            market_context: 시장 컨텍스트

        Returns:
            섹션 내용 문자열
        """
        current_price = market_context.get('current_price')
        price_change = market_context.get('price_change_pct')
        price_trend = market_context.get('price_trend', '데이터 없음')
        volatility = market_context.get('volatility', '데이터 없음')
        avg_volume = market_context.get('avg_volume')

        if section_key == "overview":
            price_str = f"{current_price:,.0f}원" if current_price else "N/A"
            change_str = f"{price_change:+.2f}%" if price_change is not None else "N/A"
            return (
                f"{company_name}(종목 코드: {ticker})은(는) 한국 주식 시장에 상장된 기업입니다. "
                f"분석 기간({market_context.get('period', '1y')}) 동안 현재 주가는 {price_str}이며, "
                f"기간 수익률은 {change_str}입니다. "
                f"주가 추세는 '{price_trend}'로 파악됩니다."
            )

        elif section_key == "simulation_summary":
            return (
                f"총 {aggregated['num_agents']}명의 AI 에이전트가 {aggregated['simulation_rounds']}라운드 "
                f"시뮬레이션에 참여했습니다. "
                f"매수 의견: {aggregated['buy_count']}명({aggregated['buy_pct']}%), "
                f"매도 의견: {aggregated['sell_count']}명({aggregated['sell_pct']}%), "
                f"보합/관망: {aggregated['hold_count']}명({aggregated['hold_pct']}%)으로 집계되었습니다. "
                f"에이전트 평균 신뢰도는 {aggregated['avg_confidence']:.0%}입니다."
            )

        elif section_key == "sentiment_analysis":
            signal = aggregated['consensus_signal']
            if '매수' in signal:
                sentiment = "전반적으로 긍정적"
            elif '매도' in signal:
                sentiment = "전반적으로 부정적"
            else:
                sentiment = "중립적"
            return (
                f"{company_name}({ticker})에 대한 시장 센티먼트는 {sentiment}으로 분석됩니다. "
                f"에이전트 합의 신호({signal})를 기반으로 판단할 때, "
                f"시장 참여자들은 해당 종목에 대해 {sentiment}인 시각을 유지하고 있습니다. "
                f"뉴스 흐름 및 외부 이벤트의 영향을 지속적으로 모니터링할 필요가 있습니다."
            )

        elif section_key == "technical_analysis":
            price_str = f"{current_price:,.0f}원" if current_price else "N/A"
            vol_str = f"{avg_volume:,.0f}주" if avg_volume else "N/A"
            return (
                f"현재 주가 {price_str} 기준, 주가 추세는 '{price_trend}'이며 "
                f"변동성은 '{volatility}'로 파악됩니다. "
                f"평균 거래량은 {vol_str}입니다. "
                f"총 {market_context.get('data_points', 0)}일간의 데이터가 분석에 활용되었습니다."
            )

        elif section_key == "consensus_forecast":
            return (
                f"AI 에이전트 합의 분석 결과: "
                f"상승(매수) 확률 {aggregated['buy_pct']}%, "
                f"하락(매도) 확률 {aggregated['sell_pct']}%, "
                f"보합 확률 {aggregated['hold_pct']}%입니다. "
                f"전체 합의 신호는 '{aggregated['consensus_signal']}'으로 도출되었습니다. "
                f"이 예측은 {aggregated['num_agents']}개 에이전트의 시뮬레이션에 기반한 통계적 결과입니다."
            )

        elif section_key == "risk_factors":
            return (
                f"주요 투자 리스크 요인:\n"
                f"1. 시장 변동성: {volatility}으로 가격 변동 위험 존재\n"
                f"2. 거시경제 리스크: 금리, 환율, 글로벌 경기 변동에 따른 영향\n"
                f"3. 산업 경쟁 리스크: 경쟁사 동향 및 산업 구조 변화\n"
                f"4. 기업 고유 리스크: 실적 변동, 경영진 변화, 사업 환경 변화\n"
                f"5. 유동성 리스크: 거래량 변동 및 시장 참여자 수급 불균형"
            )

        elif section_key == "investment_opinion":
            signal = aggregated['consensus_signal']
            return (
                f"{company_name}({ticker})에 대한 AI 시뮬레이션 종합 의견은 '{signal}'입니다. "
                f"에이전트 {aggregated['buy_pct']}%가 매수를 선택했으며, "
                f"주가 추세({price_trend})와 변동성({volatility})을 종합적으로 고려해야 합니다. "
                f"투자 전 충분한 개인 분석과 전문가 조언을 권장합니다. "
                f"본 보고서는 AI 시뮬레이션 결과이며 투자 조언이 아닙니다."
            )

        else:
            return f"{section_key} 섹션 데이터를 분석하였습니다."

    def _assemble_markdown(
        self,
        report_id: str,
        ticker: str,
        company_name: str,
        sections: Dict[str, Any],
        aggregated: Dict[str, Any],
        market_context: Dict[str, Any],
        disclaimer: str
    ) -> str:
        """
        모든 섹션을 합쳐 Markdown 형식의 최종 보고서를 생성합니다.

        Args:
            report_id: 보고서 ID
            ticker: 종목 코드
            company_name: 회사명
            sections: 생성된 섹션 딕셔너리
            aggregated: 집계 통계
            market_context: 시장 컨텍스트
            disclaimer: 면책 조항

        Returns:
            Markdown 형식의 보고서 문자열
        """
        now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

        lines = [
            f"# {company_name}({ticker}) 주식 예측 보고서",
            f"",
            f"> **보고서 ID:** {report_id}  ",
            f"> **생성 일시:** {now}  ",
            f"> **분석 기간:** {market_context.get('period', '1y')}  ",
            f"",
            f"---",
            f"",
            f"## 📊 핵심 요약",
            f"",
            f"| 지표 | 값 |",
            f"|------|-----|",
            f"| 현재 주가 | {market_context.get('current_price', 'N/A'):,.0f}원 "
            if market_context.get('current_price') else "| 현재 주가 | N/A |",
            f"| 기간 수익률 | {market_context.get('price_change_pct', 'N/A'):+.2f}% "
            if market_context.get('price_change_pct') is not None else "| 기간 수익률 | N/A |",
            f"| 주가 추세 | {market_context.get('price_trend', 'N/A')} |",
            f"| 에이전트 합의 | {aggregated['consensus_signal']} |",
            f"| 매수 비율 | {aggregated['buy_pct']}% |",
            f"| 매도 비율 | {aggregated['sell_pct']}% |",
            f"| 보합 비율 | {aggregated['hold_pct']}% |",
            f"",
            f"---",
            f""
        ]

        # 각 섹션 추가
        section_icons = {
            "overview": "🏢",
            "simulation_summary": "🤖",
            "sentiment_analysis": "📰",
            "technical_analysis": "📈",
            "consensus_forecast": "🎯",
            "risk_factors": "⚠️",
            "investment_opinion": "💡"
        }

        for section_key, section_data in sections.items():
            icon = section_icons.get(section_key, "📋")
            title = section_data.get("title", section_key)
            content = section_data.get("content", "")

            lines.append(f"## {icon} {title}")
            lines.append(f"")
            lines.append(content)
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        # 면책 조항
        lines.extend([
            f"## ⚠️ 면책 조항",
            f"",
            f"> {disclaimer}",
            f""
        ])

        # 수치를 포맷팅할 때 타입 오류 방지를 위한 후처리
        formatted_lines = []
        for line in lines:
            if isinstance(line, str):
                formatted_lines.append(line)
            else:
                formatted_lines.append(str(line))

        return "\n".join(formatted_lines)


class StockReportManager:
    """
    주식 보고서 파일 시스템 관리자

    보고서를 파일 시스템에 저장하고 조회하는 기능을 제공합니다.
    기존 ReportManager 패턴을 참고하여 주식 보고서에 맞게 구성합니다.
    """

    # 보고서 저장 기본 디렉토리
    REPORTS_BASE_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/stock_reports'
    )

    @classmethod
    def _get_report_dir(cls, report_id: str) -> str:
        """보고서 디렉토리 경로를 반환합니다."""
        report_dir = os.path.join(cls.REPORTS_BASE_DIR, report_id)
        os.makedirs(report_dir, exist_ok=True)
        return report_dir

    @classmethod
    def save_report(cls, report: Dict[str, Any]) -> bool:
        """
        보고서를 파일 시스템에 저장합니다.

        Args:
            report: 보고서 딕셔너리

        Returns:
            저장 성공 여부
        """
        try:
            report_id = report.get('report_id')
            if not report_id:
                logger.error("보고서 ID가 없습니다")
                return False

            report_dir = cls._get_report_dir(report_id)

            # 보고서 메타데이터 저장 (JSON)
            meta_path = os.path.join(report_dir, 'report.json')
            # markdown_content는 별도 파일로 저장하여 JSON 크기 최소화
            report_meta = {k: v for k, v in report.items() if k != 'markdown_content'}
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(report_meta, f, ensure_ascii=False, indent=2)

            # Markdown 보고서 별도 저장
            markdown_content = report.get('markdown_content', '')
            if markdown_content:
                md_path = os.path.join(report_dir, 'report.md')
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

            logger.info(f"보고서 저장 완료: {report_id}")
            return True

        except Exception as e:
            logger.error(f"보고서 저장 실패: {str(e)}")
            return False

    @classmethod
    def get_report(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """
        보고서를 파일 시스템에서 로드합니다.

        Args:
            report_id: 보고서 ID

        Returns:
            보고서 딕셔너리 또는 None
        """
        try:
            report_dir = os.path.join(cls.REPORTS_BASE_DIR, report_id)
            meta_path = os.path.join(report_dir, 'report.json')

            if not os.path.exists(meta_path):
                return None

            with open(meta_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

            # Markdown 내용 로드
            md_path = os.path.join(report_dir, 'report.md')
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8') as f:
                    report['markdown_content'] = f.read()
            else:
                report['markdown_content'] = ''

            return report

        except Exception as e:
            logger.error(f"보고서 로드 실패 ({report_id}): {str(e)}")
            return None

    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Dict[str, Any]]:
        """
        시뮬레이션 ID로 보고서를 검색합니다.

        Args:
            simulation_id: 시뮬레이션 ID

        Returns:
            보고서 딕셔너리 또는 None
        """
        try:
            if not os.path.exists(cls.REPORTS_BASE_DIR):
                return None

            # 모든 보고서 디렉토리 순회
            for report_id in os.listdir(cls.REPORTS_BASE_DIR):
                report_path = os.path.join(cls.REPORTS_BASE_DIR, report_id)
                # 숨김 파일 및 비디렉토리 건너뜀
                if report_id.startswith('.') or not os.path.isdir(report_path):
                    continue

                meta_path = os.path.join(report_path, 'report.json')
                if not os.path.exists(meta_path):
                    continue

                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        report_meta = json.load(f)

                    if report_meta.get('simulation_id') == simulation_id:
                        # Markdown 내용 추가
                        md_path = os.path.join(report_path, 'report.md')
                        if os.path.exists(md_path):
                            with open(md_path, 'r', encoding='utf-8') as f:
                                report_meta['markdown_content'] = f.read()
                        else:
                            report_meta['markdown_content'] = ''
                        return report_meta
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"시뮬레이션 ID로 보고서 검색 실패 ({simulation_id}): {str(e)}")
            return None

    @classmethod
    def list_reports(
        cls,
        ticker: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        보고서 목록을 반환합니다.

        Args:
            ticker: 종목 코드 필터 (선택)
            limit: 반환 최대 건수

        Returns:
            보고서 요약 목록
        """
        reports = []

        try:
            if not os.path.exists(cls.REPORTS_BASE_DIR):
                return []

            for report_id in os.listdir(cls.REPORTS_BASE_DIR):
                report_path = os.path.join(cls.REPORTS_BASE_DIR, report_id)
                if report_id.startswith('.') or not os.path.isdir(report_path):
                    continue

                meta_path = os.path.join(report_path, 'report.json')
                if not os.path.exists(meta_path):
                    continue

                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        report_meta = json.load(f)

                    # 종목 코드 필터 적용
                    if ticker and report_meta.get('ticker') != ticker:
                        continue

                    # markdown_content 제외한 요약 정보만 반환
                    summary = {
                        k: v for k, v in report_meta.items()
                        if k not in ('markdown_content', 'sections')
                    }
                    reports.append(summary)

                except Exception:
                    continue

            # 생성 시각 기준 내림차순 정렬
            reports.sort(
                key=lambda r: r.get('created_at', ''),
                reverse=True
            )
            return reports[:limit]

        except Exception as e:
            logger.error(f"보고서 목록 조회 실패: {str(e)}")
            return []

    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """
        보고서를 삭제합니다.

        Args:
            report_id: 보고서 ID

        Returns:
            삭제 성공 여부
        """
        import shutil

        try:
            report_dir = os.path.join(cls.REPORTS_BASE_DIR, report_id)
            if not os.path.exists(report_dir):
                return False

            shutil.rmtree(report_dir)
            logger.info(f"보고서 삭제 완료: {report_id}")
            return True

        except Exception as e:
            logger.error(f"보고서 삭제 실패 ({report_id}): {str(e)}")
            return False
