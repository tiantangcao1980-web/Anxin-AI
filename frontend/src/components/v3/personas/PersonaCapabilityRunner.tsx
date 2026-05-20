/**
 * PersonaCapabilityRunner — 触发 capability 的 form
 *
 * 设计取舍：
 *   各 persona 的专属 endpoint（OKR / 周报 / 选品 / 内容生成 ……）参数差异很大，
 *   P8-C 不为每个写专属 form；改成一个统一的 "capability 触发器"：
 *
 *     1. 显示 persona 的能力清单 + 状态徽章（PersonaCapabilityList）
 *     2. 用户挑选一条 capability → 在下方出现一个简洁的 textarea
 *     3. 提交 → 通过 chat() 发送 "请帮我执行：<capability> | <用户输入>"
 *        到通用 /personas/{id}/chat 端点
 *
 *   这样：
 *   - 5 个已实装 persona：通用 chat 后端会路由 capability（已支持）
 *   - 5 个未实装 persona：mock chat 给占位回复 + "规划中" 提示
 *
 *   后续 P9+ 可在此基础上为高频 capability 接入专属 endpoint。
 */

import { useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

import type { Persona } from '@/lib/api/personas'
import { usePersonasStore } from '@/lib/store/personasStore'

import { PersonaAppsBadges } from './PersonaAppsBadges'
import { PersonaCapabilityList } from './PersonaCapabilityList'
import { PersonaSkillsBadges } from './PersonaSkillsBadges'

interface Props {
  persona: Persona
}

export function PersonaCapabilityRunner({ persona }: Props) {
  const [pickedCapability, setPickedCapability] = useState<string | null>(null)
  const [extraInput, setExtraInput] = useState('')
  const chat = usePersonasStore((s) => s.chat)
  const pending = usePersonasStore((s) => s.chatPending)

  const trigger = async () => {
    if (!pickedCapability) {
      toast.warning('请先选择一项能力')
      return
    }
    const baseName = pickedCapability.split('（')[0]
    const message = extraInput.trim()
      ? `请帮我执行：${baseName}\n\n详细输入：\n${extraInput.trim()}`
      : `请帮我执行：${baseName}`
    setExtraInput('')
    try {
      await chat(persona.persona_id, message, {
        capability: baseName,
        is_implemented: !!persona.is_implemented,
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '触发失败')
    }
  }

  return (
    <div className="space-y-5 p-4">
      {/* 能力清单 */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          能力清单（{persona.capabilities.length}）
        </h3>
        <PersonaCapabilityList
          capabilities={persona.capabilities}
          isImplemented={!!persona.is_implemented}
          selectedCapability={pickedCapability}
          onPick={(c) => setPickedCapability(c)}
        />
      </section>

      {/* 触发输入 */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          触发能力
        </h3>
        {pickedCapability ? (
          <p className="text-xs text-foreground">
            将触发：
            <span className="ml-1 rounded bg-primary/10 px-1.5 py-0.5 font-medium text-primary">
              {pickedCapability.split('（')[0]}
            </span>
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">在上方选一项能力，然后填写输入并触发。</p>
        )}
        <Textarea
          rows={3}
          value={extraInput}
          onChange={(e) => setExtraInput(e.target.value)}
          placeholder="可选：贴入你的输入（如合同链接 / OKR 期间 / 选品关键词……）"
          disabled={!pickedCapability || pending}
          className="text-xs"
        />
        <Button
          onClick={trigger}
          disabled={!pickedCapability || pending}
          className="w-full gap-1"
          size="sm"
        >
          {pending ? <icons.Loader2 className="size-3.5 animate-spin" /> : <icons.PlayCircle className="size-3.5" />}
          {pending ? '执行中…' : '触发并发送到对话'}
        </Button>
      </section>

      {/* skills */}
      {persona.backed_by_skills.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            背后调用的技能（{persona.backed_by_skills.length}）
          </h3>
          <PersonaSkillsBadges skills={persona.backed_by_skills} max={20} />
        </section>
      )}

      {/* apps */}
      {persona.supported_apps.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            集成应用（{persona.supported_apps.length}）
          </h3>
          <PersonaAppsBadges apps={persona.supported_apps} max={20} />
        </section>
      )}
    </div>
  )
}
