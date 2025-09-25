'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface DependencyManagerProps {
  moduleId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function DependencyManager({ moduleId, isOpen, onClose }: DependencyManagerProps) {
  // 最小可回滚降级（Stub）：仅保留基础对话框结构，解除编译阻塞
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="dep-manager-dialog">
        <DialogHeader>
          <DialogTitle>依赖管理（临时占位）</DialogTitle>
        </DialogHeader>
        <div className="text-sm text-muted-foreground">
          该对话框已临时降级以恢复编译验证流程，稍后恢复完整功能。模块ID：{moduleId ?? '-'}
        </div>
      </DialogContent>
    </Dialog>
  );
}
