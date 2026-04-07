import { isTauri } from '@/lib/tauri-bridge'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const BACKEND_URL_KEY = 'backend_url'
const TAURI_STORE_MODULE = '@tauri-apps' + '/plugin-store'
const TAURI_STORE_PATH = 'auth.json'

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

async function getDesktopStore(): Promise<DesktopStore> {
  if (!desktopStorePromise) {
    desktopStorePromise = import(TAURI_STORE_MODULE).then(async (mod) => {
      const store = new mod.LazyStore(TAURI_STORE_PATH, { autoSave: true })
      await store.init()
      return store as DesktopStore
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

function createBrowserTokenStorage(store: StoreLike | null): TokenStorage {
  const fallback = createMemoryTokenStorage()

  return {
    async getAccessToken() {
      return store?.getItem(ACCESS_TOKEN_KEY) ?? fallback.getAccessToken()
    },
    async setAccessToken(token: string) {
      if (store) {
        store.setItem(ACCESS_TOKEN_KEY, token)
        return
      }
      await fallback.setAccessToken(token)
    },
    async getRefreshToken() {
      return store?.getItem(REFRESH_TOKEN_KEY) ?? fallback.getRefreshToken()
    },
    async setRefreshToken(token: string) {
      if (store) {
        store.setItem(REFRESH_TOKEN_KEY, token)
        return
      }
      await fallback.setRefreshToken(token)
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
      if (store) {
        store.removeItem(ACCESS_TOKEN_KEY)
        store.removeItem(REFRESH_TOKEN_KEY)
        return
      }
      await fallback.clearAuth()
    },
  }
}

function createDesktopTokenStorage(): TokenStorage {
  const browserStore = getBrowserStore()

  return {
    async getAccessToken() {
      const store = await getDesktopStore()
      const token = await store.get<string>(ACCESS_TOKEN_KEY)
      if (token) {
        setIfTruthy(browserStore, ACCESS_TOKEN_KEY, token)
        return token
      }
      return browserStore?.getItem(ACCESS_TOKEN_KEY) ?? null
    },
    async setAccessToken(token: string) {
      const store = await getDesktopStore()
      await store.set(ACCESS_TOKEN_KEY, token)
      await store.save()
      setIfTruthy(browserStore, ACCESS_TOKEN_KEY, token)
    },
    async getRefreshToken() {
      const store = await getDesktopStore()
      const token = await store.get<string>(REFRESH_TOKEN_KEY)
      if (token) {
        setIfTruthy(browserStore, REFRESH_TOKEN_KEY, token)
        return token
      }
      return browserStore?.getItem(REFRESH_TOKEN_KEY) ?? null
    },
    async setRefreshToken(token: string) {
      const store = await getDesktopStore()
      await store.set(REFRESH_TOKEN_KEY, token)
      await store.save()
      setIfTruthy(browserStore, REFRESH_TOKEN_KEY, token)
    },
    async getBackendUrl() {
      const store = await getDesktopStore()
      const url = await store.get<string>(BACKEND_URL_KEY)
      if (url) {
        setIfTruthy(browserStore, BACKEND_URL_KEY, url)
        return url
      }
      return browserStore?.getItem(BACKEND_URL_KEY) ?? null
    },
    async setBackendUrl(url: string) {
      const store = await getDesktopStore()
      await store.set(BACKEND_URL_KEY, url)
      await store.save()
      setIfTruthy(browserStore, BACKEND_URL_KEY, url)
    },
    async clearBackendUrl() {
      const store = await getDesktopStore()
      await store.delete(BACKEND_URL_KEY)
      await store.save()
      removeIfPresent(browserStore, BACKEND_URL_KEY)
    },
    async clearAuth() {
      const store = await getDesktopStore()
      await store.delete(ACCESS_TOKEN_KEY)
      await store.delete(REFRESH_TOKEN_KEY)
      await store.save()
      removeIfPresent(browserStore, ACCESS_TOKEN_KEY)
      removeIfPresent(browserStore, REFRESH_TOKEN_KEY)
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
