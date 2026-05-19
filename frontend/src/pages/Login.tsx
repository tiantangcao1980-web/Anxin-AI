/**
 * Login.tsx - 登录注册页面
 *
 * 左右分栏布局，左侧品牌展示 + 右侧登录/注册表单。
 * 支持邮箱密码登录、微信扫码、支付宝三种方式。
 * 移动端仅显示右侧表单区域。
 */

import { useState, useEffect, useRef, useCallback } from'react'
import { useNavigate, useLocation } from'react-router-dom'
import { motion, AnimatePresence } from'framer-motion'
import { toast } from'sonner'
import { icons } from'@/lib/icons'
import { authApi, type LoginResponse } from'@/lib/api'
import { createAuthClient } from'@/lib/client/auth-client'
import { getTokenStorage } from'@/lib/platform/storage'
import { useAuthStore } from'@/lib/store'
import { saveAuthToken } from'@/lib/tauri-bridge'
import { iconSize, radius, buttonStyle, heading, inputStyle, statusColor } from'@/lib/design-tokens'

declare global {
 interface Window {
 turnstile?: {
 render: (container: HTMLElement, options: Record<string, unknown>) => string | number
 reset: (widgetId?: string | number) => void
 }
 }
}

export default function Login() {
 const navigate = useNavigate()
 const location = useLocation()
 const { login: setAuth } = useAuthStore()
 const [mode, setMode] = useState<'login' |'register' |'forgot' |'verify'>('login')
 const [loading, setLoading] = useState(false)

 // V2 架构：从 URL 读取客户端角色 (?role=provider 表示服务方端登录)
 // 路由 /pro/login 会自动附加此参数
 const searchParams = new URLSearchParams(location.search)
 const clientRole: 'needer' | 'provider' = (searchParams.get('role') === 'provider' || location.pathname.startsWith('/pro')) ? 'provider' : 'needer'

 // 功能开关
 const [features, setFeatures] = useState({
 email_verify_enabled: false,
 sms_enabled: false,
 oauth_wechat_enabled: false,
 oauth_alipay_enabled: false,
 captcha_enabled: false,
 captcha_provider:'',
 captcha_site_key:'',
 })
 const [captchaToken, setCaptchaToken] = useState('')
 const captchaContainerRef = useRef<HTMLDivElement | null>(null)
 const captchaWidgetIdRef = useRef<string | number | null>(null)
 const captchaScriptLoadedRef = useRef(false)

 // 忘记密码
 const [forgotEmail, setForgotEmail] = useState('')
 const [resetToken, setResetToken] = useState('')
 const [newPassword, setNewPassword] = useState('')
 const [forgotStep, setForgotStep] = useState<'email' |'code' |'done'>('email')

 useEffect(() => {
 fetch('/api/v1/auth/features').then(r => r.json()).then(d => {
 const data = d.data || d
 setFeatures(data)
 }).catch(() => {})
 }, [])

 const captchaRequired = Boolean(
 features.captcha_enabled
 && (
 mode ==='login'
 || mode ==='register'
 || (mode ==='forgot' && forgotStep ==='email')
 )
 )

 const resetCaptcha = useCallback(() => {
 setCaptchaToken('')
 if (window.turnstile && captchaWidgetIdRef.current !== null) {
 window.turnstile.reset(captchaWidgetIdRef.current)
 }
 }, [])

 const renderCaptcha = useCallback(() => {
 if (!captchaRequired || !features.captcha_site_key) return
 if (!window.turnstile || !captchaContainerRef.current) return
 if (captchaWidgetIdRef.current !== null) return

 captchaWidgetIdRef.current = window.turnstile.render(captchaContainerRef.current, {
 sitekey: features.captcha_site_key,
 theme:'auto',
 callback: (token: string) => setCaptchaToken(token),
'expired-callback': () => setCaptchaToken(''),
'error-callback': () => setCaptchaToken(''),
 })
 }, [captchaRequired, features.captcha_site_key])

 useEffect(() => {
 if (!features.captcha_enabled || features.captcha_provider !=='turnstile') return

 const existing = document.querySelector<HTMLScriptElement>('script[data-turnstile]')
 const onReady = () => {
 captchaScriptLoadedRef.current = true
 renderCaptcha()
 }

 if (window.turnstile) {
 onReady()
 return
 }

 if (existing) {
 existing.addEventListener('load', onReady, { once: true })
 return () => existing.removeEventListener('load', onReady)
 }

 const script = document.createElement('script')
 script.src ='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
 script.async = true
 script.defer = true
 script.dataset.turnstile ='true'
 script.addEventListener('load', onReady, { once: true })
 document.head.appendChild(script)

 return () => script.removeEventListener('load', onReady)
 }, [features.captcha_enabled, features.captcha_provider, renderCaptcha])

 useEffect(() => {
 if (!captchaRequired) {
 setCaptchaToken('')
 return
 }
 if (captchaWidgetIdRef.current !== null) {
 resetCaptcha()
 } else if (captchaScriptLoadedRef.current) {
 renderCaptcha()
 }
 }, [captchaRequired, mode, forgotStep, renderCaptcha, resetCaptcha])

 // 登录表单
 const [email, setEmail] = useState('')
 const [password, setPassword] = useState('')
 const [showPassword, setShowPassword] = useState(false)

 // 注册表单
 const [regName, setRegName] = useState('')
 const [regEmail, setRegEmail] = useState('')
 const [regPassword, setRegPassword] = useState('')
 const [regConfirm, setRegConfirm] = useState('')
 const [showRegPassword, setShowRegPassword] = useState(false)
 const [agreedTerms, setAgreedTerms] = useState(false)
 // V2 架构：根据客户端角色设置默认用户类型
 const [regUserType, setRegUserType] = useState<'individual' |'enterprise' |'platform_lawyer' |'institution'>(
   clientRole === 'provider' ? 'platform_lawyer' : 'individual'
 )

 // 邮箱验证
 const [verifyEmail, setVerifyEmail] = useState('')
 const [verifyCode, setVerifyCode] = useState('')
 const [resendCountdown, setResendCountdown] = useState(0)
 const authClient = createAuthClient({
 api: authApi,
 storage: getTokenStorage(),
 persistDesktopAuth: saveAuthToken,
 })

 // 密码强度计算
 const getPasswordStrength = (pwd: string): { level: number; label: string; color: string } => {
 if (!pwd) return { level: 0, label:'', color:'' }
 let score = 0
 if (pwd.length >= 8) score++
 if (pwd.length >= 12) score++
 if (/[A-Z]/.test(pwd)) score++
 if (/[a-z]/.test(pwd)) score++
 if (/[0-9]/.test(pwd)) score++
 if (/[^A-Za-z0-9]/.test(pwd)) score++
 if (score <= 2) return { level: 1, label:'弱', color:'bg-destructive' }
 if (score <= 4) return { level: 2, label:'中', color:'bg-warning' }
 return { level: 3, label:'强', color:'bg-success' }
 }
 const pwdStrength = getPasswordStrength(regPassword)

 // 登录成功后跳转的目标路径（V2 架构：按 primary_client 决定默认入口）
 const fromState = (location.state as { from?: string })?.from
 // 根据用户的 primary_client 推断默认主入口
 const getDefaultHomeForUser = (u: { primary_client?: string; role?: string }): string => {
   if (u.primary_client === 'provider' || u.role === 'platform_lawyer' || u.role === 'org_admin') {
     return '/pro/dashboard'
   }
   return '/chat'
 }

 const persistSession = async (resp: LoginResponse) => {
 await authClient.persistSession(resp)
 setAuth(resp.user, resp.access_token)
 }

 const handleLogin = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!email || !password) {
 toast.error('请填写邮箱和密码')
 return
 }
 setLoading(true)
 try {
 const resp = await authClient.login({ email, password, captcha_token: captchaToken || undefined })
 setAuth(resp.user, resp.access_token)
 toast.success(`欢迎回来，${resp.user.name}！`)
 // V2: 如果指定了 from，去 from；否则根据用户身份决定默认入口
 const target = fromState || getDefaultHomeForUser(resp.user)
 navigate(target, { replace: true })
 } catch (err: any) {
 const msg = err.message ||'登录失败，请检查邮箱和密码'
 if (msg.includes('邮箱未验证')) {
 toast.error('邮箱未验证，请先完成验证')
 setVerifyEmail(email)
 setMode('verify')
 // 自动发送验证码
 if (!captchaRequired) authApi.resendVerification(email).catch(() => {})
 } else {
 toast.error(msg)
 }
 } finally {
 if (captchaRequired) resetCaptcha()
 setLoading(false)
 }
 }

 const handleRegister = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!regName || !regEmail || !regPassword) {
 toast.error('请填写完整注册信息')
 return
 }
 if (regPassword !== regConfirm) {
 toast.error('两次密码输入不一致')
 return
 }
 if (regPassword.length < 8) {
 toast.error('密码长度不能少于8位')
 return
 }
 if (!agreedTerms) {
 toast.error('请阅读并同意服务协议')
 return
 }
 setLoading(true)
 try {
 const resp = await authApi.register({
 name: regName,
 email: regEmail,
 password: regPassword,
 user_type: regUserType,
 captcha_token: captchaToken || undefined,
 }) as any
 if (resp.email_verified) {
 // 邮箱验证未启用，注册后自动登录
 try {
 const loginResp = await authApi.login({ email: regEmail, password: regPassword })
 await persistSession(loginResp)
 toast.success(`注册成功！欢迎 ${loginResp.user.name}`)
 navigate(fromState || '/chat', { replace: true })
 return
 } catch {
 toast.success('注册成功！请登录')
 setMode('login')
 setEmail(regEmail)
 }
 } else {
 // 邮箱验证已启用，跳转到验证步骤
 toast.success('注册成功！请查收邮箱验证码')
 setVerifyEmail(regEmail)
 setVerifyCode('')
 setMode('verify')
 }
 } catch (err: any) {
 const msg = err.message ||'注册失败'
 if (msg.includes('already') || msg.includes('已注册') || msg.includes('exist')) {
 toast.error('该邮箱已注册，请直接登录')
 setMode('login')
 setEmail(regEmail)
 } else {
 toast.error(msg)
 }
 } finally {
 if (captchaRequired) resetCaptcha()
 setLoading(false)
 }
 }

 const handleForgotPassword = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!forgotEmail) {
 toast.error('请输入邮箱地址')
 return
 }
 setLoading(true)
 try {
 const resp = await authApi.forgotPassword(forgotEmail, captchaToken || undefined)
 toast.success('验证码已发送到您的邮箱')
 if (resp.debug_token) {
 // 开发模式自动填充验证码
 setResetToken(resp.debug_token)
 }
 setForgotStep('code')
 } catch (err: any) {
 toast.error(err.message ||'发送失败')
 } finally {
 if (captchaRequired) resetCaptcha()
 setLoading(false)
 }
 }

 const handleResetPassword = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!resetToken || !newPassword) {
 toast.error('请填写重置令牌和新密码')
 return
 }
 if (newPassword.length < 8) {
 toast.error('密码长度不能少于8位')
 return
 }
 if (captchaRequired && !captchaToken) {
 toast.error('请先完成人机验证')
 return
 }
 setLoading(true)
 try {
 await authApi.resetPassword(resetToken, newPassword, captchaToken || undefined)
 toast.success('密码重置成功！请使用新密码登录')
 setForgotStep('done')
 setTimeout(() => {
 setMode('login')
 setEmail(forgotEmail)
 setPassword('')
 setForgotStep('email')
 setForgotEmail('')
 setResetToken('')
 setNewPassword('')
 }, 1500)
 } catch (err: any) {
 toast.error(err.message ||'重置失败')
 } finally {
 if (captchaRequired) resetCaptcha()
 setLoading(false)
 }
 }

 const handleVerifyEmail = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!verifyCode || verifyCode.length !== 6) {
 toast.error('请输入6位验证码')
 return
 }
 setLoading(true)
 try {
 const resp = await authApi.verifyEmail(verifyEmail, verifyCode)
 await persistSession(resp)
 toast.success('邮箱验证成功！')
 navigate(fromState || '/chat', { replace: true })
 } catch (err: any) {
 toast.error(err.message ||'验证失败')
 } finally {
 setLoading(false)
 }
 }

 const handleResendVerification = async () => {
 if (resendCountdown > 0) return
 if (captchaRequired && !captchaToken) {
 toast.error('请先完成人机验证')
 return
 }
 try {
 await authApi.resendVerification(verifyEmail, captchaToken || undefined)
 toast.success('验证码已重新发送')
 setResendCountdown(60)
 const timer = setInterval(() => {
 setResendCountdown((prev) => {
 if (prev <= 1) { clearInterval(timer); return 0 }
 return prev - 1
 })
 }, 1000)
 } catch (err: any) {
 toast.error(err.message ||'发送失败')
 } finally {
 if (captchaRequired) resetCaptcha()
 }
 }

 const handleOAuth = async (provider:'wechat' |'alipay') => {
 try {
 const resp = await fetch(`/api/v1/auth/oauth/${provider}/url`)
 const data = await resp.json()
 if (data.url) {
 // 在新窗口中打开 OAuth 授权页
 window.open(data.url,'_blank','width=600,height=700')
 toast.info(`正在打开${provider ==='wechat' ?'微信' :'支付宝'}授权页面...`)
 }
 } catch {
 toast.error(`${provider ==='wechat' ?'微信' :'支付宝'}登录暂不可用`)
 }
 }

 // 输入框通用样式 — 基于 design-tokens inputStyle.search，增加左图标 padding
 const inputCls =
 `${inputStyle.search} pl-10 py-2.5 focus:border-transparent`

 const captchaBlock = captchaRequired ? (
 <div className="space-y-2">
 <label className="block text-sm font-medium text-foreground">安全验证</label>
 <div ref={captchaContainerRef} className="min-h-[70px]" />
 {!captchaToken && (
 <p className="text-xs text-muted-foreground">请先完成人机验证后再提交。</p>
 )}
 </div>
 ) : null

 return (
 <div className="min-h-screen flex bg-background">
 {/* ===== 左侧品牌展示区（无渐变，适配深浅色模式） ===== */}
 <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden flex-col justify-between p-12 bg-muted/50 dark:bg-muted/20 border-r border-border/30">
 {/* 装饰元素 — 几何圆环 */}
 <div className="absolute inset-0 pointer-events-none">
 <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full border-[3px] border-primary/10 dark:border-primary/5" />
 <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full border-[2px] border-primary/8 dark:border-primary/4" />
 <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full border-[3px] border-primary/8 dark:border-primary/4" />
 <div className="absolute top-1/3 right-1/4 w-3 h-3 rounded-full bg-primary/20 dark:bg-primary/10" />
 <div className="absolute top-2/3 left-1/5 w-2 h-2 rounded-full bg-primary/15 dark:bg-primary/8" />
 <div className="absolute bottom-1/4 right-1/3 w-4 h-4 rounded-full bg-primary/10 dark:bg-primary/5" />
 </div>

 <div className="relative z-10">
 {/* Logo */}
 <div className="flex items-center gap-3 mb-12">
 <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center shadow-sm">
 <icons.Legal className={`${iconSize.lg} text-primary-foreground`} />
 </div>
 <div>
 <h1 className={`${heading.page} text-foreground text-2xl`}>安心智能助手</h1>
 <p className="text-sm text-muted-foreground">全链路超级 AI 智能助手系统</p>
 </div>
 </div>

 {/* 特性列表 — V3 全链路定位：覆盖法务、财税、合规、市场、获客、内容、出海等多角色 */}
 <div className="space-y-6 mb-12">
 {[
 { Icon: icons.Brain, title:'多智能体协作', desc:'10+ 专业智能体协同覆盖业务全流程' },
 { Icon: icons.Shield, title:'全流程风控', desc:'AI 实时监控合规、合同、商业与运营风险' },
 { Icon: icons.Zap, title:'效率提升10倍', desc:'自动化合同审查、文书起草、市场研究、出海运营' },
 ].map((feature, i) => (
 <motion.div
 key={feature.title}
 initial={{ opacity: 0, x: -30 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.2 + i * 0.15 }}
 className="flex items-start gap-4"
 >
 <div className="w-10 h-10 bg-primary/10 dark:bg-primary/15 rounded-lg flex items-center justify-center flex-shrink-0">
 <feature.Icon className={`${iconSize.md} text-primary`} />
 </div>
 <div>
 <h3 className="text-foreground font-medium">{feature.title}</h3>
 <p className="text-muted-foreground text-sm mt-1">{feature.desc}</p>
 </div>
 </motion.div>
 ))}
 </div>

 {/* 形象角色占位区 — 待设计完成后替换 */}
 <div className="flex gap-4 items-end">
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.6 }}
 className="w-28 h-36 bg-primary/5 dark:bg-primary/10 rounded-2xl border-2 border-dashed border-primary/20 dark:border-primary/15 flex flex-col items-center justify-center gap-2"
 >
 <icons.User className="w-8 h-8 text-primary/30 dark:text-primary/20" />
 <span className="text-[10px] text-muted-foreground/60">形象角色 1</span>
 </motion.div>
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.75 }}
 className="w-24 h-32 bg-primary/5 dark:bg-primary/10 rounded-2xl border-2 border-dashed border-primary/20 dark:border-primary/15 flex flex-col items-center justify-center gap-2"
 >
 <icons.Bot className="w-7 h-7 text-primary/30 dark:text-primary/20" />
 <span className="text-[10px] text-muted-foreground/60">形象角色 2</span>
 </motion.div>
 </div>
 </div>

 <p className="relative z-10 text-muted-foreground/50 text-xs">
 &copy; 2026 安心智能助手 &middot; 赋能企业全链路智能化
 </p>
 </div>

 {/* ===== 右侧表单区 ===== */}
 <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 className="w-full max-w-md"
 >
 {/* 移动端 Logo */}
 <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
 <div className={`w-10 h-10 bg-primary ${radius.card} flex items-center justify-center`}>
 <icons.Legal className={`${iconSize.md} text-primary-foreground`} />
 </div>
 <h1 className={heading.page}>安心智能助手</h1>
 </div>

 {/* Tab 切换（忘记密码模式时隐藏） */}
 {mode !=='forgot' && mode !=='verify' ? (
 <div className={`flex gap-1 mb-8 bg-muted p-1 ${radius.card}`}>
 {(['login','register'] as const).map((tab) => (
 <button
 key={tab}
 onClick={() => setMode(tab)}
 className={`flex-1 py-2.5 ${radius.button} text-sm font-medium transition-colors ${
 mode === tab
 ?'bg-background text-foreground shadow-sm'
 :'text-muted-foreground hover:text-foreground'
 }`}
 >
 {tab ==='login' ?'登录' :'注册'}
 </button>
 ))}
 </div>
 ) : (
 <button
 onClick={() => { setMode('login'); setForgotStep('email'); }}
 className="flex items-center gap-1.5 mb-6 text-sm text-muted-foreground hover:text-foreground transition-colors"
 >
 <icons.ArrowLeft className={iconSize.sm} />
 返回登录
 </button>
 )}

 <AnimatePresence mode="wait">
 {mode ==='forgot' ? (
 <motion.div
 key="forgot"
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 >
 <h2 className={`${heading.page} mb-2`}>重置密码</h2>
 <p className={`${heading.muted} mb-6`}>
 {forgotStep ==='email' &&'输入注册邮箱，我们将发送验证码'}
 {forgotStep ==='code' &&'输入验证码和新密码'}
 {forgotStep ==='done' &&'密码重置成功！'}
 </p>

 {forgotStep ==='email' && (
 <form onSubmit={handleForgotPassword} className="space-y-4">
 <div className="relative">
 <icons.Mail className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type="email"
 value={forgotEmail}
 onChange={(e) => setForgotEmail(e.target.value)}
 placeholder="请输入注册邮箱"
 className={inputCls}
 autoFocus
 />
 </div>
 {captchaBlock}
 <button
 type="submit"
 disabled={loading || (captchaRequired && !captchaToken)}
 className={`${buttonStyle.primary} w-full py-2.5 disabled:opacity-60 flex items-center justify-center gap-2`}
 >
 {loading && <icons.Loader2 className={`${iconSize.sm} animate-spin`} />}
 {loading ?'发送中...' :'发送验证码'}
 </button>
 </form>
 )}

 {forgotStep ==='code' && (
 <form onSubmit={handleResetPassword} className="space-y-4">
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">重置令牌</label>
 <div className="relative">
 <icons.Key className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type="text"
 value={resetToken}
 onChange={(e) => setResetToken(e.target.value)}
 placeholder="请输入邮箱中的重置令牌"
 maxLength={128}
 className={inputCls +' font-mono text-sm'}
 autoFocus
 />
 </div>
 </div>
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">新密码</label>
 <div className="relative">
 <icons.Lock className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type="password"
 value={newPassword}
 onChange={(e) => setNewPassword(e.target.value)}
 placeholder="请输入新密码（至少8位）"
 className={inputCls}
 />
 </div>
 </div>
 {captchaBlock}
 <button
 type="submit"
 disabled={loading || (captchaRequired && !captchaToken)}
 className={`${buttonStyle.primary} w-full py-2.5 disabled:opacity-60 flex items-center justify-center gap-2`}
 >
 {loading && <icons.Loader2 className={`${iconSize.sm} animate-spin`} />}
 {loading ?'重置中...' :'重置密码'}
 </button>
 <button
 type="button"
 onClick={() => setForgotStep('email')}
 className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
 >
 没收到验证码？重新发送
 </button>
 </form>
 )}

 {forgotStep ==='done' && (
 <div className="text-center py-8">
 <div className={`w-16 h-16 ${statusColor.success} ${radius.avatar} flex items-center justify-center mx-auto mb-4`}>
 <icons.CheckCircle className={`${iconSize.xl} text-success`} />
 </div>
 <p className="text-foreground font-medium">密码重置成功</p>
 <p className="text-sm text-muted-foreground mt-1">即将返回登录页面...</p>
 </div>
 )}
 </motion.div>
 ) : mode ==='verify' ? (
 <motion.div
 key="verify"
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 >
 <h2 className={`${heading.page} mb-2`}>邮箱验证</h2>
 <p className={`${heading.muted} mb-6`}>
 验证码已发送至 <span className="font-medium text-foreground">{verifyEmail}</span>
 </p>
 <form onSubmit={handleVerifyEmail} className="space-y-4">
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">验证码</label>
 <input
 type="text"
 maxLength={6}
 placeholder="请输入6位验证码"
 value={verifyCode}
 onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g,'').slice(0, 6))}
 className={inputCls +' text-center text-2xl tracking-[0.5em] font-mono'}
 />
 </div>
 <button
 type="submit"
 disabled={loading || verifyCode.length !== 6}
 className={`${buttonStyle.primary} w-full h-11 ${radius.button} font-medium`}
 >
 {loading ?'验证中...' :'验证邮箱'}
 </button>
 {captchaBlock}
 <div className="text-center text-sm text-muted-foreground">
 没收到验证码？{''}
 <button
 type="button"
 onClick={handleResendVerification}
 disabled={resendCountdown > 0 || (captchaRequired && !captchaToken)}
 className="text-primary hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
 >
 {resendCountdown > 0 ? `${resendCountdown}秒后重发` :'重新发送'}
 </button>
 </div>
 <div className="text-center">
 <button
 type="button"
 onClick={() => { setMode('login'); setEmail(verifyEmail) }}
 className="text-sm text-muted-foreground hover:text-foreground"
 >
 返回登录
 </button>
 </div>
 </form>
 </motion.div>
 ) : mode ==='login' ? (
 <motion.form
 key="login"
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 20 }}
 onSubmit={handleLogin}
 className="space-y-5"
 >
 {/* 邮箱 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">邮箱</label>
 <div className="relative">
 <icons.Mail className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type="email"
 value={email}
 onChange={(e) => setEmail(e.target.value)}
 placeholder="请输入邮箱地址"
 className={inputCls}
 autoComplete="email"
 />
 </div>
 </div>

 {/* 密码 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">密码</label>
 <div className="relative">
 <icons.Lock className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type={showPassword ?'text' :'password'}
 value={password}
 onChange={(e) => setPassword(e.target.value)}
 placeholder="请输入密码"
 className={inputCls +' pr-10'}
 autoComplete="current-password"
 />
 <button
 type="button"
 onClick={() => setShowPassword(!showPassword)}
 className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
 >
 {showPassword ? <icons.EyeOff className={iconSize.sm} /> : <icons.Eye className={iconSize.sm} />}
 </button>
 </div>
 </div>

 {/* 记住我 & 忘记密码 */}
 <div className="flex items-center justify-between">
 <label className="flex items-center gap-2 cursor-pointer">
 <input
 type="checkbox"
 className="rounded border-border text-primary focus:ring-primary/40"
 />
 <span className="text-xs text-muted-foreground">记住我</span>
 </label>
 <button
 type="button"
 onClick={() => {
 setMode('forgot')
 setForgotEmail(email)
 setForgotStep('email')
 }}
 className="text-xs text-primary hover:text-primary/80 font-medium"
 >
 忘记密码？
 </button>
 </div>

 {captchaBlock}

 {/* 提交 */}
 <button
 type="submit"
 disabled={loading || (captchaRequired && !captchaToken)}
 className={`${buttonStyle.primary} w-full py-2.5 disabled:opacity-60 flex items-center justify-center gap-2`}
 >
 {loading && <icons.Loader2 className={`${iconSize.sm} animate-spin`} />}
 {loading ?'登录中...' :'登录'}
 </button>
 </motion.form>
 ) : (
 <motion.form
 key="register"
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 onSubmit={handleRegister}
 className="space-y-4"
 >
 {/* 用户类型选择 — V2 架构：按客户端角色分流 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-2">我是</label>
 <div className="grid grid-cols-2 gap-2">
 {(clientRole === 'provider'
   ? [
       { value:'platform_lawyer', label:'律师', desc:'需实名认证' },
       { value:'institution', label:'律所/机构', desc:'需资质审核' },
     ] as const
   : [
       { value:'individual', label:'个人用户', desc:'法律咨询' },
       { value:'enterprise', label:'企业用户', desc:'企业法务' },
     ] as const
 ).map((opt) => (
 <button
 key={opt.value}
 type="button"
 onClick={() => setRegUserType(opt.value)}
 className={`p-2.5 rounded-lg border text-left transition-colors ${
 regUserType === opt.value
 ?'border-primary bg-primary/5 ring-1 ring-primary/30'
 :'border-border hover:border-primary/40'
 }`}
 >
 <div className={`text-sm font-medium ${regUserType === opt.value ?'text-primary' :'text-foreground'}`}>
 {opt.label}
 </div>
 <div className="text-xs text-muted-foreground">{opt.desc}</div>
 </button>
 ))}
 </div>
 {/* 跨端引导 */}
 <div className="mt-3 text-xs text-muted-foreground text-center">
 {clientRole === 'provider' ? (
   <>不是律师？<button type="button" onClick={() => { window.location.href = '/login' }} className="text-primary hover:underline ml-1">去用户端注册</button></>
 ) : (
   <>您是律师？<button type="button" onClick={() => { window.location.href = '/pro/login' }} className="text-primary hover:underline ml-1">去服务方端注册</button></>
 )}
 </div>
 </div>

 {/* 姓名 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">姓名</label>
 <div className="relative">
 <icons.User className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type="text"
 value={regName}
 onChange={(e) => setRegName(e.target.value)}
 placeholder="请输入姓名"
 className={inputCls}
 />
 </div>
 </div>

 {/* 邮箱 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">邮箱</label>
 <div className="relative">
 <icons.Mail className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type="email"
 value={regEmail}
 onChange={(e) => setRegEmail(e.target.value)}
 placeholder="请输入邮箱地址"
 className={inputCls}
 autoComplete="email"
 />
 </div>
 </div>

 {/* 密码 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">密码</label>
 <div className="relative">
 <icons.Lock className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type={showRegPassword ?'text' :'password'}
 value={regPassword}
 onChange={(e) => setRegPassword(e.target.value)}
 placeholder="至少8位，含大小写字母和数字"
 className={inputCls +' pr-10'}
 autoComplete="new-password"
 />
 <button
 type="button"
 onClick={() => setShowRegPassword(!showRegPassword)}
 className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
 >
 {showRegPassword ? <icons.EyeOff className={iconSize.sm} /> : <icons.Eye className={iconSize.sm} />}
 </button>
 </div>
 {/* 密码强度指示器 */}
 {regPassword && (
 <div className="mt-2 flex items-center gap-2">
 <div className="flex-1 flex gap-1">
 {[1, 2, 3].map((i) => (
 <div
 key={i}
 className={`h-1 flex-1 rounded-full transition-colors ${
 i <= pwdStrength.level ? pwdStrength.color :'bg-muted'
 }`}
 />
 ))}
 </div>
 <span className={`text-xs font-medium ${
 pwdStrength.level === 1 ?'text-destructive' :
 pwdStrength.level === 2 ?'text-warning' :'text-success'
 }`}>
 {pwdStrength.label}
 </span>
 </div>
 )}
 </div>

 {/* 确认密码 */}
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">确认密码</label>
 <div className="relative">
 <icons.Lock className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 type={showRegPassword ?'text' :'password'}
 value={regConfirm}
 onChange={(e) => setRegConfirm(e.target.value)}
 placeholder="请再次输入密码"
 className={`${inputCls}${regConfirm && regConfirm !== regPassword ?' border-destructive/20 focus:ring-destructive/20/40' :''}`}
 autoComplete="new-password"
 />
 {regConfirm && regConfirm !== regPassword && (
 <span className="absolute right-3 top-1/2 -translate-y-1/2 text-destructive">
 <icons.AlertTriangle className={iconSize.sm} />
 </span>
 )}
 {regConfirm && regConfirm === regPassword && regPassword.length >= 8 && (
 <span className="absolute right-3 top-1/2 -translate-y-1/2 text-success">
 <icons.CheckCircle className={iconSize.sm} />
 </span>
 )}
 </div>
 {regConfirm && regConfirm !== regPassword && (
 <p className="text-xs text-destructive mt-1">两次密码不一致</p>
 )}
 </div>

 {/* 服务协议 */}
 <label className="flex items-start gap-2 cursor-pointer">
 <input
 type="checkbox"
 checked={agreedTerms}
 onChange={(e) => setAgreedTerms(e.target.checked)}
 className="mt-0.5 rounded border-border text-primary focus:ring-primary/40"
 />
 <span className="text-xs text-muted-foreground leading-relaxed">
 我已阅读并同意{''}
 <a href="#" className="text-primary hover:underline">
 《服务协议》
 </a>{''}
 和{''}
 <a href="#" className="text-primary hover:underline">
 《隐私政策》
 </a>
 </span>
 </label>

 {captchaBlock}

 {/* 提交 */}
 <button
 type="submit"
 disabled={loading || (captchaRequired && !captchaToken)}
 className={`${buttonStyle.primary} w-full py-2.5 disabled:opacity-60 flex items-center justify-center gap-2`}
 >
 {loading && <icons.Loader2 className={`${iconSize.sm} animate-spin`} />}
 {loading ?'注册中...' :'注册'}
 </button>
 </motion.form>
 )}
 </AnimatePresence>

 {/* 第三方登录 — 根据后台功能开关动态显示 */}
 {(features.oauth_wechat_enabled || features.oauth_alipay_enabled) && (<><div className="relative my-6">
 <div className="absolute inset-0 flex items-center">
 <div className="w-full border-t border-border" />
 </div>
 <div className="relative flex justify-center">
 <span className="bg-background px-3 text-xs text-muted-foreground">
 或使用以下方式登录
 </span>
 </div>
 </div>

 {/* 第三方登录按钮 */}
 <div className="grid grid-cols-2 gap-3">
 {features.oauth_wechat_enabled && (
 <button
 onClick={() => handleOAuth('wechat')}
 className={`${buttonStyle.ghost} flex items-center justify-center gap-2 py-2.5 border border-border text-success hover:bg-success/5 hover:text-success`}
 >
 <svg className={iconSize.md} viewBox="0 0 24 24" fill="currentColor">
 <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm3.905 4.08c-1.88-.088-3.644.474-5.013 1.612-1.446 1.2-2.274 2.947-2.274 4.79 0 .378.042.748.12 1.112.453 2.107 1.907 3.818 3.924 4.756a.44.44 0 0 1 .166.502l-.233.872a.606.606 0 0 0-.035.16c0 .121.098.222.218.222a.24.24 0 0 0 .126-.04l1.432-.838a.65.65 0 0 1 .54-.073c.724.18 1.473.27 2.222.27 3.695 0 6.673-2.73 6.822-6.206.02-.29.033-.574.033-.864 0-3.428-3.576-6.237-8.048-6.275zm-2.19 3.428c.483 0 .874.397.874.886a.88.88 0 0 1-.874.886.88.88 0 0 1-.874-.886c0-.489.39-.886.874-.886zm4.38 0c.483 0 .874.397.874.886a.88.88 0 0 1-.874.886.88.88 0 0 1-.874-.886c0-.489.39-.886.874-.886z" />
 </svg>
 微信登录
 </button>
 )}
 {features.oauth_alipay_enabled && (
 <button
 onClick={() => handleOAuth('alipay')}
 className={`${buttonStyle.ghost} flex items-center justify-center gap-2 py-2.5 border border-border text-info hover:bg-info/5 hover:text-info`}
 >
 <svg className={iconSize.md} viewBox="0 0 24 24" fill="currentColor">
 <path d="M21.422 15.358c-1.573-.537-3.282-1.159-3.282-1.159s.908-2.059 1.178-3.483c.27-1.424.162-2.485-.432-2.98-.594-.494-1.314-.243-1.908.269-.594.512-1.575 1.871-2.25 3.06a23.819 23.819 0 0 1-5.283-1.455c1.581-2.898 2.55-5.864 2.55-5.864H7.872V2.36h4.895V1H7.872V0H6.78v1H1.943v1.36H6.78v1.386H3.116v1.36h7.443s-.733 2.234-2.037 4.582c-2.258-.82-4.448-1.348-5.61-1.05-1.02.261-1.648.868-1.92 1.588-.82 2.17.905 4.323 3.6 4.323 1.806 0 3.532-1.087 4.895-2.8.902.427 1.893.82 2.957 1.182-.61.77-1.208 1.596-1.766 2.467C8.76 18.4 6.273 21 3.612 21c-.6 0-1.122-.164-1.5-.476 0 0-.48-.388-.6-1.17 0 0-.012.025.312.49.324.466.894.702 1.62.702 1.99 0 4.185-1.754 5.82-3.943.546-.731 1.061-1.51 1.545-2.319 2.273.676 4.89 1.293 4.89 1.293S13.8 18.6 13.8 20.16c0 1.56 1.11 2.04 1.74 2.16.63.12 2.4.12 3.36-.96.96-1.08.84-2.4.84-2.4s.024.18-.144.588c-.168.408-.528.9-1.08 1.152-.552.252-1.284.12-1.284.12s-.36-.06-.36-.48c0-.42.816-1.932 1.884-3.504.564-.828 1.152-1.572 1.74-2.232 1.344.432 2.172.636 2.172.636l.78-1.884zM5.493 13.83c-1.962 0-2.868-1.362-2.484-2.598.384-1.236 1.566-1.65 2.424-1.476.858.174 2.502.696 3.858 1.266-1.134 1.698-2.448 2.808-3.798 2.808z" />
 </svg>
 支付宝登录
 </button>
 )}
 </div></>)}

 {/* 开发模式快捷登录 — 已隐藏 */}
 </motion.div>
 </div>
 </div>
 )
}
