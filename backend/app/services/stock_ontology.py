"""
주식 시장 시뮬레이션을 위한 온톨로지 정의

MiroFish의 ontology_generator.py 패턴을 참고하여,
한국 주식 시장(KOSPI/KOSDAQ) 시뮬레이션에 특화된
엔티티 타입과 관계(엣지) 타입을 정적으로 정의한다.

온톨로지 구성:
  - entity_types: 10개 (구체 타입 8개 + 범용 폴백 2개)
  - edge_types:   8개
"""

from typing import Dict, List, Any


# ============================================================
# 엔티티 타입 정의
# ============================================================

# 1. 증권사 애널리스트
ANALYST_ENTITY = {
    "name": "Analyst",
    "description": "Securities firm analyst who provides stock ratings and target prices.",
    "attributes": [
        {
            "name": "full_name",
            "type": "text",
            "description": "Full name of the analyst",
        },
        {
            "name": "firm",
            "type": "text",
            "description": "Securities firm the analyst belongs to (e.g., 미래에셋, 삼성증권)",
        },
        {
            "name": "coverage_sector",
            "type": "text",
            "description": "Industry sector covered by the analyst",
        },
    ],
    "examples": ["미래에셋 반도체 담당 애널리스트", "삼성증권 IT 리서치팀"],
}

# 2. 개인/기관 투자자
INVESTOR_ENTITY = {
    "name": "Investor",
    "description": "Individual or institutional investor participating in KOSPI/KOSDAQ markets.",
    "attributes": [
        {
            "name": "investor_type",
            "type": "text",
            "description": "Type of investor: 개인투자자 (retail) or 기관투자자 (institutional)",
        },
        {
            "name": "investment_style",
            "type": "text",
            "description": "Investment style: 가치투자, 성장투자, 단기매매, 장기투자 등",
        },
    ],
    "examples": ["개인 주식 투자자", "국민연금 주식운용팀", "한국투자신탁운용"],
}

# 3. 기업 임원/CEO
COMPANY_EXECUTIVE_ENTITY = {
    "name": "CompanyExecutive",
    "description": "Executive or CEO of a listed Korean company who influences investor sentiment.",
    "attributes": [
        {
            "name": "full_name",
            "type": "text",
            "description": "Full name of the executive",
        },
        {
            "name": "position",
            "type": "text",
            "description": "Executive position: CEO, CFO, CSO 등",
        },
        {
            "name": "company_ticker",
            "type": "text",
            "description": "Stock ticker of the company they manage",
        },
    ],
    "examples": ["삼성전자 CEO", "카카오 대표이사", "현대차 CFO"],
}

# 4. 규제기관 (금융감독원, 한국은행 등)
REGULATOR_ENTITY = {
    "name": "Regulator",
    "description": "Korean financial regulatory body such as FSS, FSC, or Bank of Korea.",
    "attributes": [
        {
            "name": "org_name",
            "type": "text",
            "description": "Name of the regulatory organization",
        },
        {
            "name": "regulatory_scope",
            "type": "text",
            "description": "Regulatory scope: 증권감독, 통화정책, 공정거래 등",
        },
    ],
    "examples": ["금융감독원(FSS)", "금융위원회(FSC)", "한국은행", "공정거래위원회"],
}

# 5. 경제 언론사
MEDIA_OUTLET_ENTITY = {
    "name": "MediaOutlet",
    "description": "Korean financial media outlet reporting on stocks and market news.",
    "attributes": [
        {
            "name": "org_name",
            "type": "text",
            "description": "Media outlet name",
        },
        {
            "name": "media_type",
            "type": "text",
            "description": "Media type: 신문, 온라인, 방송, 통신사 등",
        },
    ],
    "examples": ["한국경제신문", "매일경제", "조선비즈", "이데일리", "연합인포맥스"],
}

# 6. 외국인 투자자
FOREIGN_INVESTOR_ENTITY = {
    "name": "ForeignInvestor",
    "description": "Foreign investor or institution investing in Korean equity markets.",
    "attributes": [
        {
            "name": "org_name",
            "type": "text",
            "description": "Name of the foreign investment firm or fund",
        },
        {
            "name": "country",
            "type": "text",
            "description": "Home country or region of the investor",
        },
    ],
    "examples": [
        "미국계 헤지펀드",
        "블랙록(BlackRock)",
        "싱가포르 국부펀드(GIC)",
        "뱅가드(Vanguard)",
    ],
}

# 7. 시장조성자/기관
MARKET_MAKER_ENTITY = {
    "name": "MarketMaker",
    "description": "Korean institutional market maker or brokerage providing liquidity.",
    "attributes": [
        {
            "name": "org_name",
            "type": "text",
            "description": "Name of the market maker or brokerage",
        },
        {
            "name": "market_role",
            "type": "text",
            "description": "Role in the market: 유동성공급자, 프로그램매매, 차익거래 등",
        },
    ],
    "examples": ["한국투자증권 트레이딩팀", "KB증권 시장조성", "NH투자증권 ELW 발행"],
}

# 8. 산업 전문가
INDUSTRY_EXPERT_ENTITY = {
    "name": "IndustryExpert",
    "description": "Sector or industry expert providing insights on market trends.",
    "attributes": [
        {
            "name": "full_name",
            "type": "text",
            "description": "Full name of the expert",
        },
        {
            "name": "expertise_field",
            "type": "text",
            "description": "Area of expertise: 반도체, 바이오, 2차전지, 부동산 등",
        },
        {
            "name": "affiliation",
            "type": "text",
            "description": "Affiliated institution (research institute, university, etc.)",
        },
    ],
    "examples": [
        "한국경제연구원 반도체 연구위원",
        "연세대 금융공학 교수",
        "한국전자통신연구원 AI 전문가",
    ],
}

# 9. 범용 개인 폴백
PERSON_FALLBACK_ENTITY = {
    "name": "Person",
    "description": "Any individual person not fitting other specific person types.",
    "attributes": [
        {
            "name": "full_name",
            "type": "text",
            "description": "Full name of the person",
        },
        {
            "name": "role",
            "type": "text",
            "description": "Role or occupation of the person",
        },
    ],
    "examples": ["일반 개인투자자", "주식 블로거", "유튜브 주식 채널 운영자"],
}

# 10. 범용 조직 폴백
ORGANIZATION_FALLBACK_ENTITY = {
    "name": "Organization",
    "description": "Any organization not fitting other specific organization types.",
    "attributes": [
        {
            "name": "org_name",
            "type": "text",
            "description": "Name of the organization",
        },
        {
            "name": "org_type",
            "type": "text",
            "description": "Type of organization",
        },
    ],
    "examples": ["한국거래소(KRX)", "코스콤", "한국예탁결제원"],
}


# ============================================================
# 엣지(관계) 타입 정의
# ============================================================

EDGE_TYPES: List[Dict[str, Any]] = [
    {
        "name": "ANALYZES",
        "description": "Analyst or expert analyzes a company or sector.",
        "source_targets": [
            {"source": "Analyst", "target": "CompanyExecutive"},
            {"source": "IndustryExpert", "target": "Organization"},
            {"source": "Analyst", "target": "Organization"},
        ],
        "attributes": [
            {
                "name": "rating",
                "type": "text",
                "description": "Investment rating: 매수, 중립, 매도 등",
            }
        ],
    },
    {
        "name": "INVESTS_IN",
        "description": "Investor buys or holds a position in a company.",
        "source_targets": [
            {"source": "Investor", "target": "CompanyExecutive"},
            {"source": "ForeignInvestor", "target": "Organization"},
            {"source": "MarketMaker", "target": "Organization"},
            {"source": "Investor", "target": "Organization"},
        ],
        "attributes": [
            {
                "name": "position_type",
                "type": "text",
                "description": "Type of investment position: 매수, 매도, 보유 등",
            }
        ],
    },
    {
        "name": "MANAGES",
        "description": "Executive manages or leads the company strategy.",
        "source_targets": [
            {"source": "CompanyExecutive", "target": "Organization"},
        ],
        "attributes": [
            {
                "name": "tenure",
                "type": "text",
                "description": "Duration in the management role",
            }
        ],
    },
    {
        "name": "REGULATES",
        "description": "Regulatory body oversees or enforces rules on entities.",
        "source_targets": [
            {"source": "Regulator", "target": "Organization"},
            {"source": "Regulator", "target": "MarketMaker"},
            {"source": "Regulator", "target": "Investor"},
            {"source": "Regulator", "target": "ForeignInvestor"},
        ],
        "attributes": [],
    },
    {
        "name": "REPORTS_ON",
        "description": "Media outlet publishes news or reports about an entity.",
        "source_targets": [
            {"source": "MediaOutlet", "target": "CompanyExecutive"},
            {"source": "MediaOutlet", "target": "Organization"},
            {"source": "MediaOutlet", "target": "Regulator"},
            {"source": "MediaOutlet", "target": "Analyst"},
        ],
        "attributes": [
            {
                "name": "sentiment",
                "type": "text",
                "description": "Tone of the report: 긍정, 부정, 중립",
            }
        ],
    },
    {
        "name": "COMPETES_WITH",
        "description": "Two organizations compete in the same market or sector.",
        "source_targets": [
            {"source": "Organization", "target": "Organization"},
            {"source": "CompanyExecutive", "target": "CompanyExecutive"},
        ],
        "attributes": [],
    },
    {
        "name": "INFLUENCES",
        "description": "One entity has significant impact on another's decision or opinion.",
        "source_targets": [
            {"source": "ForeignInvestor", "target": "Investor"},
            {"source": "Analyst", "target": "Investor"},
            {"source": "MediaOutlet", "target": "Person"},
            {"source": "Regulator", "target": "Organization"},
            {"source": "IndustryExpert", "target": "Investor"},
        ],
        "attributes": [
            {
                "name": "influence_type",
                "type": "text",
                "description": "How the influence is exerted: 보고서, 인터뷰, 공시, 뉴스 등",
            }
        ],
    },
    {
        "name": "FOLLOWS",
        "description": "One entity monitors or tracks the actions of another.",
        "source_targets": [
            {"source": "Investor", "target": "Analyst"},
            {"source": "Person", "target": "Analyst"},
            {"source": "Investor", "target": "ForeignInvestor"},
            {"source": "Person", "target": "MediaOutlet"},
        ],
        "attributes": [],
    },
]


# ============================================================
# 온톨로지 생성 함수
# ============================================================

def get_stock_ontology(company_name: str, sector: str) -> Dict[str, Any]:
    """
    한국 주식 시장 시뮬레이션을 위한 온톨로지를 반환한다.

    MiroFish 온톨로지 구조와 동일한 형식(entity_types, edge_types, analysis_summary)으로
    딕셔너리를 구성하여 반환한다.

    Args:
        company_name: 시뮬레이션 대상 기업명 (예: "삼성전자")
        sector:       산업 섹터 (예: "반도체", "바이오", "2차전지")

    Returns:
        {
            "entity_types":      List[Dict],   # 10개 엔티티 타입
            "edge_types":        List[Dict],   # 8개 관계 타입
            "analysis_summary":  str,          # 온톨로지 설명
        }
    """
    # 10개 엔티티 타입 목록 (구체 8개 + 폴백 2개)
    entity_types: List[Dict[str, Any]] = [
        ANALYST_ENTITY,          # 1. 애널리스트
        INVESTOR_ENTITY,         # 2. 투자자
        COMPANY_EXECUTIVE_ENTITY,  # 3. 기업 임원
        REGULATOR_ENTITY,        # 4. 규제기관
        MEDIA_OUTLET_ENTITY,     # 5. 언론사
        FOREIGN_INVESTOR_ENTITY, # 6. 외국인 투자자
        MARKET_MAKER_ENTITY,     # 7. 시장조성자
        INDUSTRY_EXPERT_ENTITY,  # 8. 산업 전문가
        PERSON_FALLBACK_ENTITY,  # 9. 범용 개인 폴백
        ORGANIZATION_FALLBACK_ENTITY,  # 10. 범용 조직 폴백
    ]

    # 분석 요약 (기업명과 섹터를 반영)
    analysis_summary = (
        f"한국 주식 시장 시뮬레이션 온톨로지입니다. "
        f"'{company_name}' ({sector} 섹터)를 중심으로, "
        f"시장 참여자(애널리스트, 기관/개인/외국인 투자자, 기업 임원, 규제기관, 언론사, 산업 전문가)가 "
        f"뉴스와 재무 데이터에 반응하며 투자 결정을 내리는 시뮬레이션에 사용됩니다. "
        f"각 에이전트는 자신의 역할과 정보에 따라 매수/매도/보유 의견을 표명하고 "
        f"다른 참여자들에게 영향을 미칩니다."
    )

    return {
        "entity_types": entity_types,
        "edge_types": EDGE_TYPES,
        "analysis_summary": analysis_summary,
    }


# ============================================================
# 엔티티 타입 조회 헬퍼
# ============================================================

def get_entity_type_names() -> List[str]:
    """온톨로지에 정의된 모든 엔티티 타입 이름 목록을 반환한다."""
    ontology = get_stock_ontology("", "")
    return [et["name"] for et in ontology["entity_types"]]


def get_edge_type_names() -> List[str]:
    """온톨로지에 정의된 모든 엣지 타입 이름 목록을 반환한다."""
    return [et["name"] for et in EDGE_TYPES]
