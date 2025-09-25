'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  CheckCircle, 
  X,
  Eye,
  EyeOff,
  Filter,
  Bell,
  BellOff
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useRiskAlertsWebSocket } from '@/hooks/useWebSocket';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface RiskAlert {
  id: string;
  type: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  source: string;
  timestamp: number;
  acknowledged: boolean;
  resolved: boolean;
  severity: number; // 1-10
  category: 'market' | 'system' | 'strategy' | 'position' | 'liquidity';
}

interface AlertItemProps {
  alert: RiskAlert;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
  onDismiss: (id: string) => void;
}

const AlertItem = ({ alert, onAcknowledge, onResolve, onDismiss }: AlertItemProps) => {
  const getAlertConfig = () => {
    switch (alert.type) {
      case 'critical':
        return {
          icon: <AlertTriangle className="h-4 w-4" />,
          badge: <Badge variant="destructive">严重</Badge>,
          color: 'border-red-500 bg-red-50',
          iconColor: 'text-red-600'
        };
      case 'warning':
        return {
          icon: <AlertCircle className="h-4 w-4" />,
          badge: <Badge className="bg-yellow-500 hover:bg-yellow-600">警告</Badge>,
          color: 'border-yellow-500 bg-yellow-50',
          iconColor: 'text-yellow-600'
        };
      case 'info':
        return {
          icon: <Info className="h-4 w-4" />,
          badge: <Badge variant="outline">信息</Badge>,
          color: 'border-blue-500 bg-blue-50',
          iconColor: 'text-blue-600'
        };
    }
  };

  const getCategoryBadge = () => {
    const categoryMap = {
      market: '市场',
      system: '系统',
      strategy: '策略',
      position: '持仓',
      liquidity: '流动性'
    };
    return categoryMap[alert.category] || alert.category;
  };

  const config = getAlertConfig();
  const isActive = !alert.acknowledged && !alert.resolved;

  return (
    <div data-testid={`risk-alert-item-${alert.id}`} className={`p-3 border rounded-lg ${config.color} ${isActive ? 'shadow-sm' : 'opacity-60'}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className={config.iconColor}>
            {config.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <h4 className="font-medium text-sm truncate">{alert.title}</h4>
              {config.badge}
              <Badge variant="secondary" className="text-xs">
                {getCategoryBadge()}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-2">{alert.message}</p>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>来源: {alert.source}</span>
              <span>{new Date(alert.timestamp).toLocaleString()}</span>
            </div>
            <div className="flex items-center space-x-1 mt-1">
              <span className="text-xs text-muted-foreground">严重程度:</span>
              <div className="flex space-x-1">
                {Array.from({ length: 10 }, (_, i) => (
                  <div
                    key={i}
                    className={`w-2 h-2 rounded-full ${
                      i < alert.severity 
                        ? alert.severity <= 3 
                          ? 'bg-green-500' 
                          : alert.severity <= 6 
                          ? 'bg-yellow-500' 
                          : 'bg-red-500'
                        : 'bg-gray-200'
                    }`}
                  />
                ))}
              </div>
              <span className="text-xs font-medium">{alert.severity}/10</span>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col space-y-1 ml-2">
          {!alert.acknowledged && !alert.resolved && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onAcknowledge(alert.id)}
              className="h-7 px-2"
              data-testid={`btn-ack-${alert.id}`}
            >
              <Eye className="h-3 w-3" />
            </Button>
          )}
          
          {alert.acknowledged && !alert.resolved && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onResolve(alert.id)}
              className="h-7 px-2"
              data-testid={`btn-resolve-${alert.id}`}
            >
              <CheckCircle className="h-3 w-3" />
            </Button>
          )}
          
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onDismiss(alert.id)}
            className="h-7 px-2"
            data-testid={`btn-dismiss-${alert.id}`}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </div>
      
      {alert.acknowledged && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="flex items-center space-x-2">
            <CheckCircle className="h-3 w-3 text-green-600" />
            <span className="text-xs text-green-600">已确认</span>
            {alert.resolved && (
              <>
                <span className="text-xs text-muted-foreground">•</span>
                <span className="text-xs text-green-600">已解决</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const RiskAlerts = () => {
  const [alerts, setAlerts] = useState<RiskAlert[]>([
    {
      id: '1',
      type: 'critical',
      title: '持仓风险过高',
      message: 'BTC持仓超过风险阈值，当前风险敞口达到85%',
      source: 'Trade Guard',
      timestamp: Date.now() - 300000,
      acknowledged: false,
      resolved: false,
      severity: 9,
      category: 'position'
    },
    {
      id: '2',
      type: 'warning',
      title: '市场波动异常',
      message: 'ETH价格波动率超过预期，建议调整策略参数',
      source: 'Scan Pulse',
      timestamp: Date.now() - 600000,
      acknowledged: true,
      resolved: false,
      severity: 6,
      category: 'market'
    },
    {
      id: '3',
      type: 'info',
      title: '策略性能提醒',
      message: '趋势跟踪策略A连续3天收益为负，建议检查参数',
      source: 'Opti Core',
      timestamp: Date.now() - 900000,
      acknowledged: true,
      resolved: true,
      severity: 4,
      category: 'strategy'
    }
  ]);

  const [filter, setFilter] = useState<'all' | 'active' | 'critical' | 'warning' | 'info'>('all');
  const [soundEnabled, setSoundEnabled] = useState(true);
  
  const { lastMessage } = useRiskAlertsWebSocket();

  // 处理WebSocket消息
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'risk_alert') {
      const alertData = lastMessage.data as Partial<RiskAlert>;
      const newAlert: RiskAlert = {
        id: Date.now().toString(),
        type: alertData.type || 'info',
        title: alertData.title || '未知警报',
        message: alertData.message || '',
        source: alertData.source || '系统',
        severity: alertData.severity || 1,
        category: alertData.category || 'system',
        timestamp: Date.now(),
        acknowledged: false,
        resolved: false
      };
      
      setAlerts(prev => [newAlert, ...prev]);
      
      // 播放警报声音
      if (soundEnabled && newAlert.type === 'critical') {
        // 这里可以添加音频播放逻辑
        console.log('🚨 Critical alert sound');
      }
    }
  }, [lastMessage, soundEnabled]);

  const handleAcknowledge = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ));
  };

  const handleResolve = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, resolved: true } : alert
    ));
  };

  const handleDismiss = (alertId: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  const filteredAlerts = alerts.filter(alert => {
    switch (filter) {
      case 'active':
        return !alert.acknowledged && !alert.resolved;
      case 'critical':
        return alert.type === 'critical';
      case 'warning':
        return alert.type === 'warning';
      case 'info':
        return alert.type === 'info';
      default:
        return true;
    }
  });

  const activeAlerts = alerts.filter(alert => !alert.acknowledged && !alert.resolved);
  const criticalCount = activeAlerts.filter(alert => alert.type === 'critical').length;
  const warningCount = activeAlerts.filter(alert => alert.type === 'warning').length;

  return (
    <Card data-testid="risk-alerts-root">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span>风险警报</span>
            {activeAlerts.length > 0 && (
              <Badge variant="destructive" className="animate-pulse">
                {activeAlerts.length} 活跃
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="h-8 px-2"
              data-testid="btn-sound-toggle"
            >
              {soundEnabled ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
            </Button>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="outline" className="h-8 px-2" data-testid="btn-filter">
                  <Filter className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" data-testid="menu-filter">
                <DropdownMenuLabel>筛选警报</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setFilter('all')} data-testid="filter-all">
                  全部 ({alerts.length})
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilter('active')} data-testid="filter-active">
                  活跃 ({activeAlerts.length})
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setFilter('critical')} data-testid="filter-critical">
                  严重 ({criticalCount})
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilter('warning')} data-testid="filter-warning">
                  警告 ({warningCount})
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilter('info')} data-testid="filter-info">
                  信息
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground" data-testid="empty-risk-alerts">
            <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p>暂无{filter === 'all' ? '' : filter === 'active' ? '活跃' : filter}警报</p>
          </div>
        ) : (
          <ScrollArea className="h-96" data-testid="risk-alerts-scroll">
            <div className="space-y-3">
              {filteredAlerts.map((alert) => (
                <AlertItem
                  key={alert.id}
                  alert={alert}
                  onAcknowledge={handleAcknowledge}
                  onResolve={handleResolve}
                  onDismiss={handleDismiss}
                />
              ))}
            </div>
          </ScrollArea>
        )}
        
        {activeAlerts.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">批量操作</span>
              <div className="space-x-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    activeAlerts.forEach(alert => handleAcknowledge(alert.id));
                  }}
                  data-testid="btn-ack-all"
                >
                  全部确认
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    alerts.filter(alert => alert.acknowledged && !alert.resolved)
                      .forEach(alert => handleResolve(alert.id));
                  }}
                  data-testid="btn-resolve-all"
                >
                  全部解决
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};