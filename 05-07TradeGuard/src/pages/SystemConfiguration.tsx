import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Settings, 
  Shield, 
  Database, 
  Wifi, 
  Clock, 
  Save, 
  RefreshCw, 
  AlertTriangle,
  CheckCircle,
  Eye,
  EyeOff,
  Activity
} from 'lucide-react';

interface ConfigSection {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  configs: ConfigItem[];
}

interface ConfigItem {
  id: string;
  name: string;
  description: string;
  type: 'string' | 'number' | 'boolean' | 'password' | 'textarea';
  value: string | number | boolean;
  defaultValue: string | number | boolean;
  required: boolean;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
  sensitive?: boolean;
}

interface EnvironmentConfig {
  name: string;
  active: boolean;
  configs: Record<string, string | number | boolean>;
}

const SystemConfiguration: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'general' | 'security' | 'database' | 'messaging' | 'monitoring'>('general');
  const [currentEnvironment, setCurrentEnvironment] = useState<'development' | 'staging' | 'production'>('development');
  const [isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showSensitive, setShowSensitive] = useState<{ [key: string]: boolean }>({});
  
  // 环境配置
  const [environments] = useState<Record<string, EnvironmentConfig>>({
    development: {
      name: '开发环境',
      active: true,
      configs: {}
    },
    staging: {
      name: '测试环境',
      active: false,
      configs: {}
    },
    production: {
      name: '生产环境',
      active: false,
      configs: {}
    }
  });

  // 配置分组
  const [configSections, setConfigSections] = useState<ConfigSection[]>([
    {
      id: 'general',
      name: '通用设置',
      description: '系统基本配置参数',
      icon: Settings,
      configs: [
        {
          id: 'system_name',
          name: '系统名称',
          description: '交易系统的显示名称',
          type: 'string',
          value: 'TradeGuard 交易执行铁三角',
          defaultValue: 'TradeGuard 交易执行铁三角',
          required: true
        },
        {
          id: 'max_concurrent_strategies',
          name: '最大并发策略数',
          description: '系统同时执行的最大策略数量',
          type: 'number',
          value: 10,
          defaultValue: 10,
          required: true,
          validation: { min: 1, max: 50 }
        },
        {
          id: 'session_timeout',
          name: '会话超时时间',
          description: '用户会话超时时间（分钟）',
          type: 'number',
          value: 30,
          defaultValue: 30,
          required: true,
          validation: { min: 5, max: 480 }
        },
        {
          id: 'enable_debug_mode',
          name: '调试模式',
          description: '启用系统调试模式',
          type: 'boolean',
          value: true,
          defaultValue: false,
          required: false
        }
      ]
    },
    {
      id: 'security',
      name: '安全设置',
      description: '系统安全和认证配置',
      icon: Shield,
      configs: [
        {
          id: 'jwt_secret',
          name: 'JWT密钥',
          description: 'JSON Web Token签名密钥',
          type: 'password',
          value: 'your-super-secret-jwt-key-here',
          defaultValue: '',
          required: true,
          sensitive: true
        },
        {
          id: 'password_min_length',
          name: '密码最小长度',
          description: '用户密码的最小长度要求',
          type: 'number',
          value: 8,
          defaultValue: 8,
          required: true,
          validation: { min: 6, max: 32 }
        },
        {
          id: 'max_login_attempts',
          name: '最大登录尝试次数',
          description: '账户锁定前的最大登录失败次数',
          type: 'number',
          value: 5,
          defaultValue: 5,
          required: true,
          validation: { min: 3, max: 10 }
        },
        {
          id: 'enable_2fa',
          name: '启用双因子认证',
          description: '强制要求用户使用双因子认证',
          type: 'boolean',
          value: false,
          defaultValue: false,
          required: false
        },
        {
          id: 'api_rate_limit',
          name: 'API速率限制',
          description: '每分钟API调用次数限制',
          type: 'number',
          value: 1000,
          defaultValue: 1000,
          required: true,
          validation: { min: 100, max: 10000 }
        }
      ]
    },
    {
      id: 'database',
      name: '数据库设置',
      description: '数据库连接和配置',
      icon: Database,
      configs: [
        {
          id: 'db_host',
          name: '数据库主机',
          description: '数据库服务器地址',
          type: 'string',
          value: 'localhost',
          defaultValue: 'localhost',
          required: true
        },
        {
          id: 'db_port',
          name: '数据库端口',
          description: '数据库服务器端口',
          type: 'number',
          value: 5432,
          defaultValue: 5432,
          required: true,
          validation: { min: 1, max: 65535 }
        },
        {
          id: 'db_name',
          name: '数据库名称',
          description: '数据库名称',
          type: 'string',
          value: 'tradeguard',
          defaultValue: 'tradeguard',
          required: true
        },
        {
          id: 'db_username',
          name: '数据库用户名',
          description: '数据库连接用户名',
          type: 'string',
          value: 'tradeguard_user',
          defaultValue: '',
          required: true
        },
        {
          id: 'db_password',
          name: '数据库密码',
          description: '数据库连接密码',
          type: 'password',
          value: 'secure_password_123',
          defaultValue: '',
          required: true,
          sensitive: true
        },
        {
          id: 'db_pool_size',
          name: '连接池大小',
          description: '数据库连接池最大连接数',
          type: 'number',
          value: 20,
          defaultValue: 20,
          required: true,
          validation: { min: 5, max: 100 }
        }
      ]
    },
    {
      id: 'messaging',
      name: '消息队列',
      description: 'ZeroMQ和Redis配置',
      icon: Wifi,
      configs: [
        {
          id: 'zeromq_port',
          name: 'ZeroMQ端口',
          description: 'ZeroMQ消息总线端口',
          type: 'number',
          value: 5555,
          defaultValue: 5555,
          required: true,
          validation: { min: 1024, max: 65535 }
        },
        {
          id: 'redis_host',
          name: 'Redis主机',
          description: 'Redis缓存服务器地址',
          type: 'string',
          value: 'localhost',
          defaultValue: 'localhost',
          required: true
        },
        {
          id: 'redis_port',
          name: 'Redis端口',
          description: 'Redis服务器端口',
          type: 'number',
          value: 6379,
          defaultValue: 6379,
          required: true,
          validation: { min: 1, max: 65535 }
        },
        {
          id: 'redis_password',
          name: 'Redis密码',
          description: 'Redis连接密码（可选）',
          type: 'password',
          value: '',
          defaultValue: '',
          required: false,
          sensitive: true
        },
        {
          id: 'message_queue_size',
          name: '消息队列大小',
          description: '消息队列最大容量',
          type: 'number',
          value: 10000,
          defaultValue: 10000,
          required: true,
          validation: { min: 1000, max: 100000 }
        },
        {
          id: 'enable_message_persistence',
          name: '启用消息持久化',
          description: '将消息持久化到磁盘',
          type: 'boolean',
          value: true,
          defaultValue: true,
          required: false
        }
      ]
    },
    {
      id: 'monitoring',
      name: '监控告警',
      description: '系统监控和告警配置',
      icon: Activity,
      configs: [
        {
          id: 'health_check_interval',
          name: '健康检查间隔',
          description: '系统健康检查间隔时间（秒）',
          type: 'number',
          value: 30,
          defaultValue: 30,
          required: true,
          validation: { min: 10, max: 300 }
        },
        {
          id: 'alert_email',
          name: '告警邮箱',
          description: '接收系统告警的邮箱地址',
          type: 'string',
          value: 'admin@tradeguard.com',
          defaultValue: '',
          required: false
        },
        {
          id: 'cpu_threshold',
          name: 'CPU告警阈值',
          description: 'CPU使用率告警阈值（%）',
          type: 'number',
          value: 80,
          defaultValue: 80,
          required: true,
          validation: { min: 50, max: 95 }
        },
        {
          id: 'memory_threshold',
          name: '内存告警阈值',
          description: '内存使用率告警阈值（%）',
          type: 'number',
          value: 85,
          defaultValue: 85,
          required: true,
          validation: { min: 50, max: 95 }
        },
        {
          id: 'enable_slack_notifications',
          name: '启用Slack通知',
          description: '发送告警到Slack频道',
          type: 'boolean',
          value: false,
          defaultValue: false,
          required: false
        },
        {
          id: 'slack_webhook_url',
          name: 'Slack Webhook URL',
          description: 'Slack通知的Webhook地址',
          type: 'textarea',
          value: '',
          defaultValue: '',
          required: false,
          sensitive: true
        }
      ]
    }
  ]);

  // 更新配置值
  const updateConfigValue = (sectionId: string, configId: string, value: string | number | boolean) => {
    setConfigSections(prev => prev.map(section => 
      section.id === sectionId 
        ? {
            ...section,
            configs: section.configs.map(config => 
              config.id === configId ? { ...config, value } : config
            )
          }
        : section
    ));
    setHasChanges(true);
  };

  // 保存配置
  const saveConfiguration = async () => {
    setIsLoading(true);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000));
    setHasChanges(false);
    setIsLoading(false);
  };

  // 重置配置
  const resetConfiguration = () => {
    setConfigSections(prev => prev.map(section => ({
      ...section,
      configs: section.configs.map(config => ({
        ...config,
        value: config.defaultValue
      }))
    })));
    setHasChanges(true);
  };

  // 切换敏感信息显示
  const toggleSensitiveVisibility = (configId: string) => {
    setShowSensitive(prev => ({
      ...prev,
      [configId]: !prev[configId]
    }));
  };

  // 验证配置值
  const validateConfig = (config: ConfigItem): string | null => {
    if (config.required && (!config.value || config.value === '')) {
      return '此字段为必填项';
    }
    
    if (config.type === 'number' && config.validation) {
      const numValue = Number(config.value);
      if (config.validation.min !== undefined && numValue < config.validation.min) {
        return `值不能小于 ${config.validation.min}`;
      }
      if (config.validation.max !== undefined && numValue > config.validation.max) {
        return `值不能大于 ${config.validation.max}`;
      }
    }
    
    return null;
  };

  // 获取当前标签页的配置
  const getCurrentSection = () => {
    return configSections.find(section => section.id === activeTab);
  };

  // 渲染配置输入组件
  const renderConfigInput = (config: ConfigItem, sectionId: string) => {
    const error = validateConfig(config);
    const isPassword = config.type === 'password';
    const shouldShowValue = !config.sensitive || showSensitive[config.id];
    
    return (
      <div key={config.id} className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor={config.id} className="flex items-center space-x-2">
            <span>{config.name}</span>
            {config.required && <span className="text-red-500">*</span>}
            {config.sensitive && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => toggleSensitiveVisibility(config.id)}
                className="h-6 w-6 p-0"
              >
                {shouldShowValue ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              </Button>
            )}
          </Label>
        </div>
        
        {config.type === 'boolean' ? (
          <div className="flex items-center space-x-2">
            <Switch
              id={config.id}
              checked={Boolean(config.value)}
              onCheckedChange={(checked) => updateConfigValue(sectionId, config.id, checked)}
            />
            <span className="text-sm text-gray-600">{config.description}</span>
          </div>
        ) : config.type === 'textarea' ? (
          <Textarea
            id={config.id}
            value={shouldShowValue ? String(config.value || '') : '••••••••'}
            onChange={(e) => updateConfigValue(sectionId, config.id, e.target.value)}
            placeholder={config.description}
            rows={3}
            className={error ? 'border-red-500' : ''}
          />
        ) : (
          <Input
            id={config.id}
            type={isPassword && !shouldShowValue ? 'password' : config.type === 'number' ? 'number' : 'text'}
            value={shouldShowValue ? String(config.value || '') : '••••••••'}
            onChange={(e) => updateConfigValue(sectionId, config.id, 
              config.type === 'number' ? Number(e.target.value) : e.target.value
            )}
            placeholder={config.description}
            className={error ? 'border-red-500' : ''}
            min={config.validation?.min}
            max={config.validation?.max}
          />
        )}
        
        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}
        
        <p className="text-xs text-gray-500">{config.description}</p>
      </div>
    );
  };

  const currentSection = getCurrentSection();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">系统配置</h1>
            <p className="text-gray-600 mt-1">管理系统参数 · 环境配置 · 安全设置</p>
          </div>
          <div className="flex items-center space-x-4">
            {/* 环境切换 */}
            <div className="flex items-center space-x-2">
              <Label className="text-sm">环境:</Label>
              <select
                value={currentEnvironment}
                onChange={(e) => setCurrentEnvironment(e.target.value as 'development' | 'staging' | 'production')}
                className="px-3 py-1 border rounded text-sm"
              >
                {Object.entries(environments).map(([key, env]) => (
                  <option key={key} value={key}>
                    {env.name}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="outline"
              onClick={resetConfiguration}
              disabled={isLoading}
              className="flex items-center space-x-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>重置</span>
            </Button>
            <Button
              onClick={saveConfiguration}
              disabled={isLoading || !hasChanges}
              className="flex items-center space-x-2"
            >
              <Save className="w-4 h-4" />
              <span>{isLoading ? '保存中...' : '保存配置'}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 环境状态提示 */}
      <div className="mb-6">
        <Alert className={`border-2 ${
          currentEnvironment === 'production' 
            ? 'border-red-200 bg-red-50' 
            : currentEnvironment === 'staging'
            ? 'border-yellow-200 bg-yellow-50'
            : 'border-blue-200 bg-blue-50'
        }`}>
          <AlertTriangle className={`h-4 w-4 ${
            currentEnvironment === 'production' 
              ? 'text-red-600' 
              : currentEnvironment === 'staging'
              ? 'text-yellow-600'
              : 'text-blue-600'
          }`} />
          <AlertDescription className={`${
            currentEnvironment === 'production' 
              ? 'text-red-800' 
              : currentEnvironment === 'staging'
              ? 'text-yellow-800'
              : 'text-blue-800'
          }`}>
            <strong>当前环境: {environments[currentEnvironment].name}</strong>
            {currentEnvironment === 'production' && ' - 请谨慎修改生产环境配置'}
            {currentEnvironment === 'staging' && ' - 测试环境配置'}
            {currentEnvironment === 'development' && ' - 开发环境配置'}
          </AlertDescription>
        </Alert>
      </div>

      {/* 未保存更改提示 */}
      {hasChanges && (
        <div className="mb-6">
          <Alert className="border-orange-200 bg-orange-50">
            <AlertTriangle className="h-4 w-4 text-orange-600" />
            <AlertDescription className="text-orange-800">
              <strong>有未保存的更改</strong> - 请记得保存您的配置更改
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* 标签页导航 */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {configSections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveTab(section.id as 'general' | 'security' | 'database' | 'messaging' | 'monitoring')}
                  className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === section.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{section.name}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* 配置内容 */}
      {currentSection && (
        <Card className="bg-white">
          <CardHeader>
            <div className="flex items-center space-x-3">
              <currentSection.icon className="w-6 h-6 text-blue-600" />
              <div>
                <CardTitle>{currentSection.name}</CardTitle>
                <p className="text-sm text-gray-600 mt-1">{currentSection.description}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {currentSection.configs.map((config) => (
                <div key={config.id} className="space-y-4">
                  {renderConfigInput(config, currentSection.id)}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 配置验证状态 */}
      <Card className="bg-white mt-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <span>配置验证</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3 p-3 bg-green-50 rounded">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div>
                <p className="font-medium text-green-800">数据库连接</p>
                <p className="text-sm text-green-600">连接正常</p>
              </div>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-green-50 rounded">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div>
                <p className="font-medium text-green-800">Redis缓存</p>
                <p className="text-sm text-green-600">连接正常</p>
              </div>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-yellow-50 rounded">
              <Clock className="w-5 h-5 text-yellow-600" />
              <div>
                <p className="font-medium text-yellow-800">ZeroMQ</p>
                <p className="text-sm text-yellow-600">检查中...</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 配置历史 */}
      <Card className="bg-white mt-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Clock className="w-5 h-5" />
            <span>最近配置更改</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 border rounded">
              <div>
                <p className="font-medium">更新数据库连接池大小</p>
                <p className="text-sm text-gray-500">从 10 修改为 20</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">管理员</p>
                <p className="text-xs text-gray-500">2024-01-15 14:30</p>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 border rounded">
              <div>
                <p className="font-medium">启用调试模式</p>
                <p className="text-sm text-gray-500">开发环境调试模式已启用</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">开发者</p>
                <p className="text-xs text-gray-500">2024-01-15 10:15</p>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 border rounded">
              <div>
                <p className="font-medium">更新API速率限制</p>
                <p className="text-sm text-gray-500">从 500 修改为 1000</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">管理员</p>
                <p className="text-xs text-gray-500">2024-01-14 16:45</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SystemConfiguration;