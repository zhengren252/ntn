#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - 三页式报告生成器

本模块提供结构化三页式报告的生成，并提供简单的HTML渲染能力。
"""
from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime
import json


class ReportGenerator:
    """三页式报告生成器
    
    生成包含三页内容的结构化报告：
    1) 概览（overview）
    2) 风险分析（risk）
    3) 历史绩效（performance）
    """

    def _validate_input(self, data: Dict[str, Any]) -> None:
        """校验输入数据的必要字段。
        :raises ValueError: 当缺少必填字段时。
        """
        required = ['strategy_id', 'strategy_name']
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required field: {key}")

    def generate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成结构化三页式报告。
        :param data: 策略输入数据，包含基本信息、风险与绩效。
        :return: 结构化报告字典。
        """
        self._validate_input(data)

        parameters = data.get('parameters', {})
        params_summary = ", ".join(f"{k}={v}" for k, v in parameters.items()) if parameters else "无"

        # 概览页
        overview = {
            'id': 'overview',
            'title': '概览',
            'content': {
                'strategy_name': data['strategy_name'],
                'strategy_type': data.get('strategy_type', 'unknown'),
                'parameters_summary': params_summary,
                'expected_return': data.get('expected_return'),
            }
        }

        # 风险页
        ra = data.get('risk_assessment', {})
        risk = {
            'id': 'risk',
            'title': '风险分析',
            'content': {
                'risk_level': ra.get('risk_level'),
                'max_drawdown': ra.get('max_drawdown'),
                'var_95': ra.get('var_95'),
                'sharpe_ratio': ra.get('sharpe_ratio'),
            }
        }

        # 绩效页
        perf = data.get('performance', {})
        equity = perf.get('equity_curve') or []
        equity_summary = {
            'length': len(equity),
            'start': equity[0] if equity else None,
            'end': equity[-1] if equity else None,
        }
        performance = {
            'id': 'performance',
            'title': '历史绩效',
            'content': {
                'total_return': perf.get('total_return'),
                'win_rate': perf.get('win_rate'),
                'profit_factor': perf.get('profit_factor'),
                'equity_curve_summary': equity_summary,
            }
        }

        report = {
            'meta': {
                'strategy_id': data['strategy_id'],
                'generated_at': datetime.utcnow().isoformat(),
                'source': 'ReviewGuard',
            },
            'pages': [overview, risk, performance]
        }
        return report

    def generate_html(self, report: Dict[str, Any]) -> str:
        """将结构化报告渲染为简单HTML片段。
        :param report: 结构化报告
        :return: HTML字符串
        """
        pages: List[Dict[str, Any]] = report.get('pages', [])
        blocks = [
            '<div class="report">',
            f"<h1>策略报告 - {report.get('meta', {}).get('strategy_id','')}</h1>"
        ]
        for page in pages:
            title = page.get('title', '')
            content = page.get('content', {})
            blocks.append(f"<section><h2>{title}</h2><pre>{json.dumps(content, ensure_ascii=False)}</pre></section>")
        blocks.append('</div>')
        return "\n".join(blocks)