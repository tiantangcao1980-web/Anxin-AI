import { icons } from '@/lib/icons'

interface PagePlaceholderProps {
  title: string
  description: string
  icon?: keyof typeof icons
}

export function PagePlaceholder({ title, description, icon = 'FileText' }: PagePlaceholderProps) {
  const Icon = icons[icon]
  
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="text-center max-w-md">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-muted flex items-center justify-center">
          <Icon className="w-10 h-10 text-muted-foreground/50" />
        </div>
        <h2 className="text-xl font-semibold text-foreground mb-2">{title}</h2>
        <p className="text-sm text-muted-foreground mb-6">{description}</p>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
          <icons.Sparkles className="w-4 h-4" />
          <span>功能开发中</span>
        </div>
      </div>
    </div>
  )
}
