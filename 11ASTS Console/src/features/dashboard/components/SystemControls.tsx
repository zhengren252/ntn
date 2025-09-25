'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useSystemStore } from '@/store';
import { Play, Pause, Square, AlertTriangle } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

export const SystemControls = () => {
  const {
    isSystemRunning,
    emergencyStop,
    setSystemRunning,
    triggerEmergencyStop,
  } = useSystemStore();

  const [isLoading, setIsLoading] = useState(false);

  const handleStartSystem = async () => {
    setIsLoading(true);
    try {
      // 这里应该调用API启动系统
      await new Promise((resolve) => setTimeout(resolve, 1000)); // 模拟API调用
      setSystemRunning(true);
    } catch (error) {
      console.error('启动系统失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopSystem = async () => {
    setIsLoading(true);
    try {
      // 这里应该调用API停止系统
      await new Promise((resolve) => setTimeout(resolve, 1000)); // 模拟API调用
      setSystemRunning(false);
    } catch (error) {
      console.error('停止系统失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergencyStop = async () => {
    setIsLoading(true);
    try {
      // 这里应该调用API执行紧急停止
      await new Promise((resolve) => setTimeout(resolve, 500)); // 模拟API调用
      triggerEmergencyStop();
    } catch (error) {
      console.error('紧急停止失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getSystemStatus = () => {
    if (emergencyStop) {
      return {
        text: '紧急停止',
        variant: 'destructive' as const,
        color: 'bg-red-500',
      };
    }
    if (isSystemRunning) {
      return {
        text: '运行中',
        variant: 'default' as const,
        color: 'bg-green-500',
      };
    }
    return {
      text: '已停止',
      variant: 'secondary' as const,
      color: 'bg-gray-500',
    };
  };

  const status = getSystemStatus();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>系统控制</span>
          <div className="flex items-center space-x-2">
            <div
              className={`w-3 h-3 rounded-full ${status.color} animate-pulse`}
            ></div>
            <Badge variant={status.variant}>{status.text}</Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex space-x-3">
          {!isSystemRunning && !emergencyStop && (
            <Button
              onClick={handleStartSystem}
              disabled={isLoading}
              className="flex items-center space-x-2"
            >
              <Play className="h-4 w-4" />
              <span>启动系统</span>
            </Button>
          )}

          {isSystemRunning && !emergencyStop && (
            <Button
              variant="outline"
              onClick={handleStopSystem}
              disabled={isLoading}
              className="flex items-center space-x-2"
            >
              <Pause className="h-4 w-4" />
              <span>停止系统</span>
            </Button>
          )}

          {(isSystemRunning || emergencyStop) && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="destructive"
                  disabled={isLoading}
                  className="flex items-center space-x-2"
                >
                  <AlertTriangle className="h-4 w-4" />
                  <span>紧急停止</span>
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>确认紧急停止</AlertDialogTitle>
                  <AlertDialogDescription>
                    紧急停止将立即终止所有交易活动和系统进程。此操作不可撤销，请确认是否继续？
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleEmergencyStop}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    确认停止
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}

          {emergencyStop && (
            <Button
              onClick={() => {
                // 重置紧急停止状态
                useSystemStore.setState({ emergencyStop: false });
              }}
              disabled={isLoading}
              className="flex items-center space-x-2"
            >
              <Square className="h-4 w-4" />
              <span>重置系统</span>
            </Button>
          )}
        </div>

        {isLoading && (
          <div className="mt-3 text-sm text-gray-600 flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
            <span>操作执行中...</span>
          </div>
        )}

        <div className="mt-4 text-xs text-gray-500">
          <p>• 启动系统：开始所有交易策略和监控服务</p>
          <p>• 停止系统：安全停止所有交易活动</p>
          <p>• 紧急停止：立即终止所有操作，用于紧急情况</p>
        </div>
      </CardContent>
    </Card>
  );
};
