'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import {
  FileText,
  Download,
  Eye,
  Calendar,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  PieChart,
  Filter,
  Search,
} from 'lucide-react';
import { useRehearsalReports, useExportReport } from '@/hooks/useApi';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';

// 演习报告类型定义
interface RehearsalReport {
  id: string;
  title: string;
  type: 'scenario' | 'stress_test' | 'comprehensive';
  status: 'generating' | 'completed' | 'failed';
  createdAt: string;
  period: {
    start: string;
    end: string;
  };
  summary: {
    totalTests: number;
    passedTests: number;
    failedTests: number;
    averageScore: number;
    criticalIssues: number;
    recommendations: number;
  };
  details: {
    scenarios: Array<{
      name: string;
      result: 'pass' | 'fail' | 'warning';
      score: number;
      issues: string[];
    }>;
    stressTests: Array<{
      name: string;
      result: 'pass' | 'fail' | 'warning';
      metrics: Record<string, number>;
    }>;
    systemMetrics: {
      availability: number;
      performance: number;
      reliability: number;
      security: number;
    };
  };
  fileSize: string;
  downloadUrl?: string;
}

// 模拟报告数据
const mockReports: RehearsalReport[] = [
  {
    id: '1',
    title: '2024年1月风控演习综合报告',
    type: 'comprehensive',
    status: 'completed',
    createdAt: '2024-01-15T16:30:00Z',
    period: {
      start: '2024-01-01T00:00:00Z',
      end: '2024-01-15T23:59:59Z',
    },
    summary: {
      totalTests: 25,
      passedTests: 22,
      failedTests: 3,
      averageScore: 87.5,
      criticalIssues: 2,
      recommendations: 8,
    },
    details: {
      scenarios: [
        { name: '市场崩盘模拟', result: 'pass', score: 92, issues: [] },
        {
          name: '流动性危机',
          result: 'warning',
          score: 75,
          issues: ['响应时间过长'],
        },
        { name: '系统故障演练', result: 'pass', score: 88, issues: [] },
      ],
      stressTests: [
        {
          name: '高频交易压力测试',
          result: 'pass',
          metrics: { latency: 8.5, throughput: 1200 },
        },
        {
          name: '数据库负载测试',
          result: 'fail',
          metrics: { query_time: 150, connection_pool: 95 },
        },
      ],
      systemMetrics: {
        availability: 99.8,
        performance: 85.2,
        reliability: 92.1,
        security: 96.5,
      },
    },
    fileSize: '2.3 MB',
    downloadUrl: '/reports/comprehensive-2024-01.pdf',
  },
  {
    id: '2',
    title: '场景模拟专项报告',
    type: 'scenario',
    status: 'completed',
    createdAt: '2024-01-14T10:15:00Z',
    period: {
      start: '2024-01-10T00:00:00Z',
      end: '2024-01-14T23:59:59Z',
    },
    summary: {
      totalTests: 12,
      passedTests: 10,
      failedTests: 2,
      averageScore: 82.3,
      criticalIssues: 1,
      recommendations: 5,
    },
    details: {
      scenarios: [
        { name: '极端波动模拟', result: 'pass', score: 85, issues: [] },
        {
          name: '黑天鹅事件',
          result: 'fail',
          score: 45,
          issues: ['风控阈值设置不当', '应急响应延迟'],
        },
      ],
      stressTests: [],
      systemMetrics: {
        availability: 99.5,
        performance: 78.9,
        reliability: 88.7,
        security: 94.2,
      },
    },
    fileSize: '1.8 MB',
    downloadUrl: '/reports/scenario-2024-01-14.pdf',
  },
  {
    id: '3',
    title: '压力测试专项报告',
    type: 'stress_test',
    status: 'generating',
    createdAt: '2024-01-15T14:00:00Z',
    period: {
      start: '2024-01-15T00:00:00Z',
      end: '2024-01-15T23:59:59Z',
    },
    summary: {
      totalTests: 8,
      passedTests: 6,
      failedTests: 2,
      averageScore: 79.1,
      criticalIssues: 3,
      recommendations: 6,
    },
    details: {
      scenarios: [],
      stressTests: [
        {
          name: '网络带宽测试',
          result: 'fail',
          metrics: { bandwidth: 800, latency: 75 },
        },
        {
          name: '并发用户测试',
          result: 'pass',
          metrics: { concurrent_users: 500, response_time: 120 },
        },
      ],
      systemMetrics: {
        availability: 98.9,
        performance: 72.3,
        reliability: 85.6,
        security: 93.8,
      },
    },
    fileSize: '1.5 MB',
  },
];

// 报告类型配置
const reportTypes = {
  scenario: { label: '场景模拟', color: 'bg-blue-100 text-blue-800' },
  stress_test: { label: '压力测试', color: 'bg-green-100 text-green-800' },
  comprehensive: { label: '综合报告', color: 'bg-purple-100 text-purple-800' },
};

// 状态配置
const statusConfig = {
  generating: { label: '生成中', color: 'bg-yellow-100 text-yellow-800' },
  completed: { label: '已完成', color: 'bg-green-100 text-green-800' },
  failed: { label: '失败', color: 'bg-red-100 text-red-800' },
};

// 结果配置
const resultConfig = {
  pass: { label: '通过', color: 'text-green-600', icon: CheckCircle },
  fail: { label: '失败', color: 'text-red-600', icon: AlertTriangle },
  warning: { label: '警告', color: 'text-yellow-600', icon: AlertTriangle },
};

// 图表颜色
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export default function RehearsalReports() {
  const [selectedReport, setSelectedReport] = useState<RehearsalReport | null>(
    null
  );
  const [filterType, setFilterType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);

  // API hooks
  const { data: reportsResponse, isLoading } = useRehearsalReports();
  const exportReport = useExportReport();

  // 使用模拟数据
  const reportData = reportsResponse?.data || mockReports;

  // 过滤报告
  const filteredReports = reportData.filter((report) => {
    const matchesType = filterType === 'all' || report.type === filterType;
    const matchesSearch = report.title
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    return matchesType && matchesSearch;
  });

  // 导出报告
  const handleExportReport = async (
    reportId: string,
    format: 'pdf' | 'excel'
  ) => {
    try {
      await exportReport.mutateAsync({ reportId, format });
    } catch (error) {
      console.error('导出报告失败:', error);
    }
  };

  // 查看报告详情
  const handleViewReport = (report: RehearsalReport) => {
    setSelectedReport(report);
    setIsDetailDialogOpen(true);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部操作区 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">演习报告</h3>
          <p className="text-sm text-muted-foreground">
            查看和下载风控演习的详细报告和分析结果
          </p>
        </div>
        <Button>
          <FileText className="mr-2 h-4 w-4" />
          生成报告
        </Button>
      </div>

      {/* 筛选和搜索 */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              {Object.entries(reportTypes).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  {config.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center space-x-2 flex-1 max-w-md">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索报告..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* 报告列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredReports.map((report) => {
          const typeConfig = reportTypes[report.type];
          const statusConf = statusConfig[report.status];

          return (
            <Card key={report.id} className="relative">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                    <CardTitle className="text-base line-clamp-2">
                      {report.title}
                    </CardTitle>
                  </div>
                  <div className="flex flex-col space-y-1">
                    <Badge className={typeConfig.color}>
                      {typeConfig.label}
                    </Badge>
                    <Badge variant="outline" className={statusConf.color}>
                      {statusConf.label}
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>
                    {new Date(report.createdAt).toLocaleDateString('zh-CN')}
                  </span>
                  <span>•</span>
                  <span>{report.fileSize}</span>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* 报告摘要 */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">总测试:</span>
                    <span className="font-medium">
                      {report.summary.totalTests}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">通过率:</span>
                    <span className="font-medium">
                      {Math.round(
                        (report.summary.passedTests /
                          report.summary.totalTests) *
                          100
                      )}
                      %
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">平均分:</span>
                    <span className="font-medium">
                      {report.summary.averageScore}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">严重问题:</span>
                    <span className="font-medium text-red-600">
                      {report.summary.criticalIssues}
                    </span>
                  </div>
                </div>

                {/* 系统指标概览 */}
                {report.details.systemMetrics && (
                  <div className="space-y-2">
                    <span className="text-sm font-medium">系统指标</span>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="flex justify-between">
                        <span>可用性:</span>
                        <span>
                          {report.details.systemMetrics.availability}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>性能:</span>
                        <span>{report.details.systemMetrics.performance}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>可靠性:</span>
                        <span>{report.details.systemMetrics.reliability}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>安全性:</span>
                        <span>{report.details.systemMetrics.security}%</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="flex space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleViewReport(report)}
                    disabled={report.status === 'generating'}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    查看
                  </Button>

                  {report.status === 'completed' && (
                    <Button
                      size="sm"
                      onClick={() => handleExportReport(report.id, 'pdf')}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      下载
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* 报告详情对话框 */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedReport?.title}</DialogTitle>
          </DialogHeader>

          {selectedReport && <ReportDetailView report={selectedReport} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// 报告详情视图组件
function ReportDetailView({ report }: { report: RehearsalReport }) {
  // 准备图表数据
  const systemMetricsData = Object.entries(report.details.systemMetrics).map(
    ([key, value]) => ({
      name:
        key === 'availability'
          ? '可用性'
          : key === 'performance'
            ? '性能'
            : key === 'reliability'
              ? '可靠性'
              : '安全性',
      value,
    })
  );

  const testResultsData = [
    { name: '通过', value: report.summary.passedTests, color: '#00C49F' },
    { name: '失败', value: report.summary.failedTests, color: '#FF8042' },
  ];

  return (
    <div className="space-y-6">
      {/* 报告概览 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-muted-foreground">总测试数</p>
                <p className="text-2xl font-bold">
                  {report.summary.totalTests}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-muted-foreground">通过率</p>
                <p className="text-2xl font-bold">
                  {Math.round(
                    (report.summary.passedTests / report.summary.totalTests) *
                      100
                  )}
                  %
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingDown className="h-5 w-5 text-orange-600" />
              <div>
                <p className="text-sm text-muted-foreground">平均分</p>
                <p className="text-2xl font-bold">
                  {report.summary.averageScore}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-sm text-muted-foreground">严重问题</p>
                <p className="text-2xl font-bold">
                  {report.summary.criticalIssues}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 图表分析 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>系统指标分析</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={systemMetricsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>测试结果分布</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsPieChart>
                <Pie
                  data={testResultsData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {testResultsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 详细结果 */}
      <Tabs defaultValue="scenarios" className="space-y-4">
        <TabsList>
          <TabsTrigger value="scenarios">场景测试</TabsTrigger>
          <TabsTrigger value="stress">压力测试</TabsTrigger>
          <TabsTrigger value="recommendations">建议</TabsTrigger>
        </TabsList>

        <TabsContent value="scenarios" className="space-y-4">
          {report.details.scenarios.map((scenario, index) => {
            const resultConf = resultConfig[scenario.result];
            const ResultIcon = resultConf.icon;

            return (
              <Card key={index}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <ResultIcon className={`h-5 w-5 ${resultConf.color}`} />
                      <div>
                        <h4 className="font-medium">{scenario.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          评分: {scenario.score}/100
                        </p>
                      </div>
                    </div>
                    <Badge className={resultConf.color}>
                      {resultConf.label}
                    </Badge>
                  </div>

                  {scenario.issues.length > 0 && (
                    <div className="mt-3 space-y-1">
                      <p className="text-sm font-medium">发现问题:</p>
                      {scenario.issues.map((issue, i) => (
                        <p key={i} className="text-sm text-muted-foreground">
                          • {issue}
                        </p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>

        <TabsContent value="stress" className="space-y-4">
          {report.details.stressTests.map((test, index) => {
            const resultConf = resultConfig[test.result];
            const ResultIcon = resultConf.icon;

            return (
              <Card key={index}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <ResultIcon className={`h-5 w-5 ${resultConf.color}`} />
                      <div>
                        <h4 className="font-medium">{test.name}</h4>
                        <div className="flex space-x-4 text-sm text-muted-foreground">
                          {Object.entries(test.metrics).map(([key, value]) => (
                            <span key={key}>
                              {key}: {value}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <Badge className={resultConf.color}>
                      {resultConf.label}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-4">
          <Card>
            <CardContent className="p-4">
              <h4 className="font-medium mb-3">改进建议</h4>
              <div className="space-y-2">
                <p className="text-sm">
                  • 优化风控阈值设置，提高异常检测准确性
                </p>
                <p className="text-sm">• 加强系统监控，缩短故障响应时间</p>
                <p className="text-sm">• 增加备用系统容量，提高系统可用性</p>
                <p className="text-sm">• 完善应急预案，提高危机处理效率</p>
                <p className="text-sm">• 定期进行压力测试，确保系统稳定性</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
