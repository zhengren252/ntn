#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - 三页式报告生成器单元测试（TDD优先）

测试目标：
- UNIT-RG-REPORT-01: 生成基础的三页式报告结构
- UNIT-RG-REPORT-02: 生成可阅读的HTML报告片段（包含核心章节标题）
- UNIT-RG-REPORT-03: 缺失必填字段应抛出异常
"""

import pytest
import sys
import os
import importlib.util

# 以动态加载方式导入 report_generator.py，避免 services/__init__.py 的副作用依赖
CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(CURRENT_DIR, '..', 'src')
MODULE_PATH = os.path.join(SRC_DIR, 'services', 'report_generator.py')

spec = importlib.util.spec_from_file_location("report_generator", MODULE_PATH)
report_module = importlib.util.module_from_spec(spec)  # type: ignore
assert spec and spec.loader
spec.loader.exec_module(report_module)  # type: ignore
ReportGenerator = report_module.ReportGenerator  # type: ignore


@pytest.fixture
def sample_strategy_input():
    """提供一个完整且具代表性的策略输入，用于报告生成。
    该输入覆盖概览、风险与历史绩效三个维度。
    """
    return {
        'strategy_id': 'strat_001',
        'strategy_name': 'Alpha Momentum',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback': 14,
            'threshold': 1.5
        },
        'expected_return': 0.12,
        'risk_assessment': {
            'risk_level': 'low',
            'max_drawdown': 0.08,
            'var_95': 0.05,
            'sharpe_ratio': 1.8
        },
        'performance': {
            'total_return': 0.25,
            'win_rate': 0.62,
            'profit_factor': 1.7,
            'equity_curve': [100, 102, 101, 104, 107]
        }
    }


class TestThreePageReportGenerator:
    """三页式报告生成器测试类"""

    def test_unit_rg_report_01_generate_structure(self, sample_strategy_input):
        """UNIT-RG-REPORT-01: 生成基础的三页式报告结构"""
        gen = ReportGenerator()
        report = gen.generate(sample_strategy_input)

        # 元信息
        assert 'meta' in report
        assert report['meta']['strategy_id'] == sample_strategy_input['strategy_id']
        assert isinstance(report['meta'].get('generated_at'), str)

        # 三页结构
        assert 'pages' in report and isinstance(report['pages'], list) and len(report['pages']) == 3
        ids = [p.get('id') for p in report['pages']]
        assert ids == ['overview', 'risk', 'performance']

        # 概览页应包含核心字段
        overview = report['pages'][0]
        assert overview['content']['strategy_name'] == sample_strategy_input['strategy_name']
        assert overview['content']['strategy_type'] == sample_strategy_input['strategy_type']
        assert isinstance(overview['content']['parameters_summary'], str)
        assert overview['content']['expected_return'] == sample_strategy_input['expected_return']

        # 风险页应包含关键风险指标
        risk = report['pages'][1]
        assert risk['content']['risk_level'] == sample_strategy_input['risk_assessment']['risk_level']
        assert risk['content']['max_drawdown'] == sample_strategy_input['risk_assessment']['max_drawdown']
        assert risk['content']['var_95'] == sample_strategy_input['risk_assessment']['var_95']
        assert risk['content']['sharpe_ratio'] == sample_strategy_input['risk_assessment']['sharpe_ratio']

        # 绩效页应包含关键绩效指标
        perf = report['pages'][2]
        assert perf['content']['total_return'] == sample_strategy_input['performance']['total_return']
        assert perf['content']['win_rate'] == sample_strategy_input['performance']['win_rate']
        assert perf['content']['profit_factor'] == sample_strategy_input['performance']['profit_factor']
        # equity_curve_summary 为派生字段，至少应包含长度与首尾值
        ecs = perf['content']['equity_curve_summary']
        assert ecs['length'] == len(sample_strategy_input['performance']['equity_curve'])
        assert ecs['start'] == sample_strategy_input['performance']['equity_curve'][0]
        assert ecs['end'] == sample_strategy_input['performance']['equity_curve'][-1]

    def test_unit_rg_report_02_generate_html_contains_sections(self, sample_strategy_input):
        """UNIT-RG-REPORT-02: 生成可阅读的HTML报告片段（包含核心章节标题）"""
        gen = ReportGenerator()
        report = gen.generate(sample_strategy_input)
        html = gen.generate_html(report)

        assert '<h2>概览</h2>' in html
        assert '<h2>风险分析</h2>' in html
        assert '<h2>历史绩效</h2>' in html
        assert sample_strategy_input['strategy_name'] in html

    def test_unit_rg_report_03_missing_required_fields(self):
        """UNIT-RG-REPORT-03: 缺失必填字段应抛出异常"""
        gen = ReportGenerator()
        with pytest.raises(ValueError):
            gen.generate({'strategy_name': 'S'})  # 缺少 strategy_id
        with pytest.raises(ValueError):
            gen.generate({'strategy_id': 'X'})  # 缺少 strategy_name