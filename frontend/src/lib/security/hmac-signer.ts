/**
 * HMAC 请求签名器
 *
 * 使用 Web Crypto API 为每个 API 请求生成 HMAC-SHA256 签名。
 * 签名算法: HMAC-SHA256(key, timestamp + "\n" + nonce + "\n" + method + "\n" + path + "\n" + SHA256(body))
 */

let signingKey: string | null = null
let hmacEnabled = false

/** 设置签名密钥（登录后调用或从 security-config 获取） */
export function setSigningKey(key: string | null) {
  signingKey = key
}

export function setHmacEnabled(enabled: boolean) {
  hmacEnabled = enabled
}

export function isHmacEnabled(): boolean {
  return hmacEnabled && !!signingKey
}

/** 生成 16 字节随机 hex nonce */
function generateNonce(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

/** SHA-256 哈希 */
async function sha256(data: string): Promise<string> {
  const encoded = new TextEncoder().encode(data)
  const hashBuffer = await crypto.subtle.digest('SHA-256', encoded)
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

/** HMAC-SHA256 签名并返回 Base64 */
async function hmacSign(key: string, message: string): Promise<string> {
  const keyData = new TextEncoder().encode(key)
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const msgData = new TextEncoder().encode(message)
  const sigBuffer = await crypto.subtle.sign('HMAC', cryptoKey, msgData)
  // Base64 encode
  const bytes = new Uint8Array(sigBuffer)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary)
}

/**
 * 为请求生成签名头
 * @returns 签名头对象，如果未启用则返回空对象
 */
export async function signRequest(
  method: string,
  path: string,
  body?: string,
): Promise<Record<string, string>> {
  if (!hmacEnabled || !signingKey) return {}

  try {
    const timestamp = Math.floor(Date.now() / 1000).toString()
    const nonce = generateNonce()
    const bodyHash = await sha256(body || '')
    const payload = `${timestamp}\n${nonce}\n${method}\n${path}\n${bodyHash}`
    const signature = await hmacSign(signingKey, payload)

    return {
      'X-Request-Timestamp': timestamp,
      'X-Request-Nonce': nonce,
      'X-Request-Signature': signature,
    }
  } catch {
    // 签名失败静默降级
    return {}
  }
}
