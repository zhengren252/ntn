'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Upload,
  Download,
  FileText,
  Package,
  CheckCircle,
  AlertTriangle,
  X,
  Plus,
  ExternalLink
} from 'lucide-react'
import { useImportModule, useExportModule, useModuleTemplates } from '@/hooks/useApi'

interface Template {
  id: string
  name: string
  category: string
}

interface ModuleImportExportProps {
  isOpen: boolean
  onClose: () => void
  onModuleImported: (module: unknown) => void
}

export default function ModuleImportExport({ isOpen, onClose, onModuleImported }: ModuleImportExportProps) {
  const [activeTab, setActiveTab] = useState('import')
  const [importMethod, setImportMethod] = useState('file')
  const [exportFormat, setExportFormat] = useState('json')
  const [selectedModules, setSelectedModules] = useState<string[]>([])
  const [importData, setImportData] = useState({
    file: null as File | null,
    url: '',
    json: '',
    template: ''
  })
  const [exportOptions, setExportOptions] = useState({
    includeConfig: true,
    includeDependencies: true,
    includeData: false,
    compression: false
  })

  const { data: templates, isLoading: templatesLoading } = useModuleTemplates()
  const importModule = useImportModule()
  const exportModule = useExportModule()

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setImportData(prev => ({ ...prev, file }))
    }
  }

  const handleImport = () => {
    const data = {
      method: importMethod,
      ...importData
    }
    importModule.mutate(data, {
      onSuccess: (result) => {
        onModuleImported?.(result)
        onClose()
      }
    })
  }

  const handleExport = () => {
    // 如果选择了多个模块，需要逐个导出
    if (selectedModules.length > 0) {
      selectedModules.forEach(moduleId => {
        const data = {
          moduleId,
          format: exportFormat as 'zip' | 'tar',
          includeConfig: exportOptions.includeConfig,
          includeDependencies: exportOptions.includeDependencies
        }
        exportModule.mutate(data)
      })
    }
  }

  const getImportMethodIcon = (method: string) => {
    switch (method) {
      case 'file':
        return <Upload className="h-4 w-4" />
      case 'url':
        return <ExternalLink className="h-4 w-4" />
      case 'json':
        return <FileText className="h-4 w-4" />
      case 'template':
        return <Package className="h-4 w-4" />
      default:
        return <Upload className="h-4 w-4" />
    }
  }

  const mockModules = [
    { id: '1', name: '趋势跟踪策略', version: '1.0.0', size: '2.3MB' },
    { id: '2', name: '风险控制模块', version: '2.1.0', size: '1.8MB' },
    { id: '3', name: '数据分析工具', version: '1.5.2', size: '3.1MB' }
  ]

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Package className="h-5 w-5" />
            <span>模块导入导出</span>
          </DialogTitle>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="import" className="flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>导入模块</span>
            </TabsTrigger>
            <TabsTrigger value="export" className="flex items-center space-x-2">
              <Download className="h-4 w-4" />
              <span>导出模块</span>
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="import" className="space-y-6">
            {/* 导入方式选择 */}
            <Card>
              <CardHeader>
                <CardTitle>选择导入方式</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {[
                    { value: 'file', label: '本地文件', desc: '上传模块文件' },
                    { value: 'url', label: '远程URL', desc: '从URL导入' },
                    { value: 'json', label: 'JSON配置', desc: '粘贴配置代码' },
                    { value: 'template', label: '模板库', desc: '选择预设模板' }
                  ].map((method) => (
                    <Card 
                      key={method.value}
                      className={`cursor-pointer transition-colors ${
                        importMethod === method.value ? 'ring-2 ring-primary' : 'hover:bg-muted/50'
                      }`}
                      onClick={() => setImportMethod(method.value)}
                    >
                      <CardContent className="p-4 text-center">
                        <div className="flex justify-center mb-2">
                          {getImportMethodIcon(method.value)}
                        </div>
                        <h4 className="font-medium">{method.label}</h4>
                        <p className="text-sm text-muted-foreground">{method.desc}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 导入配置 */}
            <Card>
              <CardHeader>
                <CardTitle>导入配置</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {importMethod === 'file' && (
                  <div>
                    <label className="text-sm font-medium">选择文件</label>
                    <Input
                      type="file"
                      accept=".json,.zip,.tar.gz"
                      onChange={handleFileSelect}
                      className="mt-1"
                    />
                    {importData.file && (
                      <div className="mt-2 p-2 bg-muted rounded flex items-center justify-between">
                        <span className="text-sm">{importData.file.name}</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setImportData(prev => ({ ...prev, file: null }))}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                )}
                
                {importMethod === 'url' && (
                  <div>
                    <label className="text-sm font-medium">模块URL</label>
                    <Input
                      value={importData.url}
                      onChange={(e) => setImportData(prev => ({ ...prev, url: e.target.value }))}
                      placeholder="https://example.com/module.json"
                      className="mt-1"
                    />
                  </div>
                )}
                
                {importMethod === 'json' && (
                  <div>
                    <label className="text-sm font-medium">JSON配置</label>
                    <Textarea
                      value={importData.json}
                      onChange={(e) => setImportData(prev => ({ ...prev, json: e.target.value }))}
                      placeholder="粘贴模块JSON配置..."
                      rows={8}
                      className="mt-1 font-mono text-sm"
                    />
                  </div>
                )}
                
                {importMethod === 'template' && (
                  <div>
                    <label className="text-sm font-medium">选择模板</label>
                    {templatesLoading ? (
                      <Skeleton className="h-10 w-full mt-1" />
                    ) : (
                      <Select
                        value={importData.template}
                        onValueChange={(value) => setImportData(prev => ({ ...prev, template: value }))}
                      >
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="选择模板" />
                        </SelectTrigger>
                        <SelectContent>
                          {templates?.data?.map((template: Template) => (
                            <SelectItem key={template.id} value={template.id}>
                              <div className="flex items-center space-x-2">
                                <span>{template.name}</span>
                                <Badge variant="outline">{template.category}</Badge>
                              </div>
                            </SelectItem>
                          )) || []}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 导入进度 */}
            {importModule.isPending && (
              <Card>
                <CardHeader>
                  <CardTitle>导入进度</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Progress value={65} className="w-full" />
                    <p className="text-sm text-muted-foreground">正在解析模块配置...</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={onClose}>
                取消
              </Button>
              <Button 
                onClick={handleImport}
                disabled={importModule.isPending || (
                  importMethod === 'file' && !importData.file ||
                  importMethod === 'url' && !importData.url ||
                  importMethod === 'json' && !importData.json ||
                  importMethod === 'template' && !importData.template
                )}
              >
                {importModule.isPending ? '导入中...' : '开始导入'}
              </Button>
            </div>
          </TabsContent>
          
          <TabsContent value="export" className="space-y-6">
            {/* 选择模块 */}
            <Card>
              <CardHeader>
                <CardTitle>选择要导出的模块</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {mockModules.map((module) => (
                    <div key={module.id} className="flex items-center space-x-3 p-3 border rounded">
                      <input
                        type="checkbox"
                        checked={selectedModules.includes(module.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedModules(prev => [...prev, module.id])
                          } else {
                            setSelectedModules(prev => prev.filter(id => id !== module.id))
                          }
                        }}
                        className="rounded"
                      />
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium">{module.name}</span>
                          <Badge variant="outline">v{module.version}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">大小: {module.size}</p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex justify-between items-center">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedModules(mockModules.map(m => m.id))}
                  >
                    全选
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    已选择 {selectedModules.length} 个模块
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* 导出选项 */}
            <Card>
              <CardHeader>
                <CardTitle>导出选项</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium">导出格式</label>
                  <Select value={exportFormat} onValueChange={setExportFormat}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="json">JSON格式</SelectItem>
                      <SelectItem value="zip">ZIP压缩包</SelectItem>
                      <SelectItem value="tar">TAR归档</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-3">
                  <label className="text-sm font-medium">包含内容</label>
                  {[
                    { key: 'includeConfig', label: '模块配置', desc: '包含模块的配置信息' },
                    { key: 'includeDependencies', label: '依赖关系', desc: '包含模块依赖信息' },
                    { key: 'includeData', label: '运行数据', desc: '包含模块运行时数据' },
                    { key: 'compression', label: '启用压缩', desc: '减小导出文件大小' }
                  ].map((option) => (
                    <div key={option.key} className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={exportOptions[option.key as keyof typeof exportOptions]}
                        onChange={(e) => setExportOptions(prev => ({
                          ...prev,
                          [option.key]: e.target.checked
                        }))}
                        className="rounded"
                      />
                      <div>
                        <p className="font-medium">{option.label}</p>
                        <p className="text-sm text-muted-foreground">{option.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 导出进度 */}
            {exportModule.isPending && (
              <Card>
                <CardHeader>
                  <CardTitle>导出进度</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Progress value={45} className="w-full" />
                    <p className="text-sm text-muted-foreground">正在打包模块文件...</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={onClose}>
                取消
              </Button>
              <Button 
                onClick={handleExport}
                disabled={exportModule.isPending || selectedModules.length === 0}
              >
                {exportModule.isPending ? '导出中...' : '开始导出'}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}