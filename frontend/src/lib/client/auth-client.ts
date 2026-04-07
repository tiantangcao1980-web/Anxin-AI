type LoginPayload = {
  email: string
  password: string
  captcha_token?: string
}

type LoginResult<User = unknown> = {
  access_token: string
  refresh_token?: string
  token_type: string
  user: User
}

type AuthApi<User> = {
  login(data: LoginPayload): Promise<LoginResult<User>>
}

type AuthStorage = {
  setAccessToken(token: string): Promise<void>
  setRefreshToken(token: string): Promise<void>
}

type PersistDesktopAuth = (token: string, refreshToken?: string) => Promise<unknown>

export function createAuthClient<User>({
  api,
  storage,
  persistDesktopAuth,
}: {
  api: AuthApi<User>
  storage: AuthStorage
  persistDesktopAuth: PersistDesktopAuth
}) {
  const persistSession = async (result: LoginResult<User>) => {
    await storage.setAccessToken(result.access_token)
    if (result.refresh_token) {
      await storage.setRefreshToken(result.refresh_token)
    }
    await persistDesktopAuth(result.access_token, result.refresh_token)
    return result
  }

  return {
    async login(data: LoginPayload) {
      const result = await api.login(data)
      return persistSession(result)
    },
    persistSession,
  }
}
