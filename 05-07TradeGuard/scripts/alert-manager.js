#!/usr/bin/env node

/**
 * 交易执行铁三角项目 - 告警管理器
 * 负责监控指标收集、告警规则评估和通知发送
 */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const EventEmitter = require('events');
const nodemailer = require('nodemailer');
const axios = require('axios');
const sqlite3 = require('sqlite3').verbose();
const redis = require('redis');

class AlertManager extends EventEmitter {
    constructor(configPath) {
        super();
        this.configPath = configPath;
        this.config = null;
        this.metrics = new Map();
        this.alerts = new Map();
        this.silences = new Map();
        this.notificationChannels = new Map();
        this.db = null;
        this.redis = null;
        this.isRunning = false;
        
        // 绑定方法
        this.loadConfig = this.loadConfig.bind(this);
        this.initializeDatabase = this.initializeDatabase.bind(this);
        this.initializeRedis = this.initializeRedis.bind(this);
        this.collectMetrics = this.collectMetrics.bind(this);
        this.evaluateAlerts = this.evaluateAlerts.bind(this);
        this.sendNotification = this.sendNotification.bind(this);
    }

    /**
     * 加载监控配置
     */
    async loadConfig() {
        try {
            const configContent = fs.readFileSync(this.configPath, 'utf8');
            this.config = yaml.load(configContent);
            
            console.log('✅ 监控配置加载成功');
            console.log(`📊 性能指标: ${Object.keys(this.config.performance_metrics || {}).length}`);
            console.log(`📈 业务指标: ${Object.keys(this.config.business_metrics || {}).length}`);
            console.log(`🔧 技术指标: ${Object.keys(this.config.technical_metrics || {}).length}`);
            console.log(`🚨 告警规则: ${(this.config.alert_rules?.system?.length || 0) + (this.config.alert_rules?.business?.length || 0)}`);
            
            return true;
        } catch (error) {
            console.error('❌ 配置加载失败:', error.message);
            return false;
        }
    }

    /**
     * 初始化数据库连接
     */
    async initializeDatabase() {
        return new Promise((resolve, reject) => {
            const dbPath = path.join(process.cwd(), 'data', 'monitoring.db');
            
            // 确保数据目录存在
            const dataDir = path.dirname(dbPath);
            if (!fs.existsSync(dataDir)) {
                fs.mkdirSync(dataDir, { recursive: true });
            }
            
            this.db = new sqlite3.Database(dbPath, (err) => {
                if (err) {
                    console.error('❌ 数据库连接失败:', err.message);
                    reject(err);
                    return;
                }
                
                console.log('✅ 监控数据库连接成功');
                
                // 创建监控表
                this.createMonitoringTables()
                    .then(() => resolve())
                    .catch(reject);
            });
        });
    }

    /**
     * 创建监控相关表
     */
    async createMonitoringTables() {
        return new Promise((resolve, reject) => {
            const tables = [
                `CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    labels TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    environment TEXT
                )`,
                `CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT,
                    condition_text TEXT,
                    labels TEXT,
                    status TEXT DEFAULT 'firing',
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME,
                    environment TEXT
                )`,
                `CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER,
                    channel TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    sent_at DATETIME,
                    error_message TEXT,
                    FOREIGN KEY (alert_id) REFERENCES alerts (id)
                )`
            ];
            
            let completed = 0;
            tables.forEach((sql, index) => {
                this.db.run(sql, (err) => {
                    if (err) {
                        console.error(`❌ 创建表失败 (${index}):`, err.message);
                        reject(err);
                        return;
                    }
                    
                    completed++;
                    if (completed === tables.length) {
                        console.log('✅ 监控表创建完成');
                        resolve();
                    }
                });
            });
        });
    }

    /**
     * 初始化Redis连接
     */
    async initializeRedis() {
        try {
            this.redis = redis.createClient({
                host: process.env.REDIS_HOST || 'localhost',
                port: process.env.REDIS_PORT || 6379,
                password: process.env.REDIS_PASSWORD
            });
            
            await this.redis.connect();
            console.log('✅ Redis连接成功');
            return true;
        } catch (error) {
            console.error('❌ Redis连接失败:', error.message);
            return false;
        }
    }

    /**
     * 初始化通知渠道
     */
    initializeNotificationChannels() {
        const channels = this.config.notifications?.channels || [];
        
        channels.forEach(channel => {
            switch (channel.type) {
                case 'email':
                    this.notificationChannels.set(channel.name, {
                        type: 'email',
                        transporter: nodemailer.createTransporter({
                            host: channel.config.smtp_server,
                            port: channel.config.smtp_port,
                            secure: channel.config.smtp_port === 465,
                            auth: {
                                user: channel.config.username,
                                pass: process.env.SMTP_PASSWORD || channel.config.password
                            }
                        }),
                        config: channel.config
                    });
                    break;
                    
                case 'slack':
                    this.notificationChannels.set(channel.name, {
                        type: 'slack',
                        config: {
                            ...channel.config,
                            webhook_url: process.env.SLACK_WEBHOOK_URL || channel.config.webhook_url
                        }
                    });
                    break;
                    
                case 'webhook':
                    this.notificationChannels.set(channel.name, {
                        type: 'webhook',
                        config: {
                            ...channel.config,
                            url: process.env.ALERT_WEBHOOK_URL || channel.config.url,
                            headers: {
                                ...channel.config.headers,
                                Authorization: `Bearer ${process.env.WEBHOOK_TOKEN || channel.config.headers?.Authorization?.split(' ')[1]}`
                            }
                        }
                    });
                    break;
            }
        });
        
        console.log(`✅ 通知渠道初始化完成: ${this.notificationChannels.size}个`);
    }

    /**
     * 收集系统指标
     */
    async collectSystemMetrics() {
        const os = require('os');
        const fs = require('fs').promises;
        
        try {
            // CPU使用率
            const cpus = os.cpus();
            const cpuUsage = process.cpuUsage();
            const cpuPercent = (cpuUsage.user + cpuUsage.system) / 1000000 / cpus.length * 100;
            
            await this.recordMetric('cpu_usage_percent', cpuPercent, {
                module: 'system',
                environment: process.env.NODE_ENV || 'development'
            });
            
            // 内存使用率
            const totalMem = os.totalmem();
            const freeMem = os.freemem();
            const usedMem = totalMem - freeMem;
            const memPercent = (usedMem / totalMem) * 100;
            
            await this.recordMetric('memory_usage_percent', memPercent, {
                module: 'system',
                environment: process.env.NODE_ENV || 'development'
            });
            
            await this.recordMetric('memory_usage_bytes', usedMem, {
                module: 'system',
                environment: process.env.NODE_ENV || 'development'
            });
            
            // 负载平均值
            const loadAvg = os.loadavg();
            await this.recordMetric('cpu_load_average', loadAvg[0], {
                period: '1m',
                environment: process.env.NODE_ENV || 'development'
            });
            
            // 网络连接数
            const connections = await this.getNetworkConnections();
            await this.recordMetric('network_connections', connections, {
                state: 'established',
                environment: process.env.NODE_ENV || 'development'
            });
            
        } catch (error) {
            console.error('❌ 系统指标收集失败:', error.message);
        }
    }

    /**
     * 获取网络连接数
     */
    async getNetworkConnections() {
        try {
            if (process.platform === 'win32') {
                const { exec } = require('child_process');
                return new Promise((resolve) => {
                    exec('netstat -an | find "ESTABLISHED" /c', (error, stdout) => {
                        if (error) {
                            resolve(0);
                            return;
                        }
                        resolve(parseInt(stdout.trim()) || 0);
                    });
                });
            } else {
                // Linux/Mac
                const { exec } = require('child_process');
                return new Promise((resolve) => {
                    exec('netstat -an | grep ESTABLISHED | wc -l', (error, stdout) => {
                        if (error) {
                            resolve(0);
                            return;
                        }
                        resolve(parseInt(stdout.trim()) || 0);
                    });
                });
            }
        } catch (error) {
            return 0;
        }
    }

    /**
     * 收集应用指标
     */
    async collectApplicationMetrics() {
        try {
            // 从Redis获取应用指标
            if (this.redis) {
                const keys = await this.redis.keys('metrics:*');
                
                for (const key of keys) {
                    const value = await this.redis.get(key);
                    if (value) {
                        const metricData = JSON.parse(value);
                        await this.recordMetric(
                            metricData.name,
                            metricData.value,
                            metricData.labels || {}
                        );
                    }
                }
            }
            
            // 数据库连接数
            await this.recordMetric('db_connections_active', 1, {
                database: 'sqlite',
                environment: process.env.NODE_ENV || 'development'
            });
            
        } catch (error) {
            console.error('❌ 应用指标收集失败:', error.message);
        }
    }

    /**
     * 记录指标
     */
    async recordMetric(name, value, labels = {}) {
        return new Promise((resolve, reject) => {
            const labelsJson = JSON.stringify(labels);
            const environment = labels.environment || process.env.NODE_ENV || 'development';
            
            this.db.run(
                'INSERT INTO metrics (name, value, labels, environment) VALUES (?, ?, ?, ?)',
                [name, value, labelsJson, environment],
                function(err) {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(this.lastID);
                }
            );
        });
    }

    /**
     * 评估告警规则
     */
    async evaluateAlerts() {
        try {
            const systemRules = this.config.alert_rules?.system || [];
            const businessRules = this.config.alert_rules?.business || [];
            const allRules = [...systemRules, ...businessRules];
            
            for (const rule of allRules) {
                await this.evaluateRule(rule);
            }
            
        } catch (error) {
            console.error('❌ 告警规则评估失败:', error.message);
        }
    }

    /**
     * 评估单个规则
     */
    async evaluateRule(rule) {
        try {
            const condition = rule.condition;
            const isFiring = await this.evaluateCondition(condition);
            
            if (isFiring) {
                await this.fireAlert(rule);
            } else {
                await this.resolveAlert(rule.name);
            }
            
        } catch (error) {
            console.error(`❌ 规则评估失败 (${rule.name}):`, error.message);
        }
    }

    /**
     * 评估条件表达式
     */
    async evaluateCondition(condition) {
        try {
            // 简化的条件评估逻辑
            // 实际实现中应该使用更复杂的表达式解析器
            
            if (condition.includes('cpu_usage_percent > 85')) {
                const latestCpuMetric = await this.getLatestMetric('cpu_usage_percent');
                return latestCpuMetric && latestCpuMetric.value > 85;
            }
            
            if (condition.includes('memory_usage_percent > 90')) {
                const latestMemMetric = await this.getLatestMetric('memory_usage_percent');
                return latestMemMetric && latestMemMetric.value > 90;
            }
            
            if (condition.includes('risk_score > 85')) {
                const latestRiskMetric = await this.getLatestMetric('risk_score');
                return latestRiskMetric && latestRiskMetric.value > 85;
            }
            
            if (condition.includes('drawdown_percent > 10')) {
                const latestDrawdownMetric = await this.getLatestMetric('drawdown_percent');
                return latestDrawdownMetric && latestDrawdownMetric.value > 10;
            }
            
            return false;
            
        } catch (error) {
            console.error('❌ 条件评估失败:', error.message);
            return false;
        }
    }

    /**
     * 获取最新指标值
     */
    async getLatestMetric(metricName) {
        return new Promise((resolve, reject) => {
            this.db.get(
                'SELECT * FROM metrics WHERE name = ? ORDER BY timestamp DESC LIMIT 1',
                [metricName],
                (err, row) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(row);
                }
            );
        });
    }

    /**
     * 触发告警
     */
    async fireAlert(rule) {
        try {
            // 检查是否已存在活跃告警
            const existingAlert = await this.getActiveAlert(rule.name);
            if (existingAlert) {
                return; // 告警已存在，不重复触发
            }
            
            // 创建新告警
            const alertId = await this.createAlert(rule);
            
            // 发送通知
            await this.sendAlertNotifications(alertId, rule);
            
            console.log(`🚨 告警触发: ${rule.name} (${rule.severity})`);
            
        } catch (error) {
            console.error(`❌ 告警触发失败 (${rule.name}):`, error.message);
        }
    }

    /**
     * 解决告警
     */
    async resolveAlert(ruleName) {
        try {
            const result = await new Promise((resolve, reject) => {
                this.db.run(
                    'UPDATE alerts SET status = "resolved", resolved_at = CURRENT_TIMESTAMP WHERE rule_name = ? AND status = "firing"',
                    [ruleName],
                    function(err) {
                        if (err) {
                            reject(err);
                            return;
                        }
                        resolve(this.changes);
                    }
                );
            });
            
            if (result > 0) {
                console.log(`✅ 告警解决: ${ruleName}`);
            }
            
        } catch (error) {
            console.error(`❌ 告警解决失败 (${ruleName}):`, error.message);
        }
    }

    /**
     * 获取活跃告警
     */
    async getActiveAlert(ruleName) {
        return new Promise((resolve, reject) => {
            this.db.get(
                'SELECT * FROM alerts WHERE rule_name = ? AND status = "firing"',
                [ruleName],
                (err, row) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(row);
                }
            );
        });
    }

    /**
     * 创建告警记录
     */
    async createAlert(rule) {
        return new Promise((resolve, reject) => {
            const labelsJson = JSON.stringify(rule.labels || {});
            const environment = process.env.NODE_ENV || 'development';
            
            this.db.run(
                'INSERT INTO alerts (rule_name, severity, description, condition_text, labels, environment) VALUES (?, ?, ?, ?, ?, ?)',
                [rule.name, rule.severity, rule.description, rule.condition, labelsJson, environment],
                function(err) {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(this.lastID);
                }
            );
        });
    }

    /**
     * 发送告警通知
     */
    async sendAlertNotifications(alertId, rule) {
        try {
            const routing = this.config.notifications?.routing || [];
            
            // 找到匹配的路由规则
            const matchedRoutes = routing.filter(route => {
                return this.matchesRoute(rule, route.match);
            });
            
            // 如果没有匹配的路由，使用默认路由
            const routes = matchedRoutes.length > 0 ? matchedRoutes : [
                { channels: ['email'], repeat_interval: '15m' }
            ];
            
            for (const route of routes) {
                for (const channelName of route.channels) {
                    await this.sendNotification(alertId, channelName, rule);
                }
            }
            
        } catch (error) {
            console.error(`❌ 通知发送失败 (Alert ${alertId}):`, error.message);
        }
    }

    /**
     * 检查路由匹配
     */
    matchesRoute(rule, match) {
        for (const [key, value] of Object.entries(match)) {
            if (key === 'severity' && rule.severity !== value) {
                return false;
            }
            if (key === 'category' && rule.labels?.category !== value) {
                return false;
            }
            if (key === 'impact' && rule.labels?.impact !== value) {
                return false;
            }
        }
        return true;
    }

    /**
     * 发送通知
     */
    async sendNotification(alertId, channelName, rule) {
        try {
            const channel = this.notificationChannels.get(channelName);
            if (!channel) {
                console.warn(`⚠️ 通知渠道不存在: ${channelName}`);
                return;
            }
            
            // 记录通知尝试
            const notificationId = await this.createNotificationRecord(alertId, channelName);
            
            let success = false;
            let errorMessage = null;
            
            try {
                switch (channel.type) {
                    case 'email':
                        await this.sendEmailNotification(channel, rule);
                        success = true;
                        break;
                        
                    case 'slack':
                        await this.sendSlackNotification(channel, rule);
                        success = true;
                        break;
                        
                    case 'webhook':
                        await this.sendWebhookNotification(channel, rule);
                        success = true;
                        break;
                        
                    default:
                        throw new Error(`不支持的通知类型: ${channel.type}`);
                }
            } catch (error) {
                errorMessage = error.message;
            }
            
            // 更新通知记录
            await this.updateNotificationRecord(notificationId, success, errorMessage);
            
        } catch (error) {
            console.error(`❌ 通知发送失败 (${channelName}):`, error.message);
        }
    }

    /**
     * 发送邮件通知
     */
    async sendEmailNotification(channel, rule) {
        const subject = `[TradeGuard] ${rule.severity.toUpperCase()} - ${rule.description}`;
        const html = `
            <h2>告警通知</h2>
            <p><strong>规则名称:</strong> ${rule.name}</p>
            <p><strong>严重程度:</strong> ${rule.severity}</p>
            <p><strong>描述:</strong> ${rule.description}</p>
            <p><strong>条件:</strong> ${rule.condition}</p>
            <p><strong>时间:</strong> ${new Date().toLocaleString()}</p>
            <p><strong>环境:</strong> ${process.env.NODE_ENV || 'development'}</p>
        `;
        
        await channel.transporter.sendMail({
            from: channel.config.from,
            to: channel.config.to.join(', '),
            subject,
            html
        });
    }

    /**
     * 发送Slack通知
     */
    async sendSlackNotification(channel, rule) {
        const payload = {
            channel: channel.config.channel,
            username: channel.config.username,
            text: `🚨 *${rule.severity.toUpperCase()}* - ${rule.description}`,
            attachments: [
                {
                    color: rule.severity === 'critical' ? 'danger' : 'warning',
                    fields: [
                        { title: '规则名称', value: rule.name, short: true },
                        { title: '严重程度', value: rule.severity, short: true },
                        { title: '条件', value: rule.condition, short: false },
                        { title: '时间', value: new Date().toLocaleString(), short: true },
                        { title: '环境', value: process.env.NODE_ENV || 'development', short: true }
                    ]
                }
            ]
        };
        
        await axios.post(channel.config.webhook_url, payload);
    }

    /**
     * 发送Webhook通知
     */
    async sendWebhookNotification(channel, rule) {
        const payload = {
            alert: {
                name: rule.name,
                severity: rule.severity,
                description: rule.description,
                condition: rule.condition,
                labels: rule.labels || {},
                timestamp: new Date().toISOString(),
                environment: process.env.NODE_ENV || 'development'
            }
        };
        
        await axios.post(channel.config.url, payload, {
            headers: channel.config.headers
        });
    }

    /**
     * 创建通知记录
     */
    async createNotificationRecord(alertId, channel) {
        return new Promise((resolve, reject) => {
            this.db.run(
                'INSERT INTO notifications (alert_id, channel) VALUES (?, ?)',
                [alertId, channel],
                function(err) {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(this.lastID);
                }
            );
        });
    }

    /**
     * 更新通知记录
     */
    async updateNotificationRecord(notificationId, success, errorMessage) {
        return new Promise((resolve, reject) => {
            const status = success ? 'sent' : 'failed';
            const sentAt = success ? new Date().toISOString() : null;
            
            this.db.run(
                'UPDATE notifications SET status = ?, sent_at = ?, error_message = ? WHERE id = ?',
                [status, sentAt, errorMessage, notificationId],
                function(err) {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(this.changes);
                }
            );
        });
    }

    /**
     * 启动监控
     */
    async start() {
        try {
            console.log('🚀 启动告警管理器...');
            
            // 加载配置
            const configLoaded = await this.loadConfig();
            if (!configLoaded) {
                throw new Error('配置加载失败');
            }
            
            // 初始化数据库
            await this.initializeDatabase();
            
            // 初始化Redis
            await this.initializeRedis();
            
            // 初始化通知渠道
            this.initializeNotificationChannels();
            
            this.isRunning = true;
            
            // 启动监控循环
            this.startMonitoringLoop();
            
            console.log('✅ 告警管理器启动成功');
            
        } catch (error) {
            console.error('❌ 告警管理器启动失败:', error.message);
            process.exit(1);
        }
    }

    /**
     * 启动监控循环
     */
    startMonitoringLoop() {
        const metricsInterval = this.parseInterval(this.config.monitoring?.intervals?.metrics_collection || '30s');
        const alertInterval = this.parseInterval(this.config.monitoring?.intervals?.alert_evaluation || '60s');
        
        // 指标收集循环
        setInterval(async () => {
            if (this.isRunning) {
                await this.collectSystemMetrics();
                await this.collectApplicationMetrics();
            }
        }, metricsInterval);
        
        // 告警评估循环
        setInterval(async () => {
            if (this.isRunning) {
                await this.evaluateAlerts();
            }
        }, alertInterval);
        
        console.log(`📊 监控循环已启动 (指标: ${metricsInterval}ms, 告警: ${alertInterval}ms)`);
    }

    /**
     * 解析时间间隔
     */
    parseInterval(interval) {
        const match = interval.match(/^(\d+)([smh])$/);
        if (!match) {
            return 30000; // 默认30秒
        }
        
        const value = parseInt(match[1]);
        const unit = match[2];
        
        switch (unit) {
            case 's': return value * 1000;
            case 'm': return value * 60 * 1000;
            case 'h': return value * 60 * 60 * 1000;
            default: return 30000;
        }
    }

    /**
     * 停止监控
     */
    async stop() {
        console.log('🛑 停止告警管理器...');
        
        this.isRunning = false;
        
        // 关闭数据库连接
        if (this.db) {
            this.db.close();
        }
        
        // 关闭Redis连接
        if (this.redis) {
            await this.redis.quit();
        }
        
        console.log('✅ 告警管理器已停止');
    }

    /**
     * 获取监控状态
     */
    async getStatus() {
        try {
            const activeAlerts = await new Promise((resolve, reject) => {
                this.db.all(
                    'SELECT COUNT(*) as count FROM alerts WHERE status = "firing"',
                    (err, rows) => {
                        if (err) {
                            reject(err);
                            return;
                        }
                        resolve(rows[0].count);
                    }
                );
            });
            
            const totalMetrics = await new Promise((resolve, reject) => {
                this.db.all(
                    'SELECT COUNT(*) as count FROM metrics WHERE timestamp > datetime("now", "-1 hour")',
                    (err, rows) => {
                        if (err) {
                            reject(err);
                            return;
                        }
                        resolve(rows[0].count);
                    }
                );
            });
            
            return {
                running: this.isRunning,
                active_alerts: activeAlerts,
                metrics_last_hour: totalMetrics,
                notification_channels: this.notificationChannels.size,
                uptime: process.uptime()
            };
            
        } catch (error) {
            console.error('❌ 获取状态失败:', error.message);
            return {
                running: this.isRunning,
                error: error.message
            };
        }
    }
}

// 主程序
if (require.main === module) {
    const configPath = process.argv[2] || path.join(__dirname, '..', 'config', 'monitoring.yaml');
    const alertManager = new AlertManager(configPath);
    
    // 处理进程信号
    process.on('SIGINT', async () => {
        console.log('\n收到SIGINT信号，正在关闭...');
        await alertManager.stop();
        process.exit(0);
    });
    
    process.on('SIGTERM', async () => {
        console.log('\n收到SIGTERM信号，正在关闭...');
        await alertManager.stop();
        process.exit(0);
    });
    
    // 启动告警管理器
    alertManager.start().catch(error => {
        console.error('❌ 启动失败:', error.message);
        process.exit(1);
    });
}

module.exports = AlertManager;