#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker化部署测试脚本
用于执行完整的Docker化部署测试流程，包括单元/集成测试和端到端功能模拟测试
"""

import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('docker_deployment_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DockerDeploymentTester:
    """Docker化部署测试器"""
    
    def __init__(self):
        self.test_results = {
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'overall_status': 'PENDING',
            'pass_rate': 0.0,
            'issues_found': 0
        }
        self.compose_file = 'docker-compose.integration.yml'
        
    def run_command(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """执行命令并返回结果"""
        try:
            logger.info(f"执行命令: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or os.getcwd(),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {command}")
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timeout'
            }
        except Exception as e:
            logger.error(f"命令执行失败: {command}, 错误: {str(e)}")
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def cleanup_environment(self):
        """清理测试环境"""
        logger.info("清理测试环境...")
        
        # 停止并删除容器
        cleanup_commands = [
            f"docker-compose -f {self.compose_file} down --volumes --remove-orphans",
            "docker system prune -f"
        ]
        
        for cmd in cleanup_commands:
            result = self.run_command(cmd)
            if not result['success']:
                logger.warning(f"清理命令失败: {cmd}")
    
    def setup_test_environment(self):
        """设置测试环境"""
        logger.info("设置测试环境...")
        
        # 检查docker-compose文件是否存在
        if not os.path.exists(self.compose_file):
            logger.error(f"Docker Compose文件不存在: {self.compose_file}")
            return False
        
        # 构建镜像
        build_result = self.run_command(f"docker-compose -f {self.compose_file} build")
        if not build_result['success']:
            logger.error("Docker镜像构建失败")
            logger.error(f"构建错误: {build_result['stderr']}")
            return False
        
        return True
    
    def run_unit_integration_tests(self) -> Dict[str, Any]:
        """运行单元/集成测试"""
        logger.info("开始单元/集成测试...")
        
        test_result = {
            'name': 'Unit/Integration Tests',
            'status': 'PENDING',
            'start_time': datetime.now().isoformat(),
            'details': [],
            'issues': []
        }
        
        try:
            # 启动测试服务
            logger.info("启动测试环境...")
            up_result = self.run_command(
                f"docker-compose -f {self.compose_file} up -d redis tacore_service tradeguard"
            )
            
            if not up_result['success']:
                test_result['status'] = 'FAILED'
                test_result['issues'].append({
                    'severity': 'HIGH',
                    'description': '测试环境启动失败',
                    'details': up_result['stderr']
                })
                return test_result
            
            # 等待服务启动
            logger.info("等待服务启动...")
            time.sleep(30)
            
            # 运行集成测试
            logger.info("执行集成测试...")
            test_cmd_result = self.run_command(
                f"docker-compose -f {self.compose_file} run --rm tradeguard npm run test:integration"
            )
            
            if test_cmd_result['success']:
                test_result['status'] = 'PASSED'
                test_result['details'].append('集成测试通过')
            else:
                test_result['status'] = 'FAILED'
                test_result['issues'].append({
                    'severity': 'HIGH',
                    'description': '集成测试失败',
                    'details': test_cmd_result['stderr']
                })
            
        except Exception as e:
            test_result['status'] = 'FAILED'
            test_result['issues'].append({
                'severity': 'HIGH',
                'description': f'测试执行异常: {str(e)}',
                'details': ''
            })
        
        finally:
            # 清理测试环境
            self.cleanup_environment()
        
        test_result['end_time'] = datetime.now().isoformat()
        return test_result
    
    def run_e2e_functional_tests(self) -> Dict[str, Any]:
        """运行端到端功能模拟测试"""
        logger.info("开始端到端功能模拟测试...")
        
        test_result = {
            'name': 'End-to-End Functional Simulation',
            'status': 'PENDING',
            'start_time': datetime.now().isoformat(),
            'details': [],
            'issues': []
        }
        
        try:
            # 启动完整系统
            logger.info("启动完整系统...")
            up_result = self.run_command(
                f"docker-compose -f {self.compose_file} up -d redis tacore_service tradeguard"
            )
            
            if not up_result['success']:
                test_result['status'] = 'FAILED'
                test_result['issues'].append({
                    'severity': 'HIGH',
                    'description': '系统启动失败',
                    'details': up_result['stderr']
                })
                return test_result
            
            # 等待服务完全启动
            logger.info("等待服务完全启动...")
            time.sleep(45)
            
            # 执行功能测试命令
            logger.info("注入测试命令...")
            
            # 模拟发布消息到Redis
            redis_test_result = self.run_command(
                f"docker-compose -f {self.compose_file} exec -T redis redis-cli PUBLISH review.pool.approved '{{\"strategy_id\": \"test_001\", \"action\": \"BUY\", \"symbol\": \"AAPL\", \"quantity\": 100}}'"
            )
            
            if redis_test_result['success']:
                test_result['details'].append('Redis消息发布成功')
            else:
                test_result['issues'].append({
                    'severity': 'MEDIUM',
                    'description': 'Redis消息发布失败',
                    'details': redis_test_result['stderr']
                })
            
            # 检查服务日志
            logger.info("检查服务日志...")
            
            # 获取tradeguard日志
            logs_result = self.run_command(
                f"docker-compose -f {self.compose_file} logs tradeguard"
            )
            
            if logs_result['success']:
                test_result['details'].append('服务日志获取成功')
                # 简单检查日志中是否有错误
                if 'ERROR' in logs_result['stdout'] or 'FATAL' in logs_result['stdout']:
                    test_result['issues'].append({
                        'severity': 'MEDIUM',
                        'description': '服务日志中发现错误',
                        'details': '日志包含ERROR或FATAL级别消息'
                    })
            else:
                test_result['issues'].append({
                    'severity': 'LOW',
                    'description': '无法获取服务日志',
                    'details': logs_result['stderr']
                })
            
            # 判断测试结果
            if len([issue for issue in test_result['issues'] if issue['severity'] in ['HIGH', 'CRITICAL']]) == 0:
                test_result['status'] = 'PASSED'
            else:
                test_result['status'] = 'FAILED'
            
        except Exception as e:
            test_result['status'] = 'FAILED'
            test_result['issues'].append({
                'severity': 'HIGH',
                'description': f'端到端测试执行异常: {str(e)}',
                'details': ''
            })
        
        finally:
            # 清理环境
            self.cleanup_environment()
        
        test_result['end_time'] = datetime.now().isoformat()
        return test_result
    
    def calculate_pass_rate(self) -> float:
        """计算测试通过率"""
        if not self.test_results['tests']:
            return 0.0
        
        passed_tests = len([test for test in self.test_results['tests'] if test['status'] == 'PASSED'])
        total_tests = len(self.test_results['tests'])
        
        return (passed_tests / total_tests) * 100.0
    
    def count_issues(self) -> int:
        """统计问题数量"""
        total_issues = 0
        for test in self.test_results['tests']:
            total_issues += len(test.get('issues', []))
        return total_issues
    
    def generate_report(self):
        """生成测试报告"""
        self.test_results['end_time'] = datetime.now().isoformat()
        self.test_results['pass_rate'] = self.calculate_pass_rate()
        self.test_results['issues_found'] = self.count_issues()
        
        # 确定整体状态
        if self.test_results['pass_rate'] >= 95.0:
            self.test_results['overall_status'] = 'PASSED'
        else:
            self.test_results['overall_status'] = 'FAILED'
        
        # 保存报告
        report_file = f"docker_deployment_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"测试报告已生成: {report_file}")
            
            # 打印摘要
            print("\n" + "="*60)
            print("Docker化部署测试报告摘要")
            print("="*60)
            print(f"整体状态: {self.test_results['overall_status']}")
            print(f"测试通过率: {self.test_results['pass_rate']:.1f}%")
            print(f"发现问题数: {self.test_results['issues_found']}")
            print(f"测试开始时间: {self.test_results['start_time']}")
            print(f"测试结束时间: {self.test_results['end_time']}")
            print(f"详细报告: {report_file}")
            print("="*60)
            
            return report_file
            
        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始Docker化部署测试流程...")
        
        try:
            # 设置测试环境
            if not self.setup_test_environment():
                logger.error("测试环境设置失败，终止测试")
                return False
            
            # 运行单元/集成测试
            unit_test_result = self.run_unit_integration_tests()
            self.test_results['tests'].append(unit_test_result)
            
            # 运行端到端功能测试
            e2e_test_result = self.run_e2e_functional_tests()
            self.test_results['tests'].append(e2e_test_result)
            
            # 生成报告
            report_file = self.generate_report()
            
            # 检查是否达到要求的通过率
            if self.test_results['pass_rate'] >= 95.0:
                logger.info("测试通过率达到要求 (≥95%)")
                return True
            else:
                logger.warning(f"测试通过率未达到要求: {self.test_results['pass_rate']:.1f}% < 95%")
                return False
                
        except Exception as e:
            logger.error(f"测试流程执行失败: {str(e)}")
            return False
        
        finally:
            # 确保环境清理
            self.cleanup_environment()

def main():
    """主函数"""
    tester = DockerDeploymentTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        tester.cleanup_environment()
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试执行异常: {str(e)}")
        tester.cleanup_environment()
        sys.exit(1)

if __name__ == "__main__":
    main()