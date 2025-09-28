# 🐳 Docker Hub 密钥配置指南 (S.O.P.)

## 📋 问题描述

您的 CI/CD 流水线在 `docker-build` 阶段失败，原因是缺少有效的 Docker Hub 认证凭据。当前的 `ci.yml` 配置尝试推送 Docker 镜像，但没有正确配置 Docker Hub 的登录凭据。

## 🎯 所需密钥

为了成功完成 Docker 镜像构建和推送，您需要在 GitHub 仓库中创建以下两个 Repository Secrets：

- **`DOCKERHUB_USERNAME`** - 您的 Docker Hub 用户名
- **`DOCKERHUB_TOKEN`** - Docker Hub 个人访问令牌 (PAT)

---

## 🛠️ 配置步骤

### 步骤 1: 导航到 GitHub 密钥设置

1. 打开您的 GitHub 仓库页面
2. 点击仓库顶部的 **"Settings"** 标签页
3. 在左侧边栏中，找到 **"Security"** 部分
4. 点击 **"Secrets and variables"** 
5. 选择 **"Actions"** 子菜单

### 步骤 2: 配置 DOCKERHUB_USERNAME

1. 在 "Repository secrets" 部分，点击 **"New repository secret"** 按钮
2. 在 "Name" 字段中输入：`DOCKERHUB_USERNAME`
3. 在 "Secret" 字段中输入：您的 Docker Hub 用户名（例如：`yourname`）
4. 点击 **"Add secret"** 保存

### 步骤 3: 配置 DOCKERHUB_TOKEN

> ⚠️ **安全警告**: 绝不能使用您的 Docker Hub 登录密码作为令牌！

#### 3.1 生成 Docker Hub 个人访问令牌

1. 登录 [Docker Hub](https://hub.docker.com/)
2. 点击右上角您的头像，选择 **"Account Settings"**
3. 在左侧菜单中点击 **"Security"**
4. 找到 "Access Tokens" 部分，点击 **"New Access Token"**
5. 输入令牌描述（例如：`GitHub-CI-CD`）
6. 选择权限：
   - **Read, Write, Delete** （用于推送镜像）
   - 或者 **Read, Write** （如果不需要删除权限）
7. 点击 **"Generate"**
8. **立即复制生成的令牌**（只会显示一次！）

#### 3.2 在 GitHub 中添加 DOCKERHUB_TOKEN

1. 返回 GitHub 仓库的密钥设置页面
2. 点击 **"New repository secret"**
3. 在 "Name" 字段中输入：`DOCKERHUB_TOKEN`
4. 在 "Secret" 字段中粘贴刚才复制的 Docker Hub PAT
5. 点击 **"Add secret"** 保存

---

## 🔧 更新 CI/CD 配置

您还需要更新 `ci.yml` 文件中的 Docker 登录配置。将第 60-67 行的内容修改为：

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}
```

并添加环境变量定义（在文件顶部 `on:` 部分之前添加）：

```yaml
env:
  REGISTRY: docker.io
  IMAGE_NAME: your-dockerhub-username/ntn-clean
```

---

## ✅ 验证配置

### 方法 1: 重新运行失败的作业

1. 转到您仓库的 **"Actions"** 标签页
2. 找到失败的工作流运行
3. 点击失败的运行记录
4. 在页面右上角点击 **"Re-run failed jobs"** 按钮

### 方法 2: 触发新的构建

1. 向 `main` 或 `develop` 分支推送一个小的提交
2. 观察 Actions 标签页中的新工作流运行

---

## 🚨 故障排除

### 常见问题 1: 令牌权限不足
**症状**: 登录成功但推送失败  
**解决方案**: 确保 Docker Hub 令牌具有 "Write" 权限

### 常见问题 2: 用户名错误
**症状**: 认证失败  
**解决方案**: 检查 `DOCKERHUB_USERNAME` 是否与您的 Docker Hub 用户名完全一致

### 常见问题 3: 令牌过期
**症状**: 之前工作正常，突然开始失败  
**解决方案**: 在 Docker Hub 中重新生成令牌并更新 GitHub Secret

### 常见问题 4: 环境变量缺失
**症状**: 无法解析 registry 或 image name  
**解决方案**: 确保在 `ci.yml` 中正确定义了 `REGISTRY` 和 `IMAGE_NAME` 环境变量

---

## 🔒 安全最佳实践

1. **定期轮换令牌**: 建议每 6-12 个月更新一次 Docker Hub PAT
2. **最小权限原则**: 只授予 CI/CD 所需的最小权限
3. **监控使用情况**: 定期检查 Docker Hub 中的令牌使用日志
4. **及时清理**: 删除不再使用的令牌

---

## 📞 获得帮助

如果按照以上步骤操作后仍然遇到问题，请检查：

1. GitHub Actions 日志中的具体错误信息
2. Docker Hub 账户是否处于活跃状态
3. 仓库是否有正确的 Dockerfile 配置

---

*最后更新: 2025-09-27*  
*版本: 1.0*