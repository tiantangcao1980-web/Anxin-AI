export const SYNC_STATUS_BUTTON_CLASS = [
  'inline-flex',
  'min-h-9',
  'min-w-9',
  'shrink-0',
  'items-center',
  'justify-center',
  'gap-2',
  'rounded-md',
  'px-3',
  'text-xs',
  'font-medium',
  'transition-colors',
  'hover:bg-accent',
  'focus-visible:outline-none',
  'focus-visible:ring-2',
  'focus-visible:ring-ring',
  'disabled:cursor-not-allowed',
  'disabled:opacity-50',
].join(' ')

export const SYNC_STATUS_ICON_CLASS = 'h-4 w-4'
export const SYNC_STATUS_LABEL_CLASS = 'hidden whitespace-nowrap text-foreground lg:inline'
export const SYNC_STATUS_TIME_CLASS = 'hidden whitespace-nowrap text-muted-foreground 2xl:inline'

export const SYNC_CONFLICT_BUTTON_CLASS = [
  'ml-2',
  'inline-flex',
  'min-h-9',
  'shrink-0',
  'items-center',
  'gap-1.5',
  'rounded-md',
  'border',
  'border-destructive/20',
  'bg-destructive/10',
  'px-3',
  'text-xs',
  'font-medium',
  'text-destructive',
  'transition-colors',
  'hover:bg-destructive/15',
  'focus-visible:outline-none',
  'focus-visible:ring-2',
  'focus-visible:ring-destructive/30',
].join(' ')

export const SYNC_CONFLICT_ICON_CLASS = 'h-4 w-4'
export const SYNC_CONFLICT_LABEL_CLASS = 'hidden whitespace-nowrap xl:inline'
export const SYNC_CONFLICT_COUNT_CLASS =
  'rounded-full bg-destructive/15 px-1.5 py-0.5 text-[11px] leading-none tabular-nums'

export function syncToolbarStatusLabel(isSyncing: boolean, statusLabel: string) {
  if (isSyncing) return '同步中'
  return statusLabel.replace(/\.\.\.$/, '')
}
