/**
 * SkillsPage.tsx — V3 技能（占位）
 */

import { Sparkles } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function SkillsPage() {
  return (
    <PlaceholderPage
      icon={Sparkles}
      title="技能"
      description="按需启用原子化技能，扩展智能助手的处理能力"
      plannedFeatures={[
        '官方技能市场：合同抽取、风险评分、判决要素提取、法条引用核验等',
        '按对话场景智能推荐技能，降低使用门槛',
        '自定义技能：上传 Prompt + 工具组合，封装为可复用能力',
        '技能版本管理与灰度发布，避免线上能力意外回退',
        '调用日志与质量评估，沉淀最佳实践',
      ]}
    />
  )
}
