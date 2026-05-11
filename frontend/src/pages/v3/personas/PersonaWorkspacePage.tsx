/**
 * PersonaWorkspacePage — V3 persona 工作台 (P8-C)
 *
 * 路由：/v3/personas/:personaId
 *
 * 三栏布局（PersonaWorkspaceLayout）：
 *   - 顶部：persona 头像 + 名 + 描述 + 切换 persona 下拉
 *   - 左：PersonaChatPanel（接 /personas/{id}/chat）
 *   - 右：PersonaCapabilityRunner（能力清单 + 触发器）
 */

import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { PersonaChatPanel } from '@/components/v3/personas/PersonaChatPanel'
import { PersonaCapabilityRunner } from '@/components/v3/personas/PersonaCapabilityRunner'
import { PersonaWorkspaceLayout } from '@/components/v3/personas/PersonaWorkspaceLayout'

import { usePersonasStore } from '@/lib/store/personasStore'

export default function PersonaWorkspacePage() {
  const { personaId } = useParams<{ personaId: string }>()
  const navigate = useNavigate()

  const personas = usePersonasStore((s) => s.personas)
  const loading = usePersonasStore((s) => s.loading)
  const detailLoading = usePersonasStore((s) => s.detailLoading)
  const loadError = usePersonasStore((s) => s.loadError)

  const loadPersonas = usePersonasStore((s) => s.loadPersonas)
  const selectPersona = usePersonasStore((s) => s.selectPersona)
  const getPersonaById = usePersonasStore((s) => s.getPersonaById)

  // 进入页面：加载列表 + 选中详情
  useEffect(() => {
    if (personas.length === 0) {
      loadPersonas()
    }
  }, [loadPersonas, personas.length])

  useEffect(() => {
    if (personaId) {
      selectPersona(personaId)
    }
  }, [personaId, selectPersona])

  const persona = personaId ? getPersonaById(personaId) : undefined

  // 列表已加载但找不到该 persona —— 跳回 /agents
  useEffect(() => {
    if (!personaId) return
    if (personas.length === 0) return
    if (!getPersonaById(personaId)) {
      navigate('/agents', { replace: true })
    }
  }, [personaId, personas.length, getPersonaById, navigate])

  if (loadError && personas.length === 0) {
    return (
      <div className="mx-auto max-w-3xl p-10">
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
          加载失败：{loadError}
        </div>
      </div>
    )
  }

  if ((loading || detailLoading) && !persona) {
    return (
      <div className="mx-auto max-w-3xl p-10 text-center text-sm text-muted-foreground">
        正在加载 persona……
      </div>
    )
  }

  return (
    <PersonaWorkspaceLayout
      persona={persona}
      allPersonas={personas}
      onSwitchPersona={(id) => navigate(`/v3/personas/${id}`)}
      chat={persona ? <PersonaChatPanel persona={persona} /> : null}
      tools={persona ? <PersonaCapabilityRunner persona={persona} /> : null}
    />
  )
}
