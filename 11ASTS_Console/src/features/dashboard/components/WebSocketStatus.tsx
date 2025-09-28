'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  useMarketDataWebSocket, 
  useSystemStatusWebSocket, 
  useTradingEventsWebSocket, 
  useRiskAlertsWebSocket,
  WebSocketMessage
} from '@/hooks/useWebSocket';
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react';
import { useState } from 'react';

interface ConnectionStatusProps {
  name: string;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  onReconnect: () => void;
  lastMessage?: WebSocketMessage;
}

const ConnectionStatus = ({ name, connectionState, onReconnect, lastMessage }: ConnectionStatusProps) => {
  const getStatusConfig = () => {
    switch (connectionState) {
      case 'connected':
        return {
          icon: <Wifi className="h-4 w-4" />,
          badge: <Badge className="bg-green-500 hover:bg-green-600">已连接</Badge>,
          color: 'text-green-600'
        };
      case 'connecting':
        return {
          icon: <RefreshCw className="h-4 w-4 animate-spin" />,
          badge: <Badge variant="outline">连接中</Badge>,
          color: 'text-yellow-600'
        };
      case 'error':
        return {
          icon: <AlertCircle className="h-4 w-4" />,
          badge: <Badge variant="destructive">错误</Badge>,
          color: 'text-red-600'
        };
      default:
        return {
          icon: <WifiOff className="h-4 w-4" />,
          badge: <Badge variant="secondary">未连接</Badge>,
          color: 'text-gray-600'
        };
    }
  };

  const status = getStatusConfig();

  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div className="flex items-center space-x-3">
        <div className={status.color}>
          {status.icon}
        </div>
        <div>
          <p className="font-medium text-sm">{name}</p>
          <p className="text-xs text-muted-foreground">
            {lastMessage ? `最后更新: ${new Date(lastMessage.timestamp).toLocaleTimeString()}` : '无数据'}
          </p>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        {status.badge}
        {connectionState !== 'connected' && (
          <Button
            size="sm"
            variant="outline"
            onClick={onReconnect}
            className="h-8 px-2"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  );
};

export const WebSocketStatus = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const marketData = useMarketDataWebSocket();
  const systemStatus = useSystemStatusWebSocket();
  const tradingEvents = useTradingEventsWebSocket();
  const riskAlerts = useRiskAlertsWebSocket();

  const connections = [
    { name: '市场数据', ...marketData },
    { name: '系统状态', ...systemStatus },
    { name: '交易事件', ...tradingEvents },
    { name: '风险警报', ...riskAlerts }
  ];

  const connectedCount = connections.filter(conn => conn.connectionState === 'connected').length;
  const totalCount = connections.length;

  const getOverallStatus = () => {
    if (connectedCount === totalCount) {
      return { text: '全部连接', variant: 'default' as const, color: 'bg-green-500' };
    } else if (connectedCount > 0) {
      return { text: '部分连接', variant: 'outline' as const, color: 'bg-yellow-500' };
    } else {
      return { text: '连接断开', variant: 'destructive' as const, color: 'bg-red-500' };
    }
  };

  const overallStatus = getOverallStatus();

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span>实时连接状态</span>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${overallStatus.color} animate-pulse`}></div>
            <Badge variant={overallStatus.variant}>
              {connectedCount}/{totalCount} {overallStatus.text}
            </Badge>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 px-2"
            >
              {isExpanded ? '收起' : '展开'}
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0">
          <div className="space-y-3">
            {connections.map((connection, index) => (
              <ConnectionStatus
                key={index}
                name={connection.name}
                connectionState={connection.connectionState}
                onReconnect={connection.connect}
                lastMessage={connection.lastMessage}
              />
            ))}
            <div className="mt-4 pt-3 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">批量操作</span>
                <div className="space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      connections.forEach(conn => {
                        if (conn.connectionState !== 'connected') {
                          conn.connect();
                        }
                      });
                    }}
                  >
                    全部重连
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      connections.forEach(conn => conn.disconnect());
                    }}
                  >
                    全部断开
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
};