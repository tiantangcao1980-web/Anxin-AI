import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { icons } from '@/lib/icons'

interface LawyerReferralCardProps {
  caseType?: string
  riskLevel?: 'high' | 'medium' | 'low'
  onSelectService?: (serviceType: string) => void
  onFindLawyer?: () => void
  onDismiss?: () => void
}

export default function LawyerReferralCard({
  caseType = '',
  riskLevel = 'medium',
  onSelectService,
  onFindLawyer,
  onDismiss,
}: LawyerReferralCardProps) {
  const [expanded, setExpanded] = useState(false)

  const services = [
    {
      id: 'consultation',
      name: '单次咨询服务',
      price: '¥199-499/次',
      features: ['案件深度分析', '诉讼策略建议', '文书代写代审', '30分钟在线咨询'],
      recommended: riskLevel === 'low',
    },
    {
      id: 'retainer',
      name: '长期法律顾问',
      price: '¥1,999-9,999/年',
      features: ['无限次法律咨询', '合同审查（含修改）', '案件全程跟踪', '专属律师1v1'],
      recommended: riskLevel === 'high',
    },
  ]

  return (
    <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 mt-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <icons.Briefcase className="h-5 w-5 text-amber-600" />
          专业律师协助
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          基于本案分析，建议由专业律师进一步处理以保障您的合法权益。
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {services.map((service) => (
            <div
              key={service.id}
              className="relative p-4 rounded-lg border bg-white dark:bg-gray-800 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => onSelectService?.(service.id)}
            >
              {service.recommended && (
                <Badge className="absolute -top-2 right-2 bg-amber-500 text-white text-xs">
                  推荐
                </Badge>
              )}
              <h4 className="font-semibold text-sm mb-1">{service.name}</h4>
              <p className="text-lg font-bold text-amber-600 mb-2">{service.price}</p>
              <ul className="space-y-1">
                {service.features.map((f, i) => (
                  <li key={i} className="text-xs text-muted-foreground flex items-center gap-1">
                    <icons.CheckCircle className="h-3 w-3 text-green-500 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                size="sm"
                variant={service.recommended ? 'default' : 'outline'}
                className="w-full mt-3 text-xs"
                onClick={(e) => { e.stopPropagation(); onSelectService?.(service.id) }}
              >
                {service.recommended ? '选择此服务' : '了解更多'}
              </Button>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between mt-4 pt-3 border-t">
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={onFindLawyer}
          >
            <icons.Search className="h-3 w-3 mr-1" />
            匹配推荐律师
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground"
            onClick={onDismiss}
          >
            暂不需要
          </Button>
        </div>

        <p className="text-xs text-muted-foreground mt-3 text-center">
          ⚠️ AI 分析仅供参考，不构成正式法律意见。重要法律事务请咨询执业律师。
        </p>
      </CardContent>
    </Card>
  )
}
