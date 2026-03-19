"""
한국 주식 데이터 수집 서비스
뉴스 + 재무 데이터를 복합으로 수집하여 에이전트 시뮬레이션에 입력

수집 출처:
- 뉴스: 네이버 금융 (https://finance.naver.com)
- 주가/재무: pykrx 라이브러리 (한국거래소 공식 데이터)
- 감성 분석: 키워드 기반 한국어 감성 분석
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('mirofish.stock_data_collector')


# ============================================================
# 한국어 감성 분석 키워드 사전
# ============================================================

# 긍정 키워드: 주가 상승 또는 호재를 암시하는 단어
POSITIVE_KEYWORDS = [
    "상승", "호재", "매수", "성장", "돌파", "신고가", "흑자", "실적개선",
    "급등", "강세", "반등", "회복", "수익", "호실적", "개선", "확대",
    "증가", "인수", "수주", "계약", "신제품", "기대", "긍정", "우수",
    "사상최고", "최고치", "기록", "상향", "목표가상향", "매수추천",
    "어닝서프라이즈", "깜짝실적", "초과달성", "역대최대", "최대실적",
]

# 부정 키워드: 주가 하락 또는 악재를 암시하는 단어
NEGATIVE_KEYWORDS = [
    "하락", "악재", "매도", "감소", "적자", "실적악화", "하한가",
    "급락", "약세", "부진", "손실", "손해", "위험", "불확실", "우려",
    "경고", "제재", "규제", "소송", "분쟁", "리스크", "하향", "목표가하향",
    "매도추천", "어닝쇼크", "실적쇼크", "미달", "부채", "유동성위기",
    "파산", "상장폐지", "감사의견", "한계", "부정적",
]

# 중립 키워드: 단순 사실 전달 (감성 중립)
NEUTRAL_KEYWORDS = [
    "발표", "공시", "보고", "결산", "예정", "계획", "추진", "검토",
    "협의", "논의", "분석", "전망", "예측", "예상", "목표",
]

# ============================================================
# 네이버 금융 뉴스 수집 설정
# ============================================================

NAVER_FINANCE_NEWS_URL = "https://finance.naver.com/item/news_news.naver"
NAVER_FINANCE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://finance.naver.com/",
}


class StockDataCollector:
    """
    한국 주식 데이터 수집기

    네이버 금융 뉴스와 pykrx 라이브러리를 통해 주식 관련 데이터를 수집하고,
    MiroFish 시뮬레이션 입력 텍스트 형식으로 변환한다.
    """

    def __init__(self, request_timeout: int = 10):
        """
        Args:
            request_timeout: HTTP 요청 타임아웃 (초)
        """
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update(NAVER_FINANCE_HEADERS)

    # ----------------------------------------------------------
    # 1. 뉴스 수집
    # ----------------------------------------------------------

    def collect_stock_news(
        self,
        ticker: str,
        company_name: str,
        days: int = 7,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        네이버 금융에서 종목 관련 뉴스를 수집한다.

        네이버 금융 뉴스 URL 패턴:
            https://finance.naver.com/item/news_news.naver?code={ticker}&page=1

        Args:
            ticker:       종목 코드 (예: "005930" for 삼성전자)
            company_name: 회사명 (예: "삼성전자")
            days:         최근 N일 이내 뉴스만 수집 (기본값 7일)
            max_pages:    최대 페이지 수 (기본값 3페이지)

        Returns:
            뉴스 딕셔너리 리스트
            [
                {
                    "title":    str,   # 뉴스 제목
                    "url":      str,   # 뉴스 원문 URL
                    "date":     str,   # 날짜 문자열 (YYYY.MM.DD HH:MM)
                    "source":   str,   # 언론사명
                    "summary":  str,   # 제목 기반 요약 (제목과 동일, 본문 미수집)
                }
            ]
        """
        news_list: List[Dict[str, Any]] = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for page in range(1, max_pages + 1):
            try:
                url = f"{NAVER_FINANCE_NEWS_URL}?code={ticker}&page={page}"
                resp = self.session.get(url, timeout=self.request_timeout)
                resp.encoding = "euc-kr"  # 네이버 금융은 EUC-KR 인코딩
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                page_news = self._parse_naver_news_page(soup, cutoff_date)

                if not page_news:
                    # 더 이상 기간 내 뉴스가 없으면 중단
                    break

                news_list.extend(page_news)
                logger.info(
                    f"[{company_name}({ticker})] 페이지 {page}: "
                    f"{len(page_news)}건 수집 (누적 {len(news_list)}건)"
                )

            except requests.RequestException as e:
                logger.warning(
                    f"[{company_name}({ticker})] 페이지 {page} 수집 실패: {e}"
                )
                break

        logger.info(
            f"[{company_name}({ticker})] 총 {len(news_list)}건 뉴스 수집 완료"
        )
        return news_list

    def _parse_naver_news_page(
        self,
        soup: BeautifulSoup,
        cutoff_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        네이버 금융 뉴스 페이지 HTML을 파싱하여 뉴스 목록을 추출한다.

        네이버 금융 뉴스 테이블 구조:
          <table class="type5">
            <tr>
              <td class="title"><a href="...">뉴스제목</a></td>
              <td class="info">언론사</td>
              <td class="date">날짜</td>
            </tr>
            ...
          </table>
        """
        news_list = []

        # 뉴스 테이블 탐색
        news_table = soup.find("table", class_="type5")
        if not news_table:
            return news_list

        rows = news_table.find_all("tr")
        for row in rows:
            try:
                # 제목 td
                title_td = row.find("td", class_="title")
                if not title_td:
                    continue

                title_tag = title_td.find("a")
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")

                # 상대 경로를 절대 경로로 변환
                if href.startswith("/"):
                    article_url = f"https://finance.naver.com{href}"
                else:
                    article_url = href

                # 언론사
                source_td = row.find("td", class_="info")
                source = source_td.get_text(strip=True) if source_td else "알 수 없음"

                # 날짜
                date_td = row.find("td", class_="date")
                date_str = date_td.get_text(strip=True) if date_td else ""

                # 날짜 파싱 및 필터링 (YYYY.MM.DD HH:MM 형식)
                article_date = self._parse_naver_date(date_str)
                if article_date and article_date < cutoff_date:
                    # 기간 이전 뉴스 → 해당 페이지에서 더 이상 수집 불필요
                    return news_list

                # 유효한 뉴스만 추가
                if title and article_url:
                    news_list.append(
                        {
                            "title": title,
                            "url": article_url,
                            "date": date_str,
                            "source": source,
                            "summary": title,  # 본문 미수집, 제목을 요약으로 사용
                        }
                    )

            except Exception as e:
                logger.debug(f"뉴스 행 파싱 오류 (무시): {e}")
                continue

        return news_list

    @staticmethod
    def _parse_naver_date(date_str: str) -> Optional[datetime]:
        """
        네이버 금융 날짜 문자열을 datetime으로 파싱한다.

        지원 형식:
          - "2024.01.15 09:30"
          - "2024.01.15"
        """
        date_str = date_str.strip()
        for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    # ----------------------------------------------------------
    # 2. 재무/주가 데이터 수집
    # ----------------------------------------------------------

    def collect_financial_data(self, ticker: str) -> Dict[str, Any]:
        """
        pykrx 라이브러리를 사용하여 종목의 주가 및 재무 지표를 수집한다.

        수집 데이터:
          - OHLCV (시가, 고가, 저가, 종가, 거래량) - 최근 20 거래일
          - PER, PBR, DIV (배당수익률), EPS, BPS 등 재무 지표

        Args:
            ticker: 종목 코드 (예: "005930")

        Returns:
            {
                "ticker":          str,
                "current_price":   float | None,
                "price_change":    float | None,   # 전일 대비 변동률(%)
                "volume":          int | None,      # 거래량
                "per":             float | None,    # PER
                "pbr":             float | None,    # PBR
                "div":             float | None,    # 배당수익률(%)
                "eps":             float | None,    # 주당순이익
                "bps":             float | None,    # 주당순자산
                "market_cap":      int | None,      # 시가총액(억원)
                "price_history":   list,            # 최근 20일 OHLCV
                "collected_at":    str,
            }
        """
        result: Dict[str, Any] = {
            "ticker": ticker,
            "current_price": None,
            "price_change": None,
            "volume": None,
            "per": None,
            "pbr": None,
            "div": None,
            "eps": None,
            "bps": None,
            "market_cap": None,
            "price_history": [],
            "collected_at": datetime.now().isoformat(),
        }

        try:
            # pykrx 임포트 (런타임에서만 필요)
            from pykrx import stock as krx_stock  # type: ignore

            # 날짜 범위 설정 (최근 30일 → 영업일 기준 약 20일 커버)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            # ---- 주가 OHLCV 수집 ----
            ohlcv_df = krx_stock.get_market_ohlcv_by_date(start_date, end_date, ticker)

            if ohlcv_df is not None and not ohlcv_df.empty:
                # 최근 20일로 제한
                ohlcv_df = ohlcv_df.tail(20)

                # 현재(최신) 가격 및 거래량
                latest_row = ohlcv_df.iloc[-1]
                result["current_price"] = float(latest_row.get("종가", 0) or 0)
                result["volume"] = int(latest_row.get("거래량", 0) or 0)

                # 전일 대비 변동률 계산
                if len(ohlcv_df) >= 2:
                    prev_close = float(ohlcv_df.iloc[-2].get("종가", 0) or 0)
                    curr_close = result["current_price"]
                    if prev_close and prev_close > 0:
                        result["price_change"] = round(
                            (curr_close - prev_close) / prev_close * 100, 2
                        )

                # 가격 히스토리 (날짜, 종가, 거래량)
                result["price_history"] = [
                    {
                        "date": str(idx.date()),
                        "open": float(row.get("시가", 0) or 0),
                        "high": float(row.get("고가", 0) or 0),
                        "low": float(row.get("저가", 0) or 0),
                        "close": float(row.get("종가", 0) or 0),
                        "volume": int(row.get("거래량", 0) or 0),
                    }
                    for idx, row in ohlcv_df.iterrows()
                ]

            # ---- 재무 지표 수집 (PER, PBR 등) ----
            try:
                fundamental_df = krx_stock.get_market_fundamental_by_date(
                    start_date, end_date, ticker
                )

                if fundamental_df is not None and not fundamental_df.empty:
                    latest_fund = fundamental_df.iloc[-1]
                    result["per"] = self._safe_float(latest_fund.get("PER"))
                    result["pbr"] = self._safe_float(latest_fund.get("PBR"))
                    result["div"] = self._safe_float(latest_fund.get("DIV"))
                    result["eps"] = self._safe_float(latest_fund.get("EPS"))
                    result["bps"] = self._safe_float(latest_fund.get("BPS"))

            except Exception as e:
                logger.warning(f"[{ticker}] 재무 지표 수집 실패: {e}")

            # ---- 시가총액 수집 ----
            try:
                cap_df = krx_stock.get_market_cap_by_date(
                    start_date, end_date, ticker
                )
                if cap_df is not None and not cap_df.empty:
                    latest_cap = cap_df.iloc[-1]
                    # 시가총액은 원 단위 → 억 원으로 변환
                    raw_cap = latest_cap.get("시가총액", 0) or 0
                    result["market_cap"] = int(raw_cap // 1_0000_0000)

            except Exception as e:
                logger.warning(f"[{ticker}] 시가총액 수집 실패: {e}")

            logger.info(f"[{ticker}] 재무 데이터 수집 완료: 주가={result['current_price']}")

        except ImportError:
            logger.error(
                "pykrx 라이브러리가 설치되어 있지 않습니다. "
                "'pip install pykrx'로 설치하세요."
            )
        except Exception as e:
            logger.error(f"[{ticker}] 재무 데이터 수집 중 오류 발생: {e}")

        return result

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """안전하게 float 변환 (None, NaN, 0 처리)"""
        try:
            v = float(value)
            if v != v:  # NaN 검사
                return None
            return v if v != 0 else None
        except (TypeError, ValueError):
            return None

    # ----------------------------------------------------------
    # 3. 시장 감성 분석
    # ----------------------------------------------------------

    def collect_market_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        뉴스 제목 기반으로 시장 감성을 분석한다.

        키워드 기반 간단한 분류 방식:
          - 긍정 키워드 등장 횟수 vs. 부정 키워드 등장 횟수 비교
          - 최종 감성: positive / negative / neutral

        Args:
            ticker: 종목 코드

        Returns:
            {
                "ticker":              str,
                "overall_sentiment":   str,   # "positive" | "negative" | "neutral"
                "positive_count":      int,
                "negative_count":      int,
                "neutral_count":       int,
                "total_articles":      int,
                "sentiment_score":     float,  # -1.0 ~ 1.0
                "top_positive_words":  list,   # 가장 많이 등장한 긍정 키워드
                "top_negative_words":  list,   # 가장 많이 등장한 부정 키워드
                "analyzed_at":         str,
            }
        """
        # 최근 7일치 뉴스 수집 (감성 분석 목적)
        # company_name은 로그 목적이므로 ticker를 그대로 사용
        news_items = self.collect_stock_news(
            ticker=ticker,
            company_name=ticker,
            days=7,
            max_pages=2,
        )

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        # 키워드별 등장 횟수 집계
        positive_word_counts: Dict[str, int] = {}
        negative_word_counts: Dict[str, int] = {}

        for item in news_items:
            title = item.get("title", "")
            article_sentiment = self._classify_sentiment(title)

            if article_sentiment == "positive":
                positive_count += 1
                # 긍정 키워드 카운트
                for kw in POSITIVE_KEYWORDS:
                    if kw in title:
                        positive_word_counts[kw] = positive_word_counts.get(kw, 0) + 1

            elif article_sentiment == "negative":
                negative_count += 1
                # 부정 키워드 카운트
                for kw in NEGATIVE_KEYWORDS:
                    if kw in title:
                        negative_word_counts[kw] = negative_word_counts.get(kw, 0) + 1

            else:
                neutral_count += 1

        total = len(news_items)

        # 감성 점수 계산 (-1.0 ~ 1.0)
        if total > 0:
            sentiment_score = (positive_count - negative_count) / total
        else:
            sentiment_score = 0.0

        # 전체 감성 결정
        if positive_count > negative_count:
            overall = "positive"
        elif negative_count > positive_count:
            overall = "negative"
        else:
            overall = "neutral"

        # 상위 키워드 추출 (상위 5개)
        top_positive = sorted(
            positive_word_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_negative = sorted(
            negative_word_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        result = {
            "ticker": ticker,
            "overall_sentiment": overall,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_articles": total,
            "sentiment_score": round(sentiment_score, 4),
            "top_positive_words": [kw for kw, _ in top_positive],
            "top_negative_words": [kw for kw, _ in top_negative],
            "analyzed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[{ticker}] 감성 분석 완료: {overall} "
            f"(긍정={positive_count}, 부정={negative_count}, 중립={neutral_count})"
        )
        return result

    @staticmethod
    def _classify_sentiment(text: str) -> str:
        """
        단일 텍스트(뉴스 제목)의 감성을 분류한다.

        Returns:
            "positive" | "negative" | "neutral"
        """
        pos_score = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
        neg_score = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

        if pos_score > neg_score:
            return "positive"
        elif neg_score > pos_score:
            return "negative"
        return "neutral"

    # ----------------------------------------------------------
    # 4. 시뮬레이션 입력 텍스트 생성
    # ----------------------------------------------------------

    def prepare_simulation_input(
        self,
        ticker: str,
        company_name: str,
        days: int = 7,
    ) -> str:
        """
        뉴스, 재무 데이터, 감성 분석 결과를 종합하여
        MiroFish 시뮬레이션 입력 텍스트(Markdown 형식)로 변환한다.

        Args:
            ticker:       종목 코드 (예: "005930")
            company_name: 회사명 (예: "삼성전자")
            days:         뉴스 수집 기간 (기본값 7일)

        Returns:
            시뮬레이션에 사용할 구조화된 텍스트
        """
        logger.info(f"[{company_name}({ticker})] 시뮬레이션 입력 데이터 준비 시작")

        # 병렬 수집 (순서대로 호출)
        financial_data = self.collect_financial_data(ticker)
        news_list = self.collect_stock_news(ticker, company_name, days=days)
        sentiment = self.collect_market_sentiment(ticker)

        # ---- 텍스트 조립 ----
        lines: List[str] = []

        # 헤더
        lines.append(f"# {company_name} ({ticker}) 주식 시장 분석 리포트")
        lines.append(f"수집 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}")
        lines.append("")

        # 1. 시장 감성 요약
        sentiment_label_map = {
            "positive": "🟢 긍정적",
            "negative": "🔴 부정적",
            "neutral": "⚪ 중립적",
        }
        overall_label = sentiment_label_map.get(sentiment["overall_sentiment"], "중립")

        lines.append("## 1. 시장 감성 요약")
        lines.append(f"- 전반적 시장 감성: **{overall_label}**")
        lines.append(f"- 감성 점수: {sentiment['sentiment_score']:.2f} (-1.0 ~ 1.0)")
        lines.append(
            f"- 분석 뉴스 수: 총 {sentiment['total_articles']}건 "
            f"(긍정 {sentiment['positive_count']}건 / "
            f"부정 {sentiment['negative_count']}건 / "
            f"중립 {sentiment['neutral_count']}건)"
        )
        if sentiment["top_positive_words"]:
            lines.append(
                f"- 주요 긍정 키워드: {', '.join(sentiment['top_positive_words'])}"
            )
        if sentiment["top_negative_words"]:
            lines.append(
                f"- 주요 부정 키워드: {', '.join(sentiment['top_negative_words'])}"
            )
        lines.append("")

        # 2. 재무/주가 현황
        lines.append("## 2. 재무 및 주가 현황")
        if financial_data["current_price"] is not None:
            price_str = f"{financial_data['current_price']:,.0f}원"
            change_str = ""
            if financial_data["price_change"] is not None:
                change_val = financial_data["price_change"]
                sign = "+" if change_val >= 0 else ""
                change_str = f" ({sign}{change_val:.2f}%)"
            lines.append(f"- 현재 주가: **{price_str}{change_str}**")
        else:
            lines.append("- 현재 주가: 데이터 없음")

        if financial_data["volume"] is not None:
            lines.append(f"- 거래량: {financial_data['volume']:,}주")

        if financial_data["market_cap"] is not None:
            lines.append(f"- 시가총액: {financial_data['market_cap']:,}억원")

        # 밸류에이션 지표
        valuation_parts = []
        if financial_data["per"] is not None:
            valuation_parts.append(f"PER {financial_data['per']:.1f}배")
        if financial_data["pbr"] is not None:
            valuation_parts.append(f"PBR {financial_data['pbr']:.2f}배")
        if financial_data["div"] is not None:
            valuation_parts.append(f"배당수익률 {financial_data['div']:.2f}%")
        if valuation_parts:
            lines.append(f"- 밸류에이션: {' | '.join(valuation_parts)}")

        # 최근 주가 추이 (최근 5일)
        if financial_data["price_history"]:
            recent_history = financial_data["price_history"][-5:]
            lines.append("- 최근 주가 추이 (종가 기준):")
            for day in recent_history:
                lines.append(
                    f"  - {day['date']}: {day['close']:,.0f}원 "
                    f"(거래량 {day['volume']:,}주)"
                )
        lines.append("")

        # 3. 최근 뉴스
        lines.append(f"## 3. 최근 주요 뉴스 (최근 {days}일)")
        if news_list:
            # 뉴스 감성에 따라 구분 출력
            pos_news = [n for n in news_list if self._classify_sentiment(n["title"]) == "positive"]
            neg_news = [n for n in news_list if self._classify_sentiment(n["title"]) == "negative"]
            neu_news = [n for n in news_list if self._classify_sentiment(n["title"]) == "neutral"]

            # 최대 5건씩 출력
            for label, items in [
                ("### 3-1. 긍정 뉴스", pos_news[:5]),
                ("### 3-2. 부정 뉴스", neg_news[:5]),
                ("### 3-3. 중립 뉴스", neu_news[:5]),
            ]:
                if items:
                    lines.append(label)
                    for news in items:
                        lines.append(
                            f"- [{news['date']}] **{news['title']}** "
                            f"({news['source']})"
                        )
                    lines.append("")
        else:
            lines.append("- 수집된 뉴스가 없습니다.")
            lines.append("")

        # 4. 시뮬레이션 컨텍스트
        lines.append("## 4. 시뮬레이션 컨텍스트")
        lines.append(
            f"{company_name}은(는) 한국 주식 시장(KOSPI/KOSDAQ)에 상장된 기업입니다. "
            f"현재 시장에서 {overall_label} 분위기가 형성되어 있으며, "
            f"다양한 시장 참여자(애널리스트, 기관투자자, 개인투자자, 외국인투자자, 언론)들이 "
            f"이 종목에 대해 활발히 의견을 나누고 있습니다."
        )
        lines.append("")
        lines.append(
            "에이전트들은 위 뉴스와 재무 데이터를 바탕으로 투자 결정을 내리고, "
            "시장 여론을 형성하며, 서로의 의견에 반응합니다."
        )
        lines.append("")

        result_text = "\n".join(lines)
        logger.info(
            f"[{company_name}({ticker})] 시뮬레이션 입력 텍스트 생성 완료 "
            f"(길이: {len(result_text)}자)"
        )
        return result_text
