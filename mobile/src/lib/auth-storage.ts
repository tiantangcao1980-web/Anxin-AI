import AsyncStorage from '@react-native-async-storage/async-storage'
import * as SecureStore from 'expo-secure-store'
import type { AuthStorage } from './auth-storage-memory'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const BACKEND_URL_KEY = 'backend_url'

let storageSingleton: AuthStorage | null = null

export function createMobileAuthStorage(): AuthStorage {
  return {
    async getAccessToken() {
      return SecureStore.getItemAsync(ACCESS_TOKEN_KEY)
    },
    async setAccessToken(token: string) {
      await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token)
    },
    async getRefreshToken() {
      return SecureStore.getItemAsync(REFRESH_TOKEN_KEY)
    },
    async setRefreshToken(token: string) {
      await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token)
    },
    async getBackendUrl() {
      return AsyncStorage.getItem(BACKEND_URL_KEY)
    },
    async setBackendUrl(url: string) {
      await AsyncStorage.setItem(BACKEND_URL_KEY, url)
    },
    async clearBackendUrl() {
      await AsyncStorage.removeItem(BACKEND_URL_KEY)
    },
    async clearAuth() {
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY)
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY)
    },
  }
}

export function getAuthStorage(): AuthStorage {
  if (!storageSingleton) {
    storageSingleton = createMobileAuthStorage()
  }
  return storageSingleton
}
