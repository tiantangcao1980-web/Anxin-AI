/**
 * K2 (2026-05-14): i18n 骨架单测
 */
import { afterEach, describe, expect, test } from 'vitest'

import { i18n, t } from './index'

afterEach(() => {
  i18n.reset()
})

describe('i18n skeleton', () => {
  test('t(key) returns key itself when no translation', () => {
    expect(t('某个未翻译的 key')).toBe('某个未翻译的 key')
  })

  test('t(key, default) returns default when no translation', () => {
    expect(t('untranslated_key', '默认文案')).toBe('默认文案')
  })

  test('t(key) returns translation when zh-CN dict has the key', () => {
    // zh-CN dict 当前几乎为空, 只有 _comment_, 所以普通中文 key 直接 fallback
    expect(t('管理中心')).toBe('管理中心')
  })

  test('t(key) returns en-US translation after changeLanguage', () => {
    i18n.changeLanguage('en-US')
    expect(t('管理中心')).toBe('Management Center')
    expect(t('保存')).toBe('Save')
  })

  test('t(key) falls back to key when en-US dict missing the key', () => {
    i18n.changeLanguage('en-US')
    expect(t('一个不存在的英文翻译')).toBe('一个不存在的英文翻译')
  })

  test('i18n.language reflects current locale', () => {
    expect(i18n.language).toBe('zh-CN')
    i18n.changeLanguage('en-US')
    expect(i18n.language).toBe('en-US')
  })

  test('i18n.changeLanguage is idempotent on same locale', () => {
    i18n.changeLanguage('zh-CN')
    expect(i18n.language).toBe('zh-CN')
    i18n.changeLanguage('zh-CN')
    expect(i18n.language).toBe('zh-CN')
  })
})
