import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import AsyncStorage from '@react-native-async-storage/async-storage'
import type { User, Conversation } from '../types/api'

const asyncStorage = createJSONStorage(() => ({
  getItem: async (name: string) => await AsyncStorage.getItem(name),
  setItem: async (name: string, value: string) => await AsyncStorage.setItem(name, value),
  removeItem: async (name: string) => await AsyncStorage.removeItem(name),
}))

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(persist(
  (set) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
    logout: () => set({ user: null, token: null, isAuthenticated: false }),
  }),
  { name: 'auth-store', storage: asyncStorage }
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
