"""
API 라우트 모듈
기존 Blueprint(graph, simulation, report)와 주식 예측 Blueprint(stock)를 등록합니다.
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401

# 주식 예측 Blueprint - stock.py 내부에서 정의된 stock_bp를 가져옵니다
from .stock import stock_bp  # noqa: E402, F401
