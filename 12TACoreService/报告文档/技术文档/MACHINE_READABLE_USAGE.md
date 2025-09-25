# TACoreService 验收测试机器可读格式使用指南

## 概述

TACoreService验收测试套件现在支持多种机器可读的测试报告格式，便于与CI/CD系统、自动化工具和其他系统集成。

## 支持的输出格式

### 1. JSON格式
- **用途**: API集成、数据分析、自动化处理
- **特点**: 结构化数据，包含完整的测试信息
- **文件名**: `acceptance_test_report_YYYYMMDD_HHMMSS.json`

### 2. JUnit XML格式
- **用途**: CI/CD系统集成（Jenkins、GitLab CI、GitHub Actions等）
- **特点**: 标准JUnit格式，兼容大多数CI/CD工具
- **文件名**: `acceptance_test_report_YYYYMMDD_HHMMSS.xml`

### 3. CSV格式
- **用途**: 数据分析、报表生成、Excel导入
- **特点**: 表格格式，便于统计分析
- **文件名**: `acceptance_test_summary_YYYYMMDD_HHMMSS.csv`

### 4. HTML格式
- **用途**: 人工查看、报告展示
- **特点**: 可视化界面，包含图表和样式
- **文件名**: `acceptance_test_report_YYYYMMDD_HHMMSS.html`

### 5. 文本格式
- **用途**: 日志记录、简单查看
- **特点**: 纯文本，便于脚本处理
- **文件名**: `acceptance_test_report_YYYYMMDD_HHMMSS.txt`

## 命令行使用方法

### 基本用法

```bash
# 运行所有测试并生成所有格式的报告
python run_tests.py

# 运行指定测试套件
python run_tests.py --suites ZMQ_BUSINESS_API HTTP_MONITORING_API

# 生成指定格式的报告
python run_tests.py --formats json junit_xml csv

# 只生成JUnit XML格式（用于CI/CD）
python run_tests.py --formats junit_xml

# 不生成任何报告文件
python run_tests.py --no-reports
```

### API输出格式

```bash
# 在控制台输出API响应格式的结果
python run_tests.py --api-output

# 将API响应格式保存到文件
python run_tests.py --output-file test_results.json

# 同时输出到控制台和文件
python run_tests.py --api-output --output-file test_results.json
```

### 组合使用

```bash
# 运行特定测试套件，生成JSON和XML格式，并输出API格式
python run_tests.py --suites ZMQ_BUSINESS_API --formats json junit_xml --api-output
```

## API服务器使用

### 启动API服务器

```bash
python api_server.py
```

服务器将在 `http://localhost:5000` 启动。

### API端点

#### 1. 获取测试结果
```bash
# 获取最新的测试结果
curl http://localhost:5000/api/test-results

# 运行新测试并获取结果
curl "http://localhost:5000/api/test-results?run_new=true"

# 运行指定测试套件
curl "http://localhost:5000/api/test-results?run_new=true&suites=ZMQ_BUSINESS_API&suites=HTTP_MONITORING_API"
```

#### 2. 获取测试摘要
```bash
curl http://localhost:5000/api/test-results/summary
```

#### 3. 获取可用报告列表
```bash
curl http://localhost:5000/api/test-results/reports
```

#### 4. 下载报告文件
```bash
# 下载JSON格式报告
curl -O http://localhost:5000/api/test-results/download/json

# 下载JUnit XML格式报告
curl -O http://localhost:5000/api/test-results/download/xml

# 下载CSV格式报告
curl -O http://localhost:5000/api/test-results/download/csv
```

#### 5. 健康检查
```bash
curl http://localhost:5000/api/health
```

#### 6. API文档
```bash
curl http://localhost:5000/api/docs
```

## CI/CD集成示例

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Run Acceptance Tests') {
            steps {
                script {
                    // 运行测试并生成JUnit XML报告
                    sh 'python acceptance_tests/run_tests.py --formats junit_xml'
                    
                    // 发布测试结果
                    publishTestResults(
                        testResultsPattern: 'acceptance_tests/reports/*.xml'
                    )
                }
            }
        }
    }
}
```

### GitHub Actions

```yaml
name: Acceptance Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r acceptance_tests/requirements.txt
    
    - name: Run acceptance tests
      run: |
        python acceptance_tests/run_tests.py --formats junit_xml json
    
    - name: Publish test results
      uses: dorny/test-reporter@v1
      if: always()
      with:
        name: Acceptance Test Results
        path: 'acceptance_tests/reports/*.xml'
        reporter: java-junit
    
    - name: Upload test reports
      uses: actions/upload-artifact@v2
      if: always()
      with:
        name: test-reports
        path: acceptance_tests/reports/
```

### GitLab CI

```yaml
stages:
  - test

acceptance_tests:
  stage: test
  script:
    - pip install -r acceptance_tests/requirements.txt
    - python acceptance_tests/run_tests.py --formats junit_xml json
  artifacts:
    when: always
    reports:
      junit: acceptance_tests/reports/*.xml
    paths:
      - acceptance_tests/reports/
    expire_in: 1 week
```

## 数据格式说明

### JSON格式结构

```json
{
  "status": "success",
  "timestamp": "2024-01-15T10:30:00",
  "data": {
    "summary": {
      "total_tests": 25,
      "passed_tests": 23,
      "failed_tests": 2,
      "success_rate": 92.0,
      "total_duration": 45.67
    },
    "test_results": [
      {
        "case_id": "ZMQ-001",
        "title": "ZeroMQ连接测试",
        "suite_id": "ZMQ_BUSINESS_API",
        "suite_name": "ZeroMQ业务API测试",
        "status": "PASS",
        "duration": 1.234,
        "verification_results": [
          {
            "description": "连接建立成功",
            "passed": true,
            "details": "连接时间: 0.123s"
          }
        ]
      }
    ]
  }
}
```

### CSV格式字段

| 字段名 | 描述 |
|--------|------|
| Test_ID | 测试用例ID |
| Test_Title | 测试用例标题 |
| Suite_ID | 测试套件ID |
| Suite_Name | 测试套件名称 |
| Status | 测试状态 (PASS/FAIL) |
| Duration_Seconds | 执行时间（秒） |
| Start_Time | 开始时间 |
| End_Time | 结束时间 |
| Error_Message | 错误信息 |
| Verification_Points_Total | 验证点总数 |
| Verification_Points_Passed | 通过的验证点数 |
| Success_Rate | 验证点成功率 |

## 自动化脚本示例

### Python脚本获取测试结果

```python
import requests
import json

# 获取测试结果
response = requests.get('http://localhost:5000/api/test-results')
if response.status_code == 200:
    data = response.json()
    summary = data['data']['summary']
    
    print(f"测试总数: {summary['total_tests']}")
    print(f"通过率: {summary['success_rate']:.1f}%")
    
    # 检查是否有失败的测试
    if summary['failed_tests'] > 0:
        print(f"警告: {summary['failed_tests']} 个测试失败")
        exit(1)
else:
    print(f"获取测试结果失败: {response.status_code}")
    exit(1)
```

### Bash脚本监控测试状态

```bash
#!/bin/bash

# 运行测试并检查结果
python acceptance_tests/run_tests.py --formats json --output-file latest_results.json

# 解析结果
SUCCESS_RATE=$(cat latest_results.json | jq -r '.data.summary.success_rate')
FAILED_TESTS=$(cat latest_results.json | jq -r '.data.summary.failed_tests')

echo "测试成功率: ${SUCCESS_RATE}%"

if [ "$FAILED_TESTS" -gt 0 ]; then
    echo "警告: $FAILED_TESTS 个测试失败"
    exit 1
else
    echo "所有测试通过"
    exit 0
fi
```

## 最佳实践

1. **CI/CD集成**: 使用JUnit XML格式与CI/CD系统集成
2. **数据分析**: 使用JSON或CSV格式进行自动化分析
3. **报告存档**: 定期备份测试报告文件
4. **API监控**: 使用API接口实现实时测试状态监控
5. **格式选择**: 根据具体需求选择合适的输出格式

## 故障排除

### 常见问题

1. **报告文件未生成**
   - 检查报告目录权限
   - 确认测试正常执行完成

2. **API服务器无法启动**
   - 检查端口5000是否被占用
   - 确认Flask依赖已安装

3. **JUnit XML格式不兼容**
   - 确认CI/CD工具支持的XML格式版本
   - 检查XML文件结构是否正确

### 调试命令

```bash
# 检查报告目录
ls -la acceptance_tests/reports/

# 验证JSON格式
python -m json.tool acceptance_tests/reports/latest_report.json

# 检查XML格式
xmllint --format acceptance_tests/reports/latest_report.xml
```

## 更新日志

- **v1.0.0**: 初始版本，支持JSON、JUnit XML、CSV、HTML、文本格式
- 添加API服务器支持
- 添加命令行参数支持
- 添加CI