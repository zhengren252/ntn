#!/usr/bin/env node

/**
 * 交易执行铁三角项目 - 指标收集器
 * 负责收集系统、应用和业务指标，并存储到Redis和数据库
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { exec } = require('child_process');
const { promisify } = require('util');
const redis = require('redis');
const sqlite3 = require('sqlite3').verbose();
const axios = require('axios');

const execAsync = promisify(exec);

class MetricsCollector {
    constructor() {
        this.redis = null;
        this.db = null;
        this.isRunning = false;
        this.collectionIntervals = new Map();
        this.lastCollectionTime = new Map();
        
        // 指标缓存
        this.metricsCache = new Map();
        
        // 绑定方法
        this.initializeRedis = this.initializeRedis.bind(this);
        this.initializeDatabase = this.initializeDatabase.bind(this);
        this.collectSystemMetrics = this.collectSystemMetrics.bind(this);
        this.collectApplicationMetrics = this.collectApplicationMetrics.bind(this);
        this.collectBusinessMetrics = this.collectBusinessMetrics.bind(this);
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
                resolve();
            });
        });
    }

    /**
     * 收集系统指标
     */
    async collectSystemMetrics() {
        try {
            const environment = process.env.NODE_ENV || 'development';
            const timestamp = new Date().toISOString();
            
            // CPU指标
            const cpuMetrics = await this.getCPUMetrics();
            await this.storeMetrics('cpu_usage_percent', cpuMetrics.usage, {
                module: 'system',
                environment
            }, timestamp);
            
            await this.storeMetrics('cpu_load_average', cpuMetrics.loadAvg[0], {
                period: '1m',
                environment
            }, timestamp);
            
            // 内存指标
            const memoryMetrics = await this.getMemoryMetrics();
            await this.storeMetrics('memory_usage_bytes', memoryMetrics.used, {
                module: 'system',
                environment
            }, timestamp);
            
            await this.storeMetrics('memory_usage_percent', memoryMetrics.percent, {
                module: 'system',
                environment
            }, timestamp);
            
            // 磁盘指标
            const diskMetrics = await this.getDiskMetrics();
            for (const disk of diskMetrics) {
                await this.storeMetrics('disk_usage_bytes', disk.used, {
                    mount_point: disk.mountPoint,
                    environment
                }, timestamp);
            }
            
            // 网络指标
            const networkMetrics = await this.getNetworkMetrics();
            await this.storeMetrics('network_bytes_sent', networkMetrics.bytesSent, {
                interface: 'total',
                environment
            }, timestamp);
            
            await this.storeMetrics('network_bytes_received', networkMetrics.bytesReceived, {
                interface: 'total',
                environment
            }, timestamp);
            
            await this.storeMetrics('network_connections', networkMetrics.connections, {
                state: 'established',
                environment
            }, timestamp);
            
            console.log('📊 系统指标收集完成');
            
        } catch (error) {
            console.error('❌ 系统指标收集失败:', error.message);
        }
    }

    /**
     * 获取CPU指标
     */
    async getCPUMetrics() {
        const cpus = os.cpus();
        const loadAvg = os.loadavg();
        
        // 计算CPU使用率
        let totalIdle = 0;
        let totalTick = 0;
        
        cpus.forEach(cpu => {
            for (const type in cpu.times) {
                totalTick += cpu.times[type];
            }
            totalIdle += cpu.times.idle;
        });
        
        const idle = totalIdle / cpus.length;
        const total = totalTick / cpus.length;
        const usage = 100 - ~~(100 * idle / total);
        
        return {
            usage,
            loadAvg,
            cores: cpus.length
        };
    }

    /**
     * 获取内存指标
     */
    async getMemoryMetrics() {
        const totalMem = os.totalmem();
        const freeMem = os.freemem();
        const usedMem = totalMem - freeMem;
        const percent = (usedMem / totalMem) * 100;
        
        return {
            total: totalMem,
            free: freeMem,
            used: usedMem,
            percent
        };
    }

    /**
     * 获取磁盘指标
     */
    async getDiskMetrics() {
        try {
            const disks = [];
            
            if (process.platform === 'win32') {
                // Windows
                const { stdout } = await execAsync('wmic logicaldisk get size,freespace,caption');
                const lines = stdout.split('\n').filter(line => line.trim() && !line.includes('Caption'));
                
                for (const line of lines) {
                    const parts = line.trim().split(/\s+/);
                    if (parts.length >= 3) {
                        const caption = parts[0];
                        const freeSpace = parseInt(parts[1]) || 0;
                        const size = parseInt(parts[2]) || 0;
                        const used = size - freeSpace;
                        
                        disks.push({
                            mountPoint: caption,
                            total: size,
                            free: freeSpace,
                            used,
                            percent: size > 0 ? (used / size) * 100 : 0
                        });
                    }
                }
            } else {
                // Linux/Mac
                const { stdout } = await execAsync('df -B1');
                const lines = stdout.split('\n').slice(1).filter(line => line.trim());
                
                for (const line of lines) {
                    const parts = line.trim().split(/\s+/);
                    if (parts.length >= 6) {
                        const total = parseInt(parts[1]) || 0;
                        const used = parseInt(parts[2]) || 0;
                        const free = parseInt(parts[3]) || 0;
                        const mountPoint = parts[5];
                        
                        disks.push({
                            mountPoint,
                            total,
                            free,
                            used,
                            percent: total > 0 ? (used / total) * 100 : 0
                        });
                    }
                }
            }
            
            return disks;
            
        } catch (error) {
            console.error('❌ 磁盘指标获取失败:', error.message);
            return [];
        }
    }

    /**
     * 获取网络指标
     */
    async getNetworkMetrics() {
        try {
            const networkInterfaces = os.networkInterfaces();
            let bytesSent = 0;
            let bytesReceived = 0;
            
            // 从系统获取网络统计
            if (process.platform === 'win32') {
                // Windows - 使用性能计数器
                try {
                    const { stdout } = await execAsync('typeperf "\\Network Interface(*)\\Bytes Sent/sec" -sc 1');
                    // 解析输出...
                } catch (error) {
                    // 使用默认值
                }
            } else {
                // Linux/Mac - 读取 /proc/net/dev
                try {
                    const { stdout } = await execAsync('cat /proc/net/dev');
                    const lines = stdout.split('\n').slice(2);
                    
                    for (const line of lines) {
                        if (line.trim()) {
                            const parts = line.trim().split(/\s+/);
                            if (parts.length >= 10) {
                                bytesReceived += parseInt(parts[1]) || 0;
                                bytesSent += parseInt(parts[9]) || 0;
                            }
                        }
                    }
                } catch (error) {
                    // 使用默认值
                }
            }
            
            // 获取连接数
            const connections = await this.getNetworkConnections();
            
            return {
                bytesSent,
                bytesReceived,
                connections
            };
            
        } catch (error) {
            console.error('❌ 网络指标获取失败:', error.message);
            return {
                bytesSent: 0,
                bytesReceived: 0,
                connections: 0
            };
        }
    }

    /**
     * 获取网络连接数
     */
    async getNetworkConnections() {
        try {
            if (process.platform === 'win32') {
                const { stdout } = await execAsync('netstat -an | find "ESTABLISHED" /c');
                return parseInt(stdout.trim()) || 0;
            } else {
                const { stdout } = await execAsync('netstat -an | grep ESTABLISHED | wc -l');
                return parseInt(stdout.trim()) || 0;
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
            const environment = process.env.NODE_ENV || 'development';
            const timestamp = new Date().toISOString();
            
            // API指标
            await this.collectAPIMetrics(environment, timestamp);
            
            // 数据库指标
            await this.collectDatabaseMetrics(environment, timestamp);
            
            // 缓存指标
            await this.collectCacheMetrics(environment, timestamp);
            
            // ZeroMQ指标
            await this.collectZMQMetrics(environment, timestamp);
            
            console.log('📊 应用指标收集完成');
            
        } catch (error) {
            console.error('❌ 应用指标收集失败:', error.message);
        }
    }

    /**
     * 收集API指标
     */
    async collectAPIMetrics(environment, timestamp) {
        try {
            // 检查API健康状态
            const apiUrl = process.env.API_URL || 'http://localhost:3001';
            const startTime = Date.now();
            
            try {
                const response = await axios.get(`${apiUrl}/health`, { timeout: 5000 });
                const duration = Date.now() - startTime;
                
                await this.storeMetrics('http_request_duration', duration, {
                    method: 'GET',
                    endpoint: '/health',
                    environment
                }, timestamp);
                
                await this.storeMetrics('http_requests_total', 1, {
                    method: 'GET',
                    endpoint: '/health',
                    status_code: response.status.toString(),
                    environment
                }, timestamp);
                
            } catch (error) {
                const duration = Date.now() - startTime;
                
                await this.storeMetrics('http_request_duration', duration, {
                    method: 'GET',
                    endpoint: '/health',
                    environment
                }, timestamp);
                
                await this.storeMetrics('http_requests_total', 1, {
                    method: 'GET',
                    endpoint: '/health',
                    status_code: '500',
                    environment
                }, timestamp);
            }
            
        } catch (error) {
            console.error('❌ API指标收集失败:', error.message);
        }
    }

    /**
     * 收集数据库指标
     */
    async collectDatabaseMetrics(environment, timestamp) {
        try {
            if (this.db) {
                // 数据库连接数（SQLite只有一个连接）
                await this.storeMetrics('db_connections_active', 1, {
                    database: 'sqlite',
                    environment
                }, timestamp);
                
                // 数据库大小
                const dbPath = path.join(process.cwd(), 'data', 'development.db');
                if (fs.existsSync(dbPath)) {
                    const stats = fs.statSync(dbPath);
                    await this.storeMetrics('db_size_bytes', stats.size, {
                        database: 'main',
                        environment
                    }, timestamp);
                }
                
                // 测试查询性能
                const queryStart = Date.now();
                await new Promise((resolve, reject) => {
                    this.db.get('SELECT COUNT(*) as count FROM sqlite_master', (err, row) => {
                        if (err) {
                            reject(err);
                            return;
                        }
                        resolve(row);
                    });
                });
                const queryDuration = Date.now() - queryStart;
                
                await this.storeMetrics('db_query_duration', queryDuration, {
                    operation: 'SELECT',
                    table: 'sqlite_master',
                    environment
                }, timestamp);
            }
            
        } catch (error) {
            console.error('❌ 数据库指标收集失败:', error.message);
        }
    }

    /**
     * 收集缓存指标
     */
    async collectCacheMetrics(environment, timestamp) {
        try {
            if (this.redis) {
                // Redis内存使用
                const info = await this.redis.info('memory');
                const memoryMatch = info.match(/used_memory:(\d+)/);
                if (memoryMatch) {
                    const memoryUsage = parseInt(memoryMatch[1]);
                    await this.storeMetrics('cache_memory_usage', memoryUsage, {
                        cache_type: 'redis',
                        environment
                    }, timestamp);
                }
                
                // 缓存命中率（模拟）
                const hitRatio = 85 + Math.random() * 10; // 85-95%
                await this.storeMetrics('cache_hit_ratio', hitRatio, {
                    cache_type: 'redis',
                    environment
                }, timestamp);
                
                // 缓存操作数
                await this.storeMetrics('cache_operations_total', 1, {
                    operation: 'get',
                    cache_type: 'redis',
                    environment
                }, timestamp);
            }
            
        } catch (error) {
            console.error('❌ 缓存指标收集失败:', error.message);
        }
    }

    /**
     * 收集ZeroMQ指标
     */
    async collectZMQMetrics(environment, timestamp) {
        try {
            // 检查ZMQ代理是否运行
            const zmqPort = process.env.ZMQ_PORT || 5555;
            
            try {
                const net = require('net');
                const socket = new net.Socket();
                
                await new Promise((resolve, reject) => {
                    socket.setTimeout(1000);
                    
                    socket.on('connect', () => {
                        socket.destroy();
                        resolve();
                    });
                    
                    socket.on('timeout', () => {
                        socket.destroy();
                        reject(new Error('连接超时'));
                    });
                    
                    socket.on('error', (err) => {
                        reject(err);
                    });
                    
                    socket.connect(zmqPort, 'localhost');
                });
                
                // ZMQ代理可用
                await this.storeMetrics('zmq_broker_up', 1, {
                    environment
                }, timestamp);
                
                // 模拟消息指标
                await this.storeMetrics('zmq_messages_sent', Math.floor(Math.random() * 100), {
                    socket_type: 'dealer',
                    endpoint: 'tcp://localhost:5555',
                    environment
                }, timestamp);
                
                await this.storeMetrics('zmq_messages_received', Math.floor(Math.random() * 100), {
                    socket_type: 'router',
                    endpoint: 'tcp://localhost:5555',
                    environment
                }, timestamp);
                
            } catch (error) {
                // ZMQ代理不可用
                await this.storeMetrics('zmq_broker_up', 0, {
                    environment
                }, timestamp);
            }
            
        } catch (error) {
            console.error('❌ ZeroMQ指标收集失败:', error.message);
        }
    }

    /**
     * 收集业务指标
     */
    async collectBusinessMetrics() {
        try {
            const environment = process.env.NODE_ENV || 'development';
            const timestamp = new Date().toISOString();
            
            // 交易指标
            await this.collectTradingMetrics(environment, timestamp);
            
            // 风控指标
            await this.collectRiskMetrics(environment, timestamp);
            
            // 财务指标
            await this.collectFinanceMetrics(environment, timestamp);
            
            console.log('📊 业务指标收集完成');
            
        } catch (error) {
            console.error('❌ 业务指标收集失败:', error.message);
        }
    }

    /**
     * 收集交易指标
     */
    async collectTradingMetrics(environment, timestamp) {
        try {
            // 模拟交易指标
            const ordersPerSecond = Math.floor(Math.random() * 50) + 10;
            await this.storeMetrics('orders_per_second', ordersPerSecond, {
                environment
            }, timestamp);
            
            const orderExecutionTime = Math.floor(Math.random() * 500) + 100;
            await this.storeMetrics('order_execution_time', orderExecutionTime, {
                order_type: 'market',
                environment
            }, timestamp);
            
            const tradeVolume = Math.floor(Math.random() * 1000000) + 100000;
            await this.storeMetrics('trade_volume', tradeVolume, {
                symbol: 'BTCUSDT',
                currency: 'USDT',
                environment
            }, timestamp);
            
            const positionValue = Math.floor(Math.random() * 5000000) + 1000000;
            await this.storeMetrics('position_value', positionValue, {
                symbol: 'BTCUSDT',
                currency: 'USDT',
                environment
            }, timestamp);
            
        } catch (error) {
            console.error('❌ 交易指标收集失败:', error.message);
        }
    }

    /**
     * 收集风控指标
     */
    async collectRiskMetrics(environment, timestamp) {
        try {
            // 模拟风控指标
            const riskScore = Math.floor(Math.random() * 40) + 30; // 30-70
            await this.storeMetrics('risk_score', riskScore, {
                strategy: 'momentum',
                symbol: 'BTCUSDT',
                environment
            }, timestamp);
            
            const drawdownPercent = Math.random() * 3 + 1; // 1-4%
            await this.storeMetrics('drawdown_percent', drawdownPercent, {
                strategy: 'momentum',
                environment
            }, timestamp);
            
            const riskAssessmentTime = Math.floor(Math.random() * 1000) + 500;
            await this.storeMetrics('risk_assessment_time', riskAssessmentTime, {
                assessment_type: 'portfolio',
                environment
            }, timestamp);
            
        } catch (error) {
            console.error('❌ 风控指标收集失败:', error.message);
        }
    }

    /**
     * 收集财务指标
     */
    async collectFinanceMetrics(environment, timestamp) {
        try {
            // 模拟财务指标
            const accountBalance = Math.floor(Math.random() * 500000) + 200000;
            await this.storeMetrics('account_balance', accountBalance, {
                account_type: 'trading',
                currency: 'USDT',
                environment
            }, timestamp);
            
            const fundAllocationAmount = Math.floor(Math.random() * 100000) + 50000;
            await this.storeMetrics('fund_allocation_amount', fundAllocationAmount, {
                allocation_type: 'strategy',
                currency: 'USDT',
                environment
            }, timestamp);
            
            const budgetApprovalTime = Math.floor(Math.random() * 3600000) + 1800000; // 30min-90min
            await this.storeMetrics('budget_approval_time', budgetApprovalTime, {
                request_type: 'increase',
                environment
            }, timestamp);
            
        } catch (error) {
            console.error('❌ 财务指标收集失败:', error.message);
        }
    }

    /**
     * 存储指标
     */
    async storeMetrics(name, value, labels = {}, timestamp = null) {
        try {
            const ts = timestamp || new Date().toISOString();
            const environment = labels.environment || process.env.NODE_ENV || 'development';
            
            // 存储到Redis
            if (this.redis) {
                const metricKey = `metrics:${name}:${Date.now()}`;
                const metricData = {
                    name,
                    value,
                    labels,
                    timestamp: ts
                };
                
                await this.redis.setEx(metricKey, 3600, JSON.stringify(metricData)); // 1小时过期
                
                // 更新最新值
                const latestKey = `metrics:latest:${name}`;
                await this.redis.setEx(latestKey, 300, JSON.stringify(metricData)); // 5分钟过期
            }
            
            // 存储到数据库
            if (this.db) {
                await new Promise((resolve, reject) => {
                    const labelsJson = JSON.stringify(labels);
                    
                    this.db.run(
                        'INSERT INTO metrics (name, value, labels, environment, timestamp) VALUES (?, ?, ?, ?, ?)',
                        [name, value, labelsJson, environment, ts],
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
            
        } catch (error) {
            console.error(`❌ 指标存储失败 (${name}):`, error.message);
        }
    }

    /**
     * 启动指标收集
     */
    async start() {
        try {
            console.log('🚀 启动指标收集器...');
            
            // 初始化连接
            await this.initializeDatabase();
            await this.initializeRedis();
            
            this.isRunning = true;
            
            // 启动收集循环
            this.startCollectionLoop();
            
            console.log('✅ 指标收集器启动成功');
            
        } catch (error) {
            console.error('❌ 指标收集器启动失败:', error.message);
            process.exit(1);
        }
    }

    /**
     * 启动收集循环
     */
    startCollectionLoop() {
        // 系统指标收集 - 每30秒
        this.collectionIntervals.set('system', setInterval(async () => {
            if (this.isRunning) {
                await this.collectSystemMetrics();
            }
        }, 30000));
        
        // 应用指标收集 - 每60秒
        this.collectionIntervals.set('application', setInterval(async () => {
            if (this.isRunning) {
                await this.collectApplicationMetrics();
            }
        }, 60000));
        
        // 业务指标收集 - 每120秒
        this.collectionIntervals.set('business', setInterval(async () => {
            if (this.isRunning) {
                await this.collectBusinessMetrics();
            }
        }, 120000));
        
        console.log('📊 指标收集循环已启动');
        console.log('  - 系统指标: 每30秒');
        console.log('  - 应用指标: 每60秒');
        console.log('  - 业务指标: 每120秒');
    }

    /**
     * 停止指标收集
     */
    async stop() {
        console.log('🛑 停止指标收集器...');
        
        this.isRunning = false;
        
        // 清除所有定时器
        for (const [name, interval] of this.collectionIntervals) {
            clearInterval(interval);
            console.log(`  - 已停止${name}指标收集`);
        }
        this.collectionIntervals.clear();
        
        // 关闭连接
        if (this.db) {
            this.db.close();
        }
        
        if (this.redis) {
            await this.redis.quit();
        }
        
        console.log('✅ 指标收集器已停止');
    }

    /**
     * 获取收集状态
     */
    getStatus() {
        return {
            running: this.isRunning,
            active_collectors: this.collectionIntervals.size,
            last_collection_times: Object.fromEntries(this.lastCollectionTime),
            cache_size: this.metricsCache.size,
            uptime: process.uptime()
        };
    }
}

// 主程序
if (require.main === module) {
    const collector = new MetricsCollector();
    
    // 处理进程信号
    process.on('SIGINT', async () => {
        console.log('\n收到SIGINT信号，正在关闭...');
        await collector.stop();
        process.exit(0);
    });
    
    process.on('SIGTERM', async () => {
        console.log('\n收到SIGTERM信号，正在关闭...');
        await collector.stop();
        process.exit(0);
    });
    
    // 启动指标收集器
    collector.start().catch(error => {
        console.error('❌ 启动失败:', error.message);
        process.exit(1);
    });
}

module.exports = MetricsCollector;