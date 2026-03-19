"""
한국 주식 예측 전용 API 라우트
종목 분석, 시뮬레이션, 보고서 생성 등 주식 예측 관련 엔드포인트를 제공합니다.
"""

import uuid
import traceback
import threading
from flask import request, jsonify

from flask import Blueprint
stock_bp = Blueprint('stock', __name__, url_prefix='/api/stock')

from ..config import Config
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..services.stock_report_agent import StockReportAgent, StockReportManager, StockReportStatus
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.stock')


# ============== 종목 분석 인터페이스 ==============

@stock_bp.route('/analyze', methods=['POST'])
def start_analysis():
    """
    종목 분석 시작 (비동기 작업)

    주식 종목을 분석하기 위해 데이터 수집, 온톨로지 생성, 그래프 빌드를 순차 실행합니다.
    작업이 즉시 task_id를 반환하며, 진행 상태는 /analyze/<task_id>/status로 확인합니다.

    요청 (JSON):
        {
            "ticker": "005930",          // 필수, 종목 코드 (예: 삼성전자 005930)
            "company_name": "삼성전자",   // 필수, 회사명
            "period": "1y"               // 선택, 데이터 수집 기간 (기본값: 1y)
        }

    반환:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "ticker": "005930",
                "company_name": "삼성전자",
                "status": "pending",
                "message": "종목 분석 작업이 시작되었습니다"
            }
        }
    """
    try:
        data = request.get_json() or {}

        # 필수 파라미터 검증
        ticker = data.get('ticker')
        company_name = data.get('company_name')
        period = data.get('period', '1y')

        if not ticker:
            return jsonify({
                "success": False,
                "error": "ticker(종목 코드)를 입력해 주세요"
            }), 400

        if not company_name:
            return jsonify({
                "success": False,
                "error": "company_name(회사명)을 입력해 주세요"
            }), 400

        # 비동기 작업 생성
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="stock_analyze",
            metadata={
                "ticker": ticker,
                "company_name": company_name,
                "period": period
            }
        )

        # 백그라운드 작업 정의
        def run_analysis():
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="주식 데이터 수집 초기화 중..."
                )

                # 1단계: 주식 데이터 수집 (pykrx 활용)
                task_manager.update_task(
                    task_id,
                    progress=10,
                    message=f"[{ticker}] 주가 및 재무 데이터 수집 중..."
                )

                try:
                    from pykrx import stock as krx_stock
                    import pandas as pd
                    from datetime import datetime, timedelta

                    # 기간 계산
                    end_date = datetime.now().strftime("%Y%m%d")
                    if period == '1y':
                        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                    elif period == '6m':
                        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
                    elif period == '3m':
                        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
                    else:
                        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

                    # OHLCV 데이터 수집
                    ohlcv_df = krx_stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
                    ohlcv_data = ohlcv_df.reset_index().to_dict(orient='records') if not ohlcv_df.empty else []

                    # 시가총액 데이터 수집
                    cap_df = krx_stock.get_market_cap_by_date(start_date, end_date, ticker)
                    cap_data = cap_df.reset_index().to_dict(orient='records') if not cap_df.empty else []

                    # 재무 데이터 수집 (가능한 경우)
                    try:
                        fundamental_df = krx_stock.get_market_fundamental_by_date(
                            start_date, end_date, ticker
                        )
                        fundamental_data = fundamental_df.reset_index().to_dict(orient='records') if not fundamental_df.empty else []
                    except Exception:
                        fundamental_data = []

                    financial_data = {
                        "ticker": ticker,
                        "company_name": company_name,
                        "period": period,
                        "start_date": start_date,
                        "end_date": end_date,
                        "ohlcv": ohlcv_data,
                        "market_cap": cap_data,
                        "fundamental": fundamental_data
                    }

                    # 날짜 직렬화 처리
                    import json
                    def default_serializer(obj):
                        if hasattr(obj, 'isoformat'):
                            return obj.isoformat()
                        return str(obj)

                    financial_data_str = json.dumps(financial_data, default=default_serializer, ensure_ascii=False)
                    financial_data = json.loads(financial_data_str)

                    logger.info(f"[{task_id}] {ticker} 데이터 수집 완료: OHLCV {len(ohlcv_data)}건")

                except ImportError:
                    logger.warning(f"[{task_id}] pykrx 미설치 - 빈 데이터로 진행")
                    financial_data = {
                        "ticker": ticker,
                        "company_name": company_name,
                        "period": period,
                        "ohlcv": [],
                        "market_cap": [],
                        "fundamental": [],
                        "warning": "pykrx 라이브러리가 설치되지 않아 실제 데이터를 가져오지 못했습니다"
                    }
                except Exception as e:
                    logger.warning(f"[{task_id}] 데이터 수집 부분 실패: {str(e)}")
                    financial_data = {
                        "ticker": ticker,
                        "company_name": company_name,
                        "period": period,
                        "ohlcv": [],
                        "market_cap": [],
                        "fundamental": [],
                        "error": str(e)
                    }

                task_manager.update_task(
                    task_id,
                    progress=40,
                    message="온톨로지 생성 중..."
                )

                # 2단계: 주식 분석용 온톨로지 생성
                ontology = _generate_stock_ontology(ticker, company_name)

                task_manager.update_task(
                    task_id,
                    progress=70,
                    message="분석 데이터 저장 중..."
                )

                # 3단계: 분석 결과를 파일에 저장
                import os
                import json

                analysis_dir = os.path.join(
                    Config.UPLOAD_FOLDER, 'stock_analyses', task_id
                )
                os.makedirs(analysis_dir, exist_ok=True)

                analysis_result = {
                    "task_id": task_id,
                    "ticker": ticker,
                    "company_name": company_name,
                    "period": period,
                    "ontology": ontology,
                    "financial_data": financial_data,
                    "status": "completed"
                }

                with open(os.path.join(analysis_dir, 'analysis.json'), 'w', encoding='utf-8') as f:
                    json.dump(analysis_result, f, ensure_ascii=False, indent=2)

                logger.info(f"[{task_id}] 종목 분석 완료: {ticker} ({company_name})")

                task_manager.complete_task(
                    task_id,
                    result={
                        "task_id": task_id,
                        "ticker": ticker,
                        "company_name": company_name,
                        "analysis_dir": analysis_dir,
                        "ontology_entity_types": len(ontology.get("entity_types", [])),
                        "data_points": len(financial_data.get("ohlcv", []))
                    }
                )

            except Exception as e:
                logger.error(f"[{task_id}] 종목 분석 실패: {str(e)}")
                logger.error(traceback.format_exc())
                task_manager.fail_task(task_id, str(e))

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "ticker": ticker,
                "company_name": company_name,
                "status": "pending",
                "message": f"{company_name}({ticker}) 종목 분석 작업이 시작되었습니다. "
                           f"/api/stock/analyze/{task_id}/status 로 진행 상태를 확인하세요."
            }
        })

    except Exception as e:
        logger.error(f"종목 분석 시작 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@stock_bp.route('/analyze/<task_id>/status', methods=['GET'])
def get_analysis_status(task_id: str):
    """
    종목 분석 진행 상태 확인

    반환:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|failed",
                "progress": 60,
                "message": "온톨로지 생성 중...",
                "result": { ... }   // 완료 시에만 포함
            }
        }
    """
    try:
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

        if not task:
            return jsonify({
                "success": False,
                "error": f"작업을 찾을 수 없습니다: {task_id}"
            }), 404

        return jsonify({
            "success": True,
            "data": task.to_dict()
        })

    except Exception as e:
        logger.error(f"분석 상태 조회 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== 시뮬레이션 인터페이스 ==============

@stock_bp.route('/simulate', methods=['POST'])
def start_simulation():
    """
    주식 예측 시뮬레이션 시작 (비동기 작업)

    종목 분석 결과(task_id)를 기반으로 에이전트 시뮬레이션을 실행합니다.

    요청 (JSON):
        {
            "task_id": "task_xxxx",       // 필수, analyze 엔드포인트에서 반환한 task_id
            "num_agents": 50,              // 선택, 에이전트 수 (기본값: 50)
            "simulation_rounds": 10        // 선택, 시뮬레이션 라운드 수 (기본값: 10)
        }

    반환:
        {
            "success": true,
            "data": {
                "simulation_id": "stock_sim_xxxx",
                "task_id": "task_xxxx",
                "status": "pending",
                "message": "시뮬레이션 작업이 시작되었습니다"
            }
        }
    """
    try:
        data = request.get_json() or {}

        # 필수 파라미터 검증
        task_id = data.get('task_id')
        if not task_id:
            return jsonify({
                "success": False,
                "error": "task_id(분석 작업 ID)를 입력해 주세요"
            }), 400

        num_agents = data.get('num_agents', 50)
        simulation_rounds = data.get('simulation_rounds', 10)

        # 분석 작업 결과 확인
        task_manager = TaskManager()
        analysis_task = task_manager.get_task(task_id)

        if not analysis_task:
            return jsonify({
                "success": False,
                "error": f"분석 작업을 찾을 수 없습니다: {task_id}"
            }), 404

        if analysis_task.status.value != 'completed':
            return jsonify({
                "success": False,
                "error": f"분석이 아직 완료되지 않았습니다. 현재 상태: {analysis_task.status.value}"
            }), 400

        # 분석 결과 로드
        import os
        import json

        analysis_dir = os.path.join(Config.UPLOAD_FOLDER, 'stock_analyses', task_id)
        analysis_file = os.path.join(analysis_dir, 'analysis.json')

        if not os.path.exists(analysis_file):
            return jsonify({
                "success": False,
                "error": "분석 결과 파일을 찾을 수 없습니다"
            }), 404

        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)

        ticker = analysis_data.get('ticker', '')
        company_name = analysis_data.get('company_name', '')

        # 시뮬레이션 ID 생성
        simulation_id = f"stock_sim_{uuid.uuid4().hex[:12]}"

        # 시뮬레이션 메타데이터 저장
        sim_dir = os.path.join(Config.UPLOAD_FOLDER, 'stock_simulations', simulation_id)
        os.makedirs(sim_dir, exist_ok=True)

        sim_meta = {
            "simulation_id": simulation_id,
            "task_id": task_id,
            "ticker": ticker,
            "company_name": company_name,
            "num_agents": num_agents,
            "simulation_rounds": simulation_rounds,
            "status": "pending",
            "created_at": __import__('datetime').datetime.now().isoformat()
        }

        with open(os.path.join(sim_dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(sim_meta, f, ensure_ascii=False, indent=2)

        # 시뮬레이션 작업 생성
        sim_task_id = task_manager.create_task(
            task_type="stock_simulate",
            metadata={
                "simulation_id": simulation_id,
                "ticker": ticker,
                "company_name": company_name,
                "task_id": task_id
            }
        )

        # 백그라운드 시뮬레이션 실행
        def run_simulation():
            try:
                task_manager.update_task(
                    sim_task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="에이전트 시뮬레이션 초기화 중..."
                )

                financial_data = analysis_data.get('financial_data', {})
                ohlcv = financial_data.get('ohlcv', [])

                # 에이전트별 투자 결정 시뮬레이션
                import random
                agents_decisions = []

                for i in range(num_agents):
                    # 에이전트 유형 (투자 성향)
                    agent_type = random.choice(['conservative', 'moderate', 'aggressive'])

                    # 주가 추세 기반 결정 로직
                    if len(ohlcv) >= 2:
                        # 최근 데이터를 기반으로 추세 계산
                        try:
                            recent_prices = [
                                float(row.get('종가', row.get('close', 0)) or 0)
                                for row in ohlcv[-20:]
                                if row.get('종가', row.get('close', 0))
                            ]
                            if len(recent_prices) >= 2:
                                price_change_pct = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
                            else:
                                price_change_pct = 0
                        except Exception:
                            price_change_pct = 0
                    else:
                        price_change_pct = 0

                    # 에이전트 성향에 따른 확률 조정
                    base_buy_prob = 0.33 + (price_change_pct * 0.01)
                    base_sell_prob = 0.33 - (price_change_pct * 0.01)

                    if agent_type == 'aggressive':
                        buy_prob = min(0.7, base_buy_prob + 0.15)
                        sell_prob = max(0.1, base_sell_prob - 0.05)
                    elif agent_type == 'conservative':
                        buy_prob = max(0.1, base_buy_prob - 0.1)
                        sell_prob = min(0.5, base_sell_prob + 0.1)
                    else:
                        buy_prob = max(0.15, min(0.65, base_buy_prob))
                        sell_prob = max(0.15, min(0.5, base_sell_prob))

                    hold_prob = max(0.05, 1.0 - buy_prob - sell_prob)

                    # 정규화
                    total = buy_prob + sell_prob + hold_prob
                    buy_prob /= total
                    sell_prob /= total
                    hold_prob /= total

                    rand = random.random()
                    if rand < buy_prob:
                        decision = 'buy'
                    elif rand < buy_prob + sell_prob:
                        decision = 'sell'
                    else:
                        decision = 'hold'

                    agents_decisions.append({
                        "agent_id": f"agent_{i+1:04d}",
                        "agent_type": agent_type,
                        "decision": decision,
                        "confidence": round(random.uniform(0.5, 0.95), 2),
                        "reasoning": f"{agent_type} 성향 에이전트의 {decision} 결정"
                    })

                    # 진행률 업데이트 (10% 단위)
                    if (i + 1) % max(1, num_agents // 10) == 0:
                        progress = int((i + 1) / num_agents * 80)
                        task_manager.update_task(
                            sim_task_id,
                            progress=progress,
                            message=f"에이전트 시뮬레이션 진행 중... ({i+1}/{num_agents})"
                        )

                task_manager.update_task(
                    sim_task_id,
                    progress=90,
                    message="시뮬레이션 결과 집계 중..."
                )

                # 집계 결과 계산
                buy_count = sum(1 for d in agents_decisions if d['decision'] == 'buy')
                sell_count = sum(1 for d in agents_decisions if d['decision'] == 'sell')
                hold_count = sum(1 for d in agents_decisions if d['decision'] == 'hold')

                simulation_result = {
                    "simulation_id": simulation_id,
                    "task_id": task_id,
                    "ticker": ticker,
                    "company_name": company_name,
                    "num_agents": num_agents,
                    "simulation_rounds": simulation_rounds,
                    "agents_decisions": agents_decisions,
                    "summary": {
                        "buy_count": buy_count,
                        "sell_count": sell_count,
                        "hold_count": hold_count,
                        "buy_pct": round(buy_count / num_agents * 100, 1),
                        "sell_pct": round(sell_count / num_agents * 100, 1),
                        "hold_pct": round(hold_count / num_agents * 100, 1)
                    },
                    "financial_data_summary": {
                        "ohlcv_count": len(ohlcv),
                        "ticker": ticker
                    },
                    "status": "completed",
                    "completed_at": __import__('datetime').datetime.now().isoformat()
                }

                # 결과 저장
                with open(os.path.join(sim_dir, 'result.json'), 'w', encoding='utf-8') as f:
                    json.dump(simulation_result, f, ensure_ascii=False, indent=2)

                # 메타데이터 업데이트
                sim_meta['status'] = 'completed'
                with open(os.path.join(sim_dir, 'meta.json'), 'w', encoding='utf-8') as f:
                    json.dump(sim_meta, f, ensure_ascii=False, indent=2)

                logger.info(f"[{simulation_id}] 시뮬레이션 완료: 매수 {buy_count}, 매도 {sell_count}, 보합 {hold_count}")

                task_manager.complete_task(
                    sim_task_id,
                    result={
                        "simulation_id": simulation_id,
                        "ticker": ticker,
                        "company_name": company_name,
                        "summary": simulation_result["summary"]
                    }
                )

            except Exception as e:
                logger.error(f"[{simulation_id}] 시뮬레이션 실패: {str(e)}")
                logger.error(traceback.format_exc())
                task_manager.fail_task(sim_task_id, str(e))

                # 메타데이터 실패 상태 업데이트
                try:
                    sim_meta['status'] = 'failed'
                    sim_meta['error'] = str(e)
                    with open(os.path.join(sim_dir, 'meta.json'), 'w', encoding='utf-8') as f:
                        json.dump(sim_meta, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=run_simulation, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "sim_task_id": sim_task_id,
                "task_id": task_id,
                "ticker": ticker,
                "company_name": company_name,
                "status": "pending",
                "message": f"{company_name}({ticker}) 시뮬레이션이 시작되었습니다. "
                           f"/api/stock/simulate/{simulation_id}/status 로 진행 상태를 확인하세요."
            }
        })

    except Exception as e:
        logger.error(f"시뮬레이션 시작 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@stock_bp.route('/simulate/<simulation_id>/status', methods=['GET'])
def get_simulation_status(simulation_id: str):
    """
    시뮬레이션 진행 상태 확인

    반환:
        {
            "success": true,
            "data": {
                "simulation_id": "stock_sim_xxxx",
                "status": "pending|running|completed|failed",
                "ticker": "005930",
                "company_name": "삼성전자",
                "summary": {
                    "buy_pct": 45.0,
                    "sell_pct": 30.0,
                    "hold_pct": 25.0
                }
            }
        }
    """
    try:
        import os
        import json

        sim_dir = os.path.join(Config.UPLOAD_FOLDER, 'stock_simulations', simulation_id)
        meta_file = os.path.join(sim_dir, 'meta.json')

        if not os.path.exists(meta_file):
            return jsonify({
                "success": False,
                "error": f"시뮬레이션을 찾을 수 없습니다: {simulation_id}"
            }), 404

        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        # 완료된 경우 결과 포함
        result_file = os.path.join(sim_dir, 'result.json')
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            meta['summary'] = result.get('summary', {})
            meta['num_agents'] = result.get('num_agents', 0)

        return jsonify({
            "success": True,
            "data": meta
        })

    except Exception as e:
        logger.error(f"시뮬레이션 상태 조회 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== 예측 보고서 인터페이스 ==============

@stock_bp.route('/report/<simulation_id>', methods=['POST'])
def generate_report(simulation_id: str):
    """
    주식 예측 보고서 생성 (비동기 작업)

    시뮬레이션 결과를 분석하여 투자 예측 보고서를 생성합니다.

    요청 (JSON):
        {
            "force_regenerate": false   // 선택, 기존 보고서 강제 재생성 여부 (기본값: false)
        }

    반환:
        {
            "success": true,
            "data": {
                "report_id": "stock_report_xxxx",
                "simulation_id": "stock_sim_xxxx",
                "task_id": "task_xxxx",
                "status": "generating",
                "message": "보고서 생성 작업이 시작되었습니다"
            }
        }
    """
    try:
        import os
        import json

        data = request.get_json() or {}
        force_regenerate = data.get('force_regenerate', False)

        # 시뮬레이션 결과 확인
        sim_dir = os.path.join(Config.UPLOAD_FOLDER, 'stock_simulations', simulation_id)
        result_file = os.path.join(sim_dir, 'result.json')

        if not os.path.exists(result_file):
            return jsonify({
                "success": False,
                "error": f"시뮬레이션 결과를 찾을 수 없습니다. 시뮬레이션이 완료되었는지 확인해 주세요: {simulation_id}"
            }), 404

        with open(result_file, 'r', encoding='utf-8') as f:
            simulation_data = json.load(f)

        ticker = simulation_data.get('ticker', '')
        company_name = simulation_data.get('company_name', '')
        task_id = simulation_data.get('task_id', '')

        # 기존 보고서 확인
        if not force_regenerate:
            existing_report = StockReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.get('status') == StockReportStatus.COMPLETED.value:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report['report_id'],
                        "status": "completed",
                        "message": "이미 생성된 보고서가 있습니다",
                        "already_generated": True
                    }
                })

        # 분석 데이터 로드
        analysis_dir = os.path.join(Config.UPLOAD_FOLDER, 'stock_analyses', task_id)
        analysis_file = os.path.join(analysis_dir, 'analysis.json')
        financial_data = {}

        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            financial_data = analysis_data.get('financial_data', {})

        # 보고서 ID 사전 생성 (즉시 반환을 위해)
        report_id = f"stock_report_{uuid.uuid4().hex[:12]}"

        # 비동기 작업 생성
        task_manager = TaskManager()
        report_task_id = task_manager.create_task(
            task_type="stock_report_generate",
            metadata={
                "report_id": report_id,
                "simulation_id": simulation_id,
                "ticker": ticker,
                "company_name": company_name
            }
        )

        # 백그라운드 보고서 생성
        def run_report_generation():
            try:
                task_manager.update_task(
                    report_task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="StockReportAgent 초기화 중..."
                )

                # 진행률 콜백
                def progress_callback(stage: str, progress: int, message: str):
                    task_manager.update_task(
                        report_task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )

                # StockReportAgent 실행
                agent = StockReportAgent()
                report = agent.generate_report(
                    simulation_id=simulation_id,
                    ticker=ticker,
                    company_name=company_name,
                    simulation_data=simulation_data,
                    financial_data=financial_data,
                    report_id=report_id,
                    progress_callback=progress_callback
                )

                # 보고서 저장
                StockReportManager.save_report(report)

                if report.get('status') == StockReportStatus.COMPLETED.value:
                    task_manager.complete_task(
                        report_task_id,
                        result={
                            "report_id": report_id,
                            "simulation_id": simulation_id,
                            "ticker": ticker,
                            "company_name": company_name,
                            "status": "completed"
                        }
                    )
                    logger.info(f"[{report_id}] 보고서 생성 완료: {ticker} ({company_name})")
                else:
                    error_msg = report.get('error', '보고서 생성 실패')
                    task_manager.fail_task(report_task_id, error_msg)

            except Exception as e:
                logger.error(f"[{report_id}] 보고서 생성 실패: {str(e)}")
                logger.error(traceback.format_exc())
                task_manager.fail_task(report_task_id, str(e))

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=run_report_generation, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "simulation_id": simulation_id,
                "task_id": report_task_id,
                "ticker": ticker,
                "company_name": company_name,
                "status": "generating",
                "message": f"보고서 생성이 시작되었습니다. "
                           f"/api/stock/report/{report_id} 로 보고서를 조회하세요.",
                "already_generated": False
            }
        })

    except Exception as e:
        logger.error(f"보고서 생성 시작 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@stock_bp.route('/report/<report_id>', methods=['GET'])
def get_report(report_id: str):
    """
    주식 예측 보고서 조회

    반환:
        {
            "success": true,
            "data": {
                "report_id": "stock_report_xxxx",
                "simulation_id": "stock_sim_xxxx",
                "ticker": "005930",
                "company_name": "삼성전자",
                "status": "completed",
                "sections": {
                    "overview": "...",
                    "simulation_summary": "...",
                    "sentiment_analysis": "...",
                    "technical_analysis": "...",
                    "consensus_forecast": "...",
                    "risk_factors": "...",
                    "investment_opinion": "..."
                },
                "markdown_content": "...",
                "created_at": "...",
                "disclaimer": "본 보고서는 AI 시뮬레이션 결과이며 투자 조언이 아닙니다"
            }
        }
    """
    try:
        report = StockReportManager.get_report(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error": f"보고서를 찾을 수 없습니다: {report_id}"
            }), 404

        return jsonify({
            "success": True,
            "data": report
        })

    except Exception as e:
        logger.error(f"보고서 조회 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 종목 검색 인터페이스 ==============

@stock_bp.route('/search', methods=['GET'])
def search_stocks():
    """
    한국 주식 종목 검색 (pykrx 활용)

    Query 파라미터:
        query: 검색어 (종목명 또는 종목 코드)
        market: 시장 구분 (KOSPI|KOSDAQ|ALL, 기본값: ALL)
        limit: 반환 최대 건수 (기본값: 20)

    반환:
        {
            "success": true,
            "data": [
                {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "market": "KOSPI"
                },
                ...
            ],
            "count": 5
        }
    """
    try:
        query = request.args.get('query', '').strip()
        market = request.args.get('market', 'ALL').upper()
        limit = request.args.get('limit', 20, type=int)

        if not query:
            return jsonify({
                "success": False,
                "error": "검색어(query)를 입력해 주세요"
            }), 400

        results = []

        try:
            from pykrx import stock as krx_stock
            from datetime import datetime, timedelta

            # 최신 거래일 날짜 (어제)
            base_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

            # 시장별 종목 목록 조회
            markets_to_search = []
            if market in ('KOSPI', 'ALL'):
                markets_to_search.append('KOSPI')
            if market in ('KOSDAQ', 'ALL'):
                markets_to_search.append('KOSDAQ')

            for mkt in markets_to_search:
                try:
                    tickers = krx_stock.get_market_ticker_list(base_date, market=mkt)
                    for ticker_code in tickers:
                        try:
                            name = krx_stock.get_market_ticker_name(ticker_code)
                            # 검색어 매칭 (종목명 또는 코드)
                            if (query.lower() in name.lower() or
                                    query in ticker_code):
                                results.append({
                                    "ticker": ticker_code,
                                    "name": name,
                                    "market": mkt
                                })
                                if len(results) >= limit:
                                    break
                        except Exception:
                            continue
                except Exception as e:
                    logger.warning(f"[{mkt}] 종목 목록 조회 실패: {str(e)}")
                    continue

                if len(results) >= limit:
                    break

        except ImportError:
            logger.warning("pykrx 미설치 - 종목 검색 불가")
            return jsonify({
                "success": False,
                "error": "pykrx 라이브러리가 설치되지 않아 종목 검색을 사용할 수 없습니다. "
                         "'pip install pykrx'를 실행해 주세요."
            }), 503

        return jsonify({
            "success": True,
            "data": results[:limit],
            "count": len(results[:limit]),
            "query": query,
            "market": market
        })

    except Exception as e:
        logger.error(f"종목 검색 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 내부 유틸리티 함수 ==============

def _generate_stock_ontology(ticker: str, company_name: str) -> dict:
    """
    주식 분석을 위한 온톨로지 생성

    Args:
        ticker: 종목 코드
        company_name: 회사명

    Returns:
        온톨로지 딕셔너리 (entity_types, edge_types 포함)
    """
    return {
        "entity_types": [
            {
                "name": "Company",
                "description": f"{company_name}({ticker}) 및 관련 기업",
                "examples": [company_name, "경쟁사", "협력사"]
            },
            {
                "name": "Investor",
                "description": "개인 투자자 및 기관 투자자",
                "examples": ["개인투자자", "외국인투자자", "기관투자자"]
            },
            {
                "name": "FinancialMetric",
                "description": "재무 지표 및 주가 지표",
                "examples": ["PER", "PBR", "ROE", "EPS", "주가수익률"]
            },
            {
                "name": "MarketEvent",
                "description": "시장 이벤트 및 뉴스",
                "examples": ["실적발표", "배당공시", "유상증자", "대외경제이슈"]
            },
            {
                "name": "Sector",
                "description": "산업 섹터 및 업종",
                "examples": ["반도체", "전자", "IT", "금융"]
            }
        ],
        "edge_types": [
            {
                "name": "INVESTS_IN",
                "description": "투자자가 종목에 투자하는 관계",
                "source": "Investor",
                "target": "Company"
            },
            {
                "name": "AFFECTS",
                "description": "시장 이벤트가 기업 또는 지표에 영향을 주는 관계",
                "source": "MarketEvent",
                "target": "Company"
            },
            {
                "name": "HAS_METRIC",
                "description": "기업이 재무 지표를 보유하는 관계",
                "source": "Company",
                "target": "FinancialMetric"
            },
            {
                "name": "BELONGS_TO",
                "description": "기업이 특정 섹터에 속하는 관계",
                "source": "Company",
                "target": "Sector"
            },
            {
                "name": "COMPETES_WITH",
                "description": "기업 간 경쟁 관계",
                "source": "Company",
                "target": "Company"
            }
        ],
        "description": f"{company_name}({ticker}) 주식 분석 온톨로지"
    }
