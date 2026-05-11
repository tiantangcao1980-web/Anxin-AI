// -*- coding: utf-8 -*-
/**
 * Personas API（与 web/frontend/src/lib/api/personas.ts 契约对齐）
 *
 * 后端 endpoint：
 *   - GET    /api/v1/personas
 *   - GET    /api/v1/personas/{persona_id}
 *   - POST   /api/v1/personas/{persona_id}/chat
 *
 * 给 P21-C 使用 —— 它在 subpackages/personas/ 下做详情页 / chat 页。
 */

import { apiClient } from './client'
import type {
  Persona,
  PersonaDetail,
  PersonaListOut,
  ChatRequest,
  ChatResponse,
} from '../../types/persona'

export async function listPersonas(): Promise<Persona[]> {
  const data = await apiClient.get<PersonaListOut>('/personas')
  return data.items
}

export async function getPersona(personaId: string): Promise<PersonaDetail> {
  return apiClient.get<PersonaDetail>(`/personas/${encodeURIComponent(personaId)}`)
}

export async function chatWithPersona(
  personaId: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  return apiClient.post<ChatResponse>(
    `/personas/${encodeURIComponent(personaId)}/chat`,
    {
      message: body.message,
      history: body.history ?? [],
      extra: body.extra ?? {},
    },
  )
}

export const personasApi = {
  list: listPersonas,
  get: getPersona,
  chat: chatWithPersona,
}
