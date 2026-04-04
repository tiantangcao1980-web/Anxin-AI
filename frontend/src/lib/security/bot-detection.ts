/**
 * 轻量 Bot 信号采集（Phase 2）
 *
 * 自实现，不引入额外依赖。检测常见的自动化工具特征。
 * 通过 X-Bot-Signals 请求头（Base64 JSON）发送给后端。
 */

export interface BotSignals {
  /** navigator.webdriver 为 true（Selenium/Puppeteer 特征） */
  webdriver: boolean
  /** navigator.languages 为空（无头浏览器） */
  noLanguages: boolean
  /** navigator.plugins 为空（无头浏览器） */
  noPlugins: boolean
  /** window.outerWidth/Height 为 0（不可见窗口） */
  zeroSize: boolean
  /** 有 chrome 对象但无 chrome.runtime（无头 Chrome） */
  headlessChrome: boolean
  /** 采集时间戳 */
  ts: number
}

let cachedSignals: BotSignals | null = null

/** 采集 Bot 信号（仅执行一次） */
export function collectBotSignals(): BotSignals {
  if (cachedSignals) return cachedSignals

  const nav = navigator as unknown as Record<string, unknown>

  cachedSignals = {
    webdriver: !!nav.webdriver,
    noLanguages: !navigator.languages || navigator.languages.length === 0,
    noPlugins: !navigator.plugins || navigator.plugins.length === 0,
    zeroSize: window.outerWidth === 0 || window.outerHeight === 0,
    headlessChrome:
      'chrome' in window &&
      !(window as Record<string, unknown>).chrome?.hasOwnProperty?.('runtime'),
    ts: Date.now(),
  }

  return cachedSignals
}

/** 获取 Base64 编码的信号字符串（用于请求头） */
export function getBotSignalsHeader(): string | null {
  const signals = collectBotSignals()
  try {
    return btoa(JSON.stringify(signals))
  } catch {
    return null
  }
}
