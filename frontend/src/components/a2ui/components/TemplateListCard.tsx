import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { icons } from '@/lib/icons'

interface Template {
  id: string
  name: string
  category: string
  sub_category: string
  description: string
  format: string
  download_path?: string
}

interface TemplateListCardProps {
  templates: Template[]
  onDownload?: (template: Template) => void
  onAIGenerate?: () => void
  onBrowseLibrary?: () => void
}

export default function TemplateListCard({
  templates,
  onDownload,
  onAIGenerate,
  onBrowseLibrary,
}: TemplateListCardProps) {
  if (!templates || templates.length === 0) {
    return (
      <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-900/20 mt-4">
        <CardContent className="pt-6">
          <div className="text-center py-4">
            <icons.FileText className="h-10 w-10 mx-auto text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground mb-4">
              暂未找到匹配的模板，您可以：
            </p>
            <div className="flex justify-center gap-3">
              <Button variant="outline" size="sm" onClick={onBrowseLibrary}>
                <icons.BookOpen className="h-4 w-4 mr-1" />
                浏览法律智库
              </Button>
              <Button size="sm" onClick={onAIGenerate}>
                <icons.Sparkles className="h-4 w-4 mr-1" />
                AI 定制生成
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 mt-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <icons.FileText className="h-5 w-5 text-blue-600" />
          为您找到 {templates.length} 个相关模板
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {templates.map((tpl) => (
            <div
              key={tpl.id}
              className="flex items-center justify-between p-3 rounded-lg border bg-white dark:bg-gray-800 hover:shadow-sm transition-shadow"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-medium truncate">{tpl.name}</h4>
                  <Badge variant="secondary" className="text-xs">
                    {tpl.format.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 truncate">
                  {tpl.description}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="ml-3 flex-shrink-0 text-xs"
                onClick={() => onDownload?.(tpl)}
              >
                <icons.Download className="h-3 w-3 mr-1" />
                下载
              </Button>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between mt-4 pt-3 border-t">
          <Button variant="ghost" size="sm" className="text-xs" onClick={onBrowseLibrary}>
            浏览更多模板
          </Button>
          <Button variant="outline" size="sm" className="text-xs" onClick={onAIGenerate}>
            <icons.Sparkles className="h-3 w-3 mr-1" />
            不满意？AI 定制生成
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
