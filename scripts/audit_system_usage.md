# NeuroTrade Nexus (NTN) - 系统审计脚本使用说明

## 概述

`audit_system.ps1` 脚本已经更新，支持更灵活的参数配置和自动跳过功能，避免在未提供必要参数时出现错误。

## 参数说明

### 基本参数
- `-LogLevel <string>`: 日志级别，默认为 "INFO"
- `-SkipIntegrationTest`: 跳过集成测试的开关参数

### 虚拟机连接参数
- `-VmHost <string>`: 虚拟机IP地址（必需，用于集成测试）
- `-VmUser <string>`: 虚拟机用户名（必需，用于集成测试）
- `-VmProjectPath <string>`: 虚拟机项目路径，默认为 "~/projects"

## 使用示例

### 1. 基本使用（跳过集成测试）
```powershell
.\audit_system.ps1
```
当未提供虚拟机参数时，脚本会自动跳过集成测试部分，避免连接错误。

### 2. 显式跳过集成测试
```powershell
.\audit_system.ps1 -SkipIntegrationTest
```

### 3. 完整集成测试
```powershell
.\audit_system.ps1 -VmHost "192.168.1.7" -VmUser "tjsga"
```

### 4. 自定义虚拟机项目路径
```powershell
.\audit_system.ps1 -VmHost "192.168.1.7" -VmUser "tjsga" -VmProjectPath "/home/user/ntn"
```

### 5. 调试模式
```powershell
.\audit_system.ps1 -LogLevel "DEBUG" -VmHost "192.168.1.7" -VmUser "tjsga"
```

## 错误处理改进

### 1. 自动参数检查
- 脚本会自动检查虚拟机连接参数是否提供
- 如果未提供必要参数，会显示友好提示并跳过相关测试

### 2. 网络连接预检查
- 在执行 `Invoke-WebRequest` 之前，先进行TCP连接测试
- 避免长时间等待和不必要的错误

### 3. 详细错误信息
- 提供更详细的错误描述，便于问题诊断
- 区分连接超时和其他类型的错误

## 常见问题解决

### Q: 出现 "Invoke-WebRequest URI参数错误"
A: 这通常是因为未提供虚拟机参数。使用以下方法之一：
1. 添加 `-VmHost` 和 `-VmUser` 参数
2. 使用 `-SkipIntegrationTest` 跳过集成测试
3. 直接运行脚本（会自动跳过）

### Q: 虚拟机连接失败
A: 检查以下项目：
1. 虚拟机IP地址是否正确
2. SSH连接是否正常
3. 用户名和权限是否正确
4. 网络连接是否稳定

### Q: 端点测试失败
A: 脚本现在会：
1. 先进行TCP连接测试
2. 提供详细的错误信息
3. 继续测试其他端点
4. 计算整体连通率

## 最佳实践

1. **开发环境**: 使用 `-SkipIntegrationTest` 进行快速本地测试
2. **测试环境**: 提供完整的虚拟机参数进行全面测试
3. **生产环境**: 确保所有参数正确配置，启用完整审计
4. **调试**: 使用 `-LogLevel "DEBUG"` 获取详细日志

## 输出说明

脚本会生成带时间戳的审计日志文件：`audit_yyyyMMdd_HHmmss.log`

日志包含：
- PASS: 测试通过
- FAIL: 测试失败
- WARN: 警告信息
- INFO: 一般信息

最终会显示测试统计和总体结果。