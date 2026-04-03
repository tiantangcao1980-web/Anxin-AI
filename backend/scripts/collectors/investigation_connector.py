# -*- coding: utf-8 -*-
"""
企业调查数据源连接器

为项目的智能调查功能（investigation_orchestrator.py / due_diligence_service.py）
提供企业信息查询的标准化接口和数据源注册表。

支持的数据源:
  1. 天眼查 API (tianyancha.com)         — 工商信息、股权、诉讼
  2. 企查查 API (qcc.com)                — 企业信息查询
  3. 爱企查 API (aiqicha.baidu.com)      — 百度企业信用
  4. 企业信用公示系统 (gsxt.gov.cn)        — 工商公示信息
  5. 中国执行信息公开网 (zxgk.court.gov.cn)— 执行案件信息
  6. 全国法院失信被执行人 (shixin.court.gov.cn) — 失信名单
  7. 信用中国 (creditchina.gov.cn)        — 信用信息
  8. 中国裁判文书网 (wenshu.court.gov.cn)  — 裁判文书（受限）

注意: 大部分 API 需要付费注册获取 API Key。
本模块仅定义连接器接口和注册表，实际调用在 due_diligence_service.py 中。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class DataSourceType(str, Enum):
    """数据源类型"""
    BUSINESS_REGISTRY = "business_registry"  # 工商注册
    LITIGATION = "litigation"  # 诉讼信息
    CREDIT = "credit"  # 信用信息
    EXECUTION = "execution"  # 执行信息
    PENALTY = "penalty"  # 行政处罚
    DISHONEST = "dishonest"  # 失信名单
    JUDGMENT = "judgment"  # 裁判文书
    COMPREHENSIVE = "comprehensive"  # 综合查询


@dataclass
class InvestigationDataSource:
    """调查数据源定义"""

    name: str  # 数据源名称
    source_type: DataSourceType  # 数据源类型
    base_url: str  # API 基础URL
    api_key_env: str  # API Key 环境变量名
    description: str  # 数据源描述
    rate_limit: float = 1.0  # 每秒最大请求数
    requires_auth: bool = True  # 是否需要认证
    is_free: bool = False  # 是否免费
    endpoints: Dict[str, str] = field(default_factory=dict)  # API 端点
    supported_queries: List[str] = field(default_factory=list)  # 支持的查询类型
    notes: str = ""  # 使用注意事项


# ==================== 数据源注册表 ====================


INVESTIGATION_DATA_SOURCES: List[InvestigationDataSource] = [
    # ---------- 商业 API ----------
    InvestigationDataSource(
        name="天眼查",
        source_type=DataSourceType.COMPREHENSIVE,
        base_url="https://open.api.tianyancha.com",
        api_key_env="TIANYANCHA_API_KEY",
        description="全面的企业信息查询API，涵盖工商、诉讼、知识产权、招投标等",
        rate_limit=10.0,
        endpoints={
            "company_search": "/services/open/search/2.0",
            "company_detail": "/services/open/ic/baseinfoV2/2.0",
            "shareholders": "/services/open/ic/holder/2.0",
            "executives": "/services/open/ic/staff/2.0",
            "lawsuits": "/services/open/jr/lawSuit/3.0",
            "court_notices": "/services/open/jr/courtNoticeV2/2.0",
            "dishonest": "/services/open/jr/dishonest/2.0",
            "penalties": "/services/open/mr/punishmentInfo/3.0",
            "ip_patents": "/services/open/zs/patents/2.0",
            "ip_trademarks": "/services/open/zs/tradeMark/2.0",
        },
        supported_queries=[
            "company_search", "company_detail", "shareholders",
            "executives", "lawsuits", "dishonest", "penalties",
            "ip_patents", "ip_trademarks",
        ],
        notes="需要在 https://open.tianyancha.com 注册并获取API Token",
    ),

    InvestigationDataSource(
        name="企查查",
        source_type=DataSourceType.COMPREHENSIVE,
        base_url="https://api.qichacha.com",
        api_key_env="QICHACHA_API_KEY",
        description="企业工商信息、股权结构、诉讼记录等综合查询",
        rate_limit=5.0,
        endpoints={
            "company_search": "/ECIV4/Search",
            "company_detail": "/ECIV4/GetDetailsByName",
            "shareholders": "/ECIRelation/GetShareHolderInfo",
            "lawsuits": "/JudicialDocV4/SearchShiXin",
        },
        supported_queries=["company_search", "company_detail", "shareholders", "lawsuits"],
        notes="需要在 https://openapi.qcc.com 注册",
    ),

    InvestigationDataSource(
        name="爱企查",
        source_type=DataSourceType.COMPREHENSIVE,
        base_url="https://aiqicha.baidu.com/api",
        api_key_env="AIQICHA_API_KEY",
        description="百度旗下企业信用信息平台",
        rate_limit=5.0,
        endpoints={
            "company_search": "/company/search",
            "company_detail": "/company/detail",
        },
        supported_queries=["company_search", "company_detail"],
        notes="需要百度开发者账号",
    ),

    # ---------- 政府公开数据 ----------
    InvestigationDataSource(
        name="国家企业信用信息公示系统",
        source_type=DataSourceType.BUSINESS_REGISTRY,
        base_url="https://www.gsxt.gov.cn",
        api_key_env="",
        description="工商登记信息、经营异常、行政处罚等公示信息",
        rate_limit=0.5,
        requires_auth=False,
        is_free=True,
        endpoints={
            "search": "/corp-query-entprise-info-xxgg-100000.html",
        },
        supported_queries=["company_search"],
        notes="无API，需通过网页爬取。有较严格的反爬措施（验证码、IP限制）。"
              "建议作为辅助验证源，不作为主要数据来源。",
    ),

    InvestigationDataSource(
        name="中国执行信息公开网",
        source_type=DataSourceType.EXECUTION,
        base_url="http://zxgk.court.gov.cn",
        api_key_env="",
        description="法院执行案件信息查询，包括被执行人信息、执行标的等",
        rate_limit=0.3,
        requires_auth=False,
        is_free=True,
        endpoints={
            "search_person": "/zhixing/newChatDoor",
            "search_company": "/zhixing/newChatDoor",
        },
        supported_queries=["execution_search"],
        notes="无API，网页端有验证码。可通过姓名+身份证号或公司名查询。",
    ),

    InvestigationDataSource(
        name="全国法院失信被执行人名单",
        source_type=DataSourceType.DISHONEST,
        base_url="http://shixin.court.gov.cn",
        api_key_env="",
        description="失信被执行人（老赖）名单查询",
        rate_limit=0.3,
        requires_auth=False,
        is_free=True,
        endpoints={
            "search": "/",
        },
        supported_queries=["dishonest_search"],
        notes="可查询自然人和企业是否在失信名单中。有验证码。",
    ),

    InvestigationDataSource(
        name="信用中国",
        source_type=DataSourceType.CREDIT,
        base_url="https://www.creditchina.gov.cn",
        api_key_env="CREDIT_CHINA_API_KEY",
        description="国家信用信息共享平台，整合各部门信用数据",
        rate_limit=1.0,
        requires_auth=True,
        endpoints={
            "search": "/api/credit_search",
            "detail": "/api/credit_detail",
            "red_list": "/api/red_list",
            "black_list": "/api/black_list",
        },
        supported_queries=["credit_search", "red_list", "black_list"],
        notes="部分接口可能需要申请数据共享权限。"
              "提供行政许可、行政处罚、红名单、黑名单等信息。",
    ),

    InvestigationDataSource(
        name="中国裁判文书网",
        source_type=DataSourceType.JUDGMENT,
        base_url="https://wenshu.court.gov.cn",
        api_key_env="",
        description="全国法院裁判文书，含刑事、民事、行政等全部案件类型",
        rate_limit=0.1,
        requires_auth=True,
        is_free=True,
        endpoints={
            "search": "/website/parse/rest.q4w",
        },
        supported_queries=["judgment_search"],
        notes="反爬措施极其严格（滑块验证码、IP封禁、加密参数）。"
              "2018年后上线防爬系统，频繁访问IP会被封禁。"
              "不建议直接爬取，存在法律风险。"
              "建议使用天眼查/企查查的诉讼接口作为替代。",
    ),
]


# ==================== 查询接口 ====================


def get_available_sources(
    source_type: Optional[DataSourceType] = None,
    only_free: bool = False,
) -> List[InvestigationDataSource]:
    """获取可用的数据源列表"""
    sources = INVESTIGATION_DATA_SOURCES

    if source_type:
        sources = [s for s in sources if s.source_type == source_type]

    if only_free:
        sources = [s for s in sources if s.is_free]

    return sources


def get_source_by_name(name: str) -> Optional[InvestigationDataSource]:
    """按名称获取数据源"""
    for source in INVESTIGATION_DATA_SOURCES:
        if source.name == name:
            return source
    return None


def get_recommended_sources_for_investigation() -> Dict[str, List[str]]:
    """
    获取智能调查推荐的数据源组合。

    返回按调查维度分组的推荐数据源列表。
    调查编排器可以据此决定从哪些数据源获取数据。
    """
    return {
        "basic_info": [
            "天眼查",  # 首选：API最全面
            "企查查",  # 备选
            "国家企业信用信息公示系统",  # 官方验证
        ],
        "litigation": [
            "天眼查",  # 诉讼记录API
            "企查查",
            "中国裁判文书网",  # 受限，作为补充
        ],
        "credit": [
            "信用中国",  # 官方信用数据
            "天眼查",
        ],
        "execution": [
            "中国执行信息公开网",  # 执行案件
            "全国法院失信被执行人名单",  # 失信名单
            "天眼查",
        ],
        "penalty": [
            "天眼查",  # 行政处罚
            "信用中国",  # 黑名单
            "国家企业信用信息公示系统",  # 经营异常
        ],
        "ip": [
            "天眼查",  # 专利、商标
        ],
    }


def print_source_summary():
    """打印数据源摘要（用于开发调试）"""
    print("\n" + "=" * 80)
    print("企业调查数据源注册表")
    print("=" * 80)

    for source in INVESTIGATION_DATA_SOURCES:
        auth = "需要认证" if source.requires_auth else "公开访问"
        cost = "免费" if source.is_free else "付费"
        print(f"\n  [{source.name}] ({source.source_type.value})")
        print(f"    {source.description}")
        print(f"    URL: {source.base_url}")
        print(f"    认证: {auth} | 费用: {cost} | 限速: {source.rate_limit} req/s")
        if source.api_key_env:
            print(f"    API Key 环境变量: {source.api_key_env}")
        if source.notes:
            print(f"    注意: {source.notes}")
        print(f"    支持查询: {', '.join(source.supported_queries)}")

    print("\n" + "=" * 80)
    print("\n推荐数据源组合:")
    for dimension, sources in get_recommended_sources_for_investigation().items():
        print(f"  {dimension}: {' → '.join(sources)}")


if __name__ == "__main__":
    print_source_summary()
