const RECOVERY_KEY = '__dynamic_import_recovery__'
const RECOVERY_TTL_MS = 30_000

let hasBoundRecovery = false

function getRecoveryPayload() {
  try {
    const value = window.sessionStorage.getItem(RECOVERY_KEY)
    return value ? (JSON.parse(value) as { path: string; ts: number }) : null
  } catch {
    return null
  }
}

function shouldRecover() {
  const payload = getRecoveryPayload()
  if (!payload) return true
  if (payload.path !== window.location.pathname) return true
  return Date.now() - payload.ts > RECOVERY_TTL_MS
}

function markRecovery() {
  window.sessionStorage.setItem(
    RECOVERY_KEY,
    JSON.stringify({
      path: window.location.pathname,
      ts: Date.now(),
    }),
  )
}

function getErrorMessage(reason: unknown) {
  if (typeof reason === 'string') return reason
  if (reason instanceof Error) return reason.message
  if (typeof reason === 'object' && reason && 'message' in reason && typeof reason.message === 'string') {
    return reason.message
  }
  return ''
}

function isDynamicImportFailure(reason: unknown) {
  const message = getErrorMessage(reason)
  return (
    /Failed to fetch dynamically imported module/i.test(message) ||
    /Importing a module script failed/i.test(message) ||
    /error loading dynamically imported module/i.test(message)
  )
}

function recover() {
  if (!shouldRecover()) return
  markRecovery()
  window.location.reload()
}

export function setupDynamicImportRecovery() {
  if (typeof window === 'undefined' || hasBoundRecovery) return

  hasBoundRecovery = true

  window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault()
    recover()
  })

  window.addEventListener('unhandledrejection', (event) => {
    if (!isDynamicImportFailure(event.reason)) return
    event.preventDefault()
    recover()
  })

  window.addEventListener('error', (event) => {
    if (!isDynamicImportFailure((event as ErrorEvent).error ?? event.message)) return
    event.preventDefault()
    recover()
  })
}
