/**
 * OidcCallback —— OIDC IdP 回调处理页
 *
 * 流程：
 *   1. IdP 把用户重定向到 /login/oidc/callback#id_token=...&state=...
 *   2. 本页面解析 hash / query，从 sessionStorage 取 nonce
 *   3. POST /api/v1/auth/oidc/callback { id_token }
 *   4. 后端返回本地 access_token + refresh_token
 *   5. 写 store + 跳到 /chat（或 state 中的目标路径）
 *
 * 失败时显示具体后端报错，并提供"返回登录"按钮。
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/store'
import { fetchCurrentUserWithToken } from '@/lib/api'

type Stage = 'verifying' | 'failed' | 'success'

export default function OidcCallback() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [stage, setStage] = useState<Stage>('verifying')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        // IdP 用 implicit flow 时 id_token 在 fragment 里
        const hashParams = new URLSearchParams(
          window.location.hash.replace(/^#/, '')
        )
        const queryParams = new URLSearchParams(window.location.search)
        const idToken =
          hashParams.get('id_token') || queryParams.get('id_token') || ''
        const stateRaw =
          hashParams.get('state') || queryParams.get('state') || ''

        if (!idToken) {
          // IdP 可能用 error 参数返回失败
          const errCode =
            hashParams.get('error') || queryParams.get('error') || 'no_id_token'
          const errDesc =
            hashParams.get('error_description') ||
            queryParams.get('error_description') ||
            'IdP 未返回 id_token'
          throw new Error(`${errCode}: ${errDesc}`)
        }

        // POST 给后端验签
        const resp = await fetch('/api/v1/auth/oidc/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id_token: idToken }),
        })
        const data = await resp.json().catch(() => ({}))
        if (!resp.ok) {
          throw new Error(data.detail || `HTTP ${resp.status}`)
        }
        const accessToken = data.access_token as string
        if (!accessToken) throw new Error('callback 返回缺少 access_token')

        // 拿当前用户 + 写 store
        const user = await fetchCurrentUserWithToken(accessToken)
        if (!user) throw new Error('access_token 校验失败')
        login(user, accessToken)

        // 清掉 hash，避免 id_token 留在 URL 里
        window.history.replaceState({}, '', '/login/oidc/callback')

        // 决定跳回哪里
        let redirect = '/chat'
        try {
          if (stateRaw) {
            const decoded = decodeURIComponent(stateRaw)
            if (decoded.startsWith('/') && !decoded.startsWith('//')) {
              redirect = decoded
            }
          }
        } catch {
          /* ignore */
        }
        // 清 nonce
        sessionStorage.removeItem('oidc_nonce')

        setStage('success')
        if (data.is_new_user) {
          toast.success('SSO 首次登录，已自动创建账号')
        } else {
          toast.success('SSO 登录成功')
        }
        navigate(redirect, { replace: true })
      } catch (err) {
        const msg = (err as Error).message || '未知错误'
        setStage('failed')
        setError(msg)
        toast.error(`SSO 登录失败：${msg}`)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-md w-full rounded-3xl border border-border bg-card p-8 text-center space-y-4">
        {stage === 'verifying' && (
          <>
            <div className="w-12 h-12 mx-auto rounded-full border-4 border-primary border-t-transparent animate-spin" />
            <h1 className="text-lg font-medium">正在校验 SSO 凭证…</h1>
            <p className="text-sm text-muted-foreground">
              这一步会向后端发送 id_token 校验签名 / iss / aud / exp。
            </p>
          </>
        )}
        {stage === 'failed' && (
          <>
            <div className="text-3xl">⚠️</div>
            <h1 className="text-lg font-medium">SSO 登录失败</h1>
            <p className="text-sm text-destructive break-all">{error}</p>
            <div className="pt-2 flex gap-2 justify-center">
              <Button variant="outline" onClick={() => navigate('/login', { replace: true })}>
                返回登录
              </Button>
              <Button onClick={() => window.location.reload()}>重试</Button>
            </div>
          </>
        )}
        {stage === 'success' && (
          <>
            <div className="text-3xl">✅</div>
            <h1 className="text-lg font-medium">登录成功，正在跳转…</h1>
          </>
        )}
      </div>
    </div>
  )
}
