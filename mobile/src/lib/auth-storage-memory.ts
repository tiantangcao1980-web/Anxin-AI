const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const BACKEND_URL_KEY = 'backend_url'

export interface AuthStorage {
  getAccessToken(): Promise<string | null>
  setAccessToken(token: string): Promise<void>
  getRefreshToken(): Promise<string | null>
  setRefreshToken(token: string): Promise<void>
  getBackendUrl(): Promise<string | null>
  setBackendUrl(url: string): Promise<void>
  clearBackendUrl(): Promise<void>
  clearAuth(): Promise<void>
}

const memoryState = new Map<string, string>()

export function createMemoryAuthStorage(): AuthStorage {
  return {
    async getAccessToken() {
      return memoryState.get(ACCESS_TOKEN_KEY) ?? null
    },
    async setAccessToken(token: string) {
      memoryState.set(ACCESS_TOKEN_KEY, token)
    },
    async getRefreshToken() {
      return memoryState.get(REFRESH_TOKEN_KEY) ?? null
    },
    async setRefreshToken(token: string) {
      memoryState.set(REFRESH_TOKEN_KEY, token)
    },
    async getBackendUrl() {
      return memoryState.get(BACKEND_URL_KEY) ?? null
    },
    async setBackendUrl(url: string) {
      memoryState.set(BACKEND_URL_KEY, url)
    },
    async clearBackendUrl() {
      memoryState.delete(BACKEND_URL_KEY)
    },
    async clearAuth() {
      memoryState.delete(ACCESS_TOKEN_KEY)
      memoryState.delete(REFRESH_TOKEN_KEY)
    },
  }
}
