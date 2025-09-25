'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useDashboardChart } from '@/hooks/useApi'
import ReactECharts from 'echarts-for-react'
import { EChartsOption } from 'echarts'

// 定义CallbackDataParams类型
interface CallbackDataParams {
  axisValue?: string
  value?: number | string
  seriesName?: string
  dataIndex?: number
  color?: string
}

type TimeRange = '1h' | '4h' | '1d' | '1w' | '1m'

const timeRangeOptions = [
  { value: '1h', label: '1小时' },
  { value: '4h', label: '4小时' },
  { value: '1d', label: '1天' },
  { value: '1w', label: '1周' },
  { value: '1m', label: '1月' }
]

export const TradingChart = () => {
  const [timeRange, setTimeRange] = useState<TimeRange>('1d')
  const { data: chartData, isLoading, error } = useDashboardChart(timeRange)

  const getChartOption = (): EChartsOption => {
    if (!chartData?.data) {
      return {
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center'
        }
      }
    }

    const data = chartData.data

    return {
      title: {
        text: '实时交易概览',
        left: 'left'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: (params: any) => {
          if (Array.isArray(params) && params.length > 0) {
            const data = params[0]
            return `
              <div>
                <div>时间: ${data.axisValue}</div>
                <div>盈亏: ¥${typeof data.value === 'number' ? data.value.toLocaleString() : data.value}</div>
              </div>
            `
          }
          return ''
        }
      },
      legend: {
        data: ['累计盈亏', '单日盈亏'],
        top: 30
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.timestamps || []
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => `¥${value.toLocaleString()}`
        }
      },
      series: [
        {
          name: '累计盈亏',
          type: 'line',
          smooth: true,
          data: data.cumulativeProfit || [],
          itemStyle: {
            color: '#10b981'
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                {
                  offset: 0,
                  color: 'rgba(16, 185, 129, 0.3)'
                },
                {
                  offset: 1,
                  color: 'rgba(16, 185, 129, 0.05)'
                }
              ]
            }
          }
        },
        {
          name: '单日盈亏',
          type: 'bar',
          data: data.dailyProfit || [],
          itemStyle: {
            color: (params: any) => {
              const value = typeof params.value === 'number' ? params.value : 0
              return value >= 0 ? '#10b981' : '#ef4444'
            }
          }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          start: 70,
          end: 100
        },
        {
          start: 70,
          end: 100,
          height: 20,
          bottom: 10
        }
      ]
    }
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>实时交易概览</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-red-600">
            图表数据加载失败
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>实时交易概览</CardTitle>
          <div className="flex space-x-2">
            {timeRangeOptions.map((option) => (
              <Button
                key={option.value}
                variant={timeRange === option.value ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTimeRange(option.value as TimeRange)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          </div>
        ) : (
          <ReactECharts
            option={getChartOption()}
            style={{ height: '400px', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        )}
      </CardContent>
    </Card>
  )
}