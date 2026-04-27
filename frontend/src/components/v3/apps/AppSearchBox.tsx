/**
 * AppSearchBox — 应用搜索框
 *
 * 左侧 Search 图标 + 受控 Input + 右侧 Clear 按钮（仅在有输入时显示）。
 */

import { Search, X } from 'lucide-react'

import { Input } from '@/components/ui/input'
import { cn } from '@/components/ui/utils'

interface AppSearchBoxProps {
  value: string
  onChange: (next: string) => void
  placeholder?: string
  className?: string
}

export function AppSearchBox({
  value,
  onChange,
  placeholder = '搜索应用名称、描述...',
  className,
}: AppSearchBoxProps) {
  return (
    <div className={cn('relative w-full max-w-md', className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-9 pr-9"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="absolute right-2 top-1/2 inline-flex size-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="清空搜索"
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  )
}
