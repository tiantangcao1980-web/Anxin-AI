import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { getAuthStorage } from './auth-storage'
import type { User, Conversation } from '../types/api'

/**
 * 存储策略（单一来源）：
 * - Token（access/refresh）：统一走 SecureStore（加密存储），由 auth-storage.ts 负责。
 * - 用户画像（user）：zustand + AsyncStorage 持久化，非敏感信息，便于冷启动渲染。
 * - 登录态（isAuthenticated）：启动时由 hydrate 从 SecureStore 读 access_token 决定，
 *   避免 AsyncStorage 与 SecureStore 状态不同步。
 */

const userStorage = createJSONStorage(() => ({
  getItem: async (name: string) => await AsyncStorage.getItem(name),
  setItem: async (name: string, value: string) => await AsyncStorage.setItem(name, value),
  removeItem: async (name: string) => await AsyncStorage.removeItem(name),
}))

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  hydrated: boolean
  markHydrated: () => void
  /** 登录成功后调用：user 入 store，token 入 SecureStore */
  setAuth: (user: User, accessToken: string, refreshToken?: string) => Promise<void>
  /** 登出：清 SecureStore + 清 user */
  logout: () => Promise<void>
  /** 刷新 token 后同步认证状态（例如 401 自动续签完成） */
  syncAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(persist(
  (set) => ({
    user: null,
    isAuthenticated: false,
    hydrated: false,
    markHydrated: () => set({ hydrated: true }),
    setAuth: async (user, accessToken, refreshToken) => {
      const storage = getAuthStorage()
      await storage.setAccessToken(accessToken)
      if (refreshToken) await storage.setRefreshToken(refreshToken)
      set({ user, isAuthenticated: true })
    },
    logout: async () => {
      await getAuthStorage().clearAuth()
      set({ user: null, isAuthenticated: false })
    },
    syncAuth: async () => {
      const token = await getAuthStorage().getAccessToken()
      set({ isAuthenticated: !!token })
    },
  }),
  {
    name: 'auth-store',
    storage: userStorage,
    // 只持久化用户画像，不持久化登录态（冷启动由 SecureStore token 决定）
    partialize: (state) => ({ user: state.user }),
    onRehydrateStorage: () => async (state) => {
      // 冷启动：读 SecureStore access_token 判断登录态
      try {
        const token = await getAuthStorage().getAccessToken()
        state?.markHydrated()
        if (token && state) {
          // 手动触发 set 使 isAuthenticated 生效
          useAuthStore.setState({ isAuthenticated: true })
        } else {
          state?.markHydrated()
        }
      } catch {
        state?.markHydrated()
      }
    },
  },
))

interface ChatState {
  conversations: Conversation[]
  activeConversationId: string | null
  setConversations: (convs: Conversation[]) => void
  setActiveConversation: (id: string | null) => void
}

export const useChatStore = create<ChatState>()((set) => ({
  conversations: [],
  activeConversationId: null,
  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (activeConversationId) => set({ activeConversationId }),
}))
