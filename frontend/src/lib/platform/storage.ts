import { isTauri } from '@/lib/tauri-bridge'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const BACKEND_URL_KEY = 'backend_url'
const TAURI_STORE_PATH = 'auth.json'
const ZUSTAND_AUTH_KEY = 'auth-storage'

type StoreLike = {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

type DesktopStore = {
  get<T>(key: string): Promise<T | undefined>
  set(key: string, value: unknown): Promise<void>
  delete(key: string): Promise<boolean>
  save(): Promise<void>
}

export interface TokenStorage {
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

let desktopStorePromise: Promise<DesktopStore> | null = null
let tokenStorageSingleton: TokenStorage | null = null

function getBrowserStore(): StoreLike | null {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null
  }
  return window.localStorage
}

function setIfTruthy(store: StoreLike | null, key: string, value: string) {
  if (!store) {
    return
  }
  store.setItem(key, value)
}

function removeIfPresent(store: StoreLike | null, key: string) {
  if (!store) {
    return
  }
  store.removeItem(key)
}

function sanitizePersistedAuthState(store: StoreLike | null) {
  if (!store) {
    return
  }
  const raw = store.getItem(ZUSTAND_AUTH_KEY)
  if (!raw) {
    return
  }
  try {
    const parsed = JSON.parse(raw)
    if (parsed?.state && typeof parsed.state === 'object') {
      delete parsed.state.token
      store.setItem(ZUSTAND_AUTH_KEY, JSON.stringify(parsed))
    }
  } catch {
    store.removeItem(ZUSTAND_AUTH_KEY)
  }
}

function removeLegacyBrowserTokens(store: StoreLike | null) {
  removeIfPresent(store, ACCESS_TOKEN_KEY)
  removeIfPresent(store, REFRESH_TOKEN_KEY)
  sanitizePersistedAuthState(store)
}

function readLegacyBrowserToken(store: StoreLike | null, key: string): string | null {
  const token = store?.getItem(key) ?? null
  if (token) {
    removeIfPresent(store, key)
    sanitizePersistedAuthState(store)
  }
  return token
}

export function getAccessTokenSnapshot(): string | null {
  return memoryState.get(ACCESS_TOKEN_KEY) ?? null
}

export function setAccessTokenSnapshot(token: string | null) {
  if (token) {
    memoryState.set(ACCESS_TOKEN_KEY, token)
    return
  }
  memoryState.delete(ACCESS_TOKEN_KEY)
}

async function getDesktopStore(): Promise<DesktopStore> {
  if (!desktopStorePromise) {
    desktopStorePromise = import(/* @vite-ignore */ '@tauri-apps/plugin-store')
      .then(async (mod: any) => {
        const store = new mod.LazyStore(TAURI_STORE_PATH, { autoSave: true })
        await store.init()
        return store as DesktopStore
      })
      .catch((error) => {
        // Tauri store 加载失败时静默降级到内存存储，避免错误弹窗
        console.debug('[Tauri] plugin-store 加载失败，降级到浏览器存储:', error)
        throw error
      })
  }
  return desktopStorePromise
}

export function createMemoryTokenStorage(): TokenStorage {
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

export function createBrowserTokenStorage(store: StoreLike | null): TokenStorage {
  const fallback = createMemoryTokenStorage()

  return {
    async getAccessToken() {
      const token = getAccessTokenSnapshot()
      if (token) {
        return token
      }
      const legacyToken = readLegacyBrowserToken(store, ACCESS_TOKEN_KEY)
      if (legacyToken) {
        setAccessTokenSnapshot(legacyToken)
        return legacyToken
      }
      return fallback.getAccessToken()
    },
    async setAccessToken(token: string) {
      setAccessTokenSnapshot(token)
      removeLegacyBrowserTokens(store)
      await fallback.setAccessToken(token)
    },
    async getRefreshToken() {
      const legacyToken = readLegacyBrowserToken(store, REFRESH_TOKEN_KEY)
      if (legacyToken) {
        return legacyToken
      }
      return fallback.getRefreshToken()
    },
    async setRefreshToken(_token: string) {
      removeLegacyBrowserTokens(store)
      memoryState.delete(REFRESH_TOKEN_KEY)
    },
    async getBackendUrl() {
      return store?.getItem(BACKEND_URL_KEY) ?? fallback.getBackendUrl()
    },
    async setBackendUrl(url: string) {
      if (store) {
        store.setItem(BACKEND_URL_KEY, url)
        return
      }
      await fallback.setBackendUrl(url)
    },
    async clearBackendUrl() {
      if (store) {
        store.removeItem(BACKEND_URL_KEY)
        return
      }
      await fallback.clearBackendUrl()
    },
    async clearAuth() {
      setAccessTokenSnapshot(null)
      memoryState.delete(REFRESH_TOKEN_KEY)
      removeLegacyBrowserTokens(store)
      await fallback.clearAuth()
    },
  }
}

function createDesktopTokenStorage(): TokenStorage {
  const browserStore = getBrowserStore()
  const browserFallback = createBrowserTokenStorage(browserStore)

  // 尝试 desktop store，失败时降级到浏览器存储
  const tryDesktop = async <T>(op: (store: DesktopStore) => Promise<T>, fallback: () => Promise<T>): Promise<T> => {
    try {
      const store = await getDesktopStore()
      return await op(store)
    } catch {
      return fallback()
    }
  }

  return {
    async getAccessToken() {
      return tryDesktop(async (store) => {
        const token = await store.get<string>(ACCESS_TOKEN_KEY)
        if (token) {
          setAccessTokenSnapshot(token)
          removeLegacyBrowserTokens(browserStore)
          return token
        }
        const legacyToken = readLegacyBrowserToken(browserStore, ACCESS_TOKEN_KEY)
        if (legacyToken) {
          setAccessTokenSnapshot(legacyToken)
          return legacyToken
        }
        return getAccessTokenSnapshot()
      }, () => browserFallback.getAccessToken())
    },
    async setAccessToken(token: string) {
      return tryDesktop(async (store) => {
        await store.set(ACCESS_TOKEN_KEY, token)
        await store.save()
        setAccessTokenSnapshot(token)
        removeLegacyBrowserTokens(browserStore)
      }, () => browserFallback.setAccessToken(token))
    },
    async getRefreshToken() {
      return tryDesktop(async (store) => {
        const token = await store.get<string>(REFRESH_TOKEN_KEY)
        if (token) {
          removeLegacyBrowserTokens(browserStore)
          return token
        }
        return readLegacyBrowserToken(browserStore, REFRESH_TOKEN_KEY)
      }, () => browserFallback.getRefreshToken())
    },
    async setRefreshToken(token: string) {
      return tryDesktop(async (store) => {
        await store.set(REFRESH_TOKEN_KEY, token)
        await store.save()
        removeLegacyBrowserTokens(browserStore)
      }, () => browserFallback.setRefreshToken(token))
    },
    async getBackendUrl() {
      return tryDesktop(async (store) => {
        const url = await store.get<string>(BACKEND_URL_KEY)
        if (url) {
          setIfTruthy(browserStore, BACKEND_URL_KEY, url)
          return url
        }
        return browserStore?.getItem(BACKEND_URL_KEY) ?? null
      }, () => browserFallback.getBackendUrl())
    },
    async setBackendUrl(url: string) {
      return tryDesktop(async (store) => {
        await store.set(BACKEND_URL_KEY, url)
        await store.save()
        setIfTruthy(browserStore, BACKEND_URL_KEY, url)
      }, () => browserFallback.setBackendUrl(url))
    },
    async clearBackendUrl() {
      return tryDesktop(async (store) => {
        await store.delete(BACKEND_URL_KEY)
        await store.save()
        removeIfPresent(browserStore, BACKEND_URL_KEY)
      }, () => browserFallback.clearBackendUrl())
    },
    async clearAuth() {
      return tryDesktop(async (store) => {
        await store.delete(ACCESS_TOKEN_KEY)
        await store.delete(REFRESH_TOKEN_KEY)
        await store.save()
        setAccessTokenSnapshot(null)
        memoryState.delete(REFRESH_TOKEN_KEY)
        removeLegacyBrowserTokens(browserStore)
      }, () => browserFallback.clearAuth())
    },
  }
}

export function getTokenStorage(): TokenStorage {
  if (!tokenStorageSingleton) {
    tokenStorageSingleton = isTauri()
      ? createDesktopTokenStorage()
      : createBrowserTokenStorage(getBrowserStore())
  }
  return tokenStorageSingleton
}
