#!/usr/bin/env python3
# 测试结果API服务器
# Test Results API Server

import os
import sys
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TestConfig
from utils.report_generator import ReportGenerator
from run_tests import AcceptanceTestRunner

app = Flask(__name__)
CORS(app)  # 启用跨域支持


class TestResultsAPI:
    """测试结果API服务"""

    def __init__(self):
        self.config = TestConfig()
        self.runner = AcceptanceTestRunner()
        self.report_generator = ReportGenerator()

    def get_latest_test_results(self) -> Optional[Dict[str, Any]]:
        """获取最新的测试结果"""
        try:
            # 查找最新的JSON报告文件
            json_files = glob.glob(
                os.path.join(self.config.REPORT_DIR, "acceptance_test_report_*.json")
            )
            if not json_files:
                return None

            # 按修改时间排序，获取最新的文件
            latest_file = max(json_files, key=os.path.getmtime)

            with open(latest_file, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            print(f"获取测试结果失败: {e}")
            return None

    def run_tests_and_get_results(self, suites: List[str] = None) -> Dict[str, Any]:
        """运行测试并返回结果"""
        try:
            # 运行测试
            test_data = self.runner.run_all_tests(suites)

            # 生成API响应格式
            api_response = self.runner.generate_api_response(test_data)

            return api_response

        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": {"message": str(e), "type": type(e).__name__},
            }


# 创建API实例
api = TestResultsAPI()


@app.route("/api/test-results", methods=["GET"])
def get_test_results():
    """获取测试结果API"""
    try:
        # 检查是否需要运行新测试
        run_new = request.args.get("run_new", "false").lower() == "true"
        suites = request.args.getlist("suites")

        if run_new:
            # 运行新测试
            result = api.run_tests_and_get_results(suites if suites else None)
        else:
            # 获取最新的测试结果
            result = api.get_latest_test_results()
            if result is None:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "timestamp": datetime.now().isoformat(),
                            "error": {
                                "message": "No test results found",
                                "type": "NotFound",
                            },
                        }
                    ),
                    404,
                )

        return jsonify(result)

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": {"message": str(e), "type": type(e).__name__},
                }
            ),
            500,
        )


@app.route("/api/test-results/summary", methods=["GET"])
def get_test_summary():
    """获取测试摘要API"""
    try:
        result = api.get_latest_test_results()
        if result is None:
            return jsonify({"status": "error", "message": "No test results found"}), 404

        # 只返回摘要信息
        summary_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": result.get("data", {}).get("summary", {}),
        }

        return jsonify(summary_data)

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": {"message": str(e), "type": type(e).__name__},
                }
            ),
            500,
        )


@app.route("/api/test-results/reports", methods=["GET"])
def get_available_reports():
    """获取可用报告列表API"""
    try:
        reports_dir = api.config.REPORT_DIR

        # 查找所有报告文件
        report_patterns = {
            "html": "acceptance_test_report_*.html",
            "json": "acceptance_test_report_*.json",
            "text": "acceptance_test_report_*.txt",
            "xml": "acceptance_test_report_*.xml",
            "csv": "acceptance_test_summary_*.csv",
        }

        available_reports = {}
        for format_type, pattern in report_patterns.items():
            files = glob.glob(os.path.join(reports_dir, pattern))
            if files:
                # 获取最新文件
                latest_file = max(files, key=os.path.getmtime)
                file_info = {
                    "file_path": latest_file,
                    "file_name": os.path.basename(latest_file),
                    "modified_time": datetime.fromtimestamp(
                        os.path.getmtime(latest_file)
                    ).isoformat(),
                    "size_bytes": os.path.getsize(latest_file),
                }
                available_reports[format_type] = file_info

        return jsonify(
            {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "reports": available_reports,
                    "total_formats": len(available_reports),
                },
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": {"message": str(e), "type": type(e).__name__},
                }
            ),
            500,
        )


@app.route("/api/test-results/download/<format_type>", methods=["GET"])
def download_report(format_type):
    """下载指定格式的报告文件"""
    try:
        reports_dir = api.config.REPORT_DIR

        # 定义文件模式
        patterns = {
            "html": "acceptance_test_report_*.html",
            "json": "acceptance_test_report_*.json",
            "text": "acceptance_test_report_*.txt",
            "xml": "acceptance_test_report_*.xml",
            "csv": "acceptance_test_summary_*.csv",
        }

        if format_type not in patterns:
            return (
                jsonify(
                    {"status": "error", "message": f"Unsupported format: {format_type}"}
                ),
                400,
            )

        # 查找文件
        files = glob.glob(os.path.join(reports_dir, patterns[format_type]))
        if not files:
            return (
                jsonify(
                    {"status": "error", "message": f"No {format_type} reports found"}
                ),
                404,
            )

        # 获取最新文件
        latest_file = max(files, key=os.path.getmtime)

        return send_file(
            latest_file, as_attachment=True, download_name=os.path.basename(latest_file)
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": {"message": str(e), "type": type(e).__name__},
                }
            ),
            500,
        )


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查API"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "TACoreService Test Results API",
            "version": "1.0.0",
        }
    )


@app.route("/api/docs", methods=["GET"])
def api_documentation():
    """API文档"""
    docs = {
        "title": "TACoreService Test Results API",
        "version": "1.0.0",
        "description": "提供TACoreService验收测试结果的API接口",
        "endpoints": {
            "GET /api/test-results": {
                "description": "获取测试结果",
                "parameters": {
                    "run_new": "是否运行新测试 (true/false)",
                    "suites": "指定测试套件 (可多个)",
                },
            },
            "GET /api/test-results/summary": {"description": "获取测试摘要"},
            "GET /api/test-results/reports": {"description": "获取可用报告列表"},
            "GET /api/test-results/download/<format>": {
                "description": "下载指定格式的报告",
                "formats": ["html", "json", "text", "xml", "csv"],
            },
            "GET /api/health": {"description": "健康检查"},
        },
    }

    return jsonify(docs)


if __name__ == "__main__":
    print("启动TACoreService测试结果API服务器...")
    print("API文档: http://localhost:5000/api/docs")
    print("健康检查: http://localhost:5000/api/health")
    print("测试结果: http://localhost:5000/api/test-results")

    app.run(host="0.0.0.0", port=5000, debug=True)
