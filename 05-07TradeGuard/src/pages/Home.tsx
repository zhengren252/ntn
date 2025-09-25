import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Activity, Shield, DollarSign, Settings, BarChart3, Users, Monitor, Cog } from 'lucide-react';

const Home: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      {/* 页面标题 */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          TradeGuard 交易执行铁三角
        </h1>
        <p className="text-lg text-gray-600">
          智能交易系统 · 风险管控 · 资金管理
        </p>
        <Badge variant="secondary" className="mt-2">
          系统版本 v1.0.0
        </Badge>
      </div>

      {/* 系统概览 */}
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* 交易员模组 */}
          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center space-x-2">
                <Activity className="w-6 h-6 text-blue-600" />
                <span>交易员模组</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                策略包管理、订单执行、实时监控
              </p>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">活跃策略</span>
                  <span className="font-medium">8</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">今日订单</span>
                  <span className="font-medium">156</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">成功率</span>
                  <span className="font-medium text-green-600">94.2%</span>
                </div>
              </div>
              <Link to="/trader">
                <Button className="w-full mt-4" variant="outline">
                  进入工作台
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* 风控模组 */}
          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center space-x-2">
                <Shield className="w-6 h-6 text-red-600" />
                <span>风控模组</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                风险评估、实时监控、警报管理
              </p>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">风险评分</span>
                  <span className="font-medium text-yellow-600">中等</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">活跃警报</span>
                  <span className="font-medium">3</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">VaR值</span>
                  <span className="font-medium">$125,000</span>
                </div>
              </div>
              <Link to="/risk">
                <Button className="w-full mt-4" variant="outline">
                  风控管理
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* 财务模组 */}
          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center space-x-2">
                <DollarSign className="w-6 h-6 text-green-600" />
                <span>财务模组</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                预算审批、账户管理、资金分配
              </p>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">总资产</span>
                  <span className="font-medium">$2.5M</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">可用资金</span>
                  <span className="font-medium">$850K</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">待审批</span>
                  <span className="font-medium text-orange-600">5</span>
                </div>
              </div>
              <Link to="/finance">
                <Button className="w-full mt-4" variant="outline">
                  财务管理
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* 系统状态 */}
        <Card className="bg-white shadow-lg mb-8">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="w-6 h-6 text-purple-600" />
              <span>系统状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">99.9%</div>
                <div className="text-sm text-gray-500">系统可用性</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">45ms</div>
                <div className="text-sm text-gray-500">平均响应时间</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">1,247</div>
                <div className="text-sm text-gray-500">今日交易量</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">12</div>
                <div className="text-sm text-gray-500">在线用户</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 快速操作 */}
        <Card className="bg-white shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="w-6 h-6 text-gray-600" />
              <span>快速操作</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Link to="/master">
                <Button variant="outline" className="h-16 w-full flex flex-col items-center space-y-1">
                  <Monitor className="w-5 h-5" />
                  <span className="text-sm">总控台</span>
                </Button>
              </Link>
              <Link to="/dashboard">
                <Button variant="outline" className="h-16 w-full flex flex-col items-center space-y-1">
                  <BarChart3 className="w-5 h-5" />
                  <span className="text-sm">监控仪表板</span>
                </Button>
              </Link>
              <Link to="/config">
                <Button variant="outline" className="h-16 w-full flex flex-col items-center space-y-1">
                  <Cog className="w-5 h-5" />
                  <span className="text-sm">系统配置</span>
                </Button>
              </Link>
              <Button variant="outline" className="h-16 flex flex-col items-center space-y-1">
                <Users className="w-5 h-5" />
                <span className="text-sm">用户管理</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Home;