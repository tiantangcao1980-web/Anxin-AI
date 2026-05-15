/**
 * 隐私守门核心模块单测
 *
 * 覆盖 commits 0949c127 / 9e3ed74a / a678d354 的 fail-closed 契约：
 *   - assertMiniProgramDataNetworkAllowed 在敏感模式 throw
 *   - assertMiniProgramDataNetworkAllowed 在 standard 通过
 *   - getStoredPrivacyMode 默认回退 standard
 *   - MiniProgramPrivacyNetworkBlockedError 携带 mode
 */

import { afterEach, describe, expect, it } from 'vitest'
import { __storage } from '../../../tests/stubs/taro'
import {
  assertMiniProgramDataNetworkAllowed,
  getStoredPrivacyMode,
  isMiniProgramPrivacyNetworkBlockedError,
  MiniProgramPrivacyNetworkBlockedError,
  setStoredPrivacyMode,
} from './index'

afterEach(() => {
  __storage.reset()
})

describe('privacy module · fail-closed 契约', () => {
  it('standard 模式：assert 通过，不 throw', () => {
    setStoredPrivacyMode('standard')
    expect(() => assertMiniProgramDataNetworkAllowed()).not.toThrow()
  })

  it('local 模式：assert throw MiniProgramPrivacyNetworkBlockedError', () => {
    setStoredPrivacyMode('local')
    expect(() => assertMiniProgramDataNetworkAllowed()).toThrow(
      MiniProgramPrivacyNetworkBlockedError,
    )
  })

  it('top-secret 模式：assert throw MiniProgramPrivacyNetworkBlockedError', () => {
    setStoredPrivacyMode('top-secret')
    expect(() => assertMiniProgramDataNetworkAllowed()).toThrow(
      MiniProgramPrivacyNetworkBlockedError,
    )
  })

  it('错误携带 mode 字段，便于上层做差异化降级', () => {
    setStoredPrivacyMode('local')
    try {
      assertMiniProgramDataNetworkAllowed()
      throw new Error('should have thrown')
    } catch (err) {
      expect(isMiniProgramPrivacyNetworkBlockedError(err)).toBe(true)
      if (isMiniProgramPrivacyNetworkBlockedError(err)) {
        expect(err.mode).toBe('local')
      }
    }
  })

  it('storage 未写入时回退 standard（fail-open default — 仅当用户从未切过）', () => {
    expect(getStoredPrivacyMode()).toBe('standard')
    expect(() => assertMiniProgramDataNetworkAllowed()).not.toThrow()
  })

  it('storage 写入非法值时回退 standard（防御性）', () => {
    __storage.set('anxin:privacy_mode', 'unknown-mode')
    expect(getStoredPrivacyMode()).toBe('standard')
  })

  it('mode 参数显式传入时覆盖 storage 读取', () => {
    setStoredPrivacyMode('standard')
    expect(() => assertMiniProgramDataNetworkAllowed('local')).toThrow(
      MiniProgramPrivacyNetworkBlockedError,
    )
  })

  it('setStoredPrivacyMode 持久化到 storage', () => {
    setStoredPrivacyMode('top-secret')
    expect(getStoredPrivacyMode()).toBe('top-secret')
  })

  it('isMiniProgramPrivacyNetworkBlockedError 仅识别正确类型', () => {
    expect(isMiniProgramPrivacyNetworkBlockedError(new Error('other'))).toBe(false)
    expect(isMiniProgramPrivacyNetworkBlockedError('string')).toBe(false)
    expect(isMiniProgramPrivacyNetworkBlockedError(null)).toBe(false)
    expect(
      isMiniProgramPrivacyNetworkBlockedError(
        new MiniProgramPrivacyNetworkBlockedError('local'),
      ),
    ).toBe(true)
  })
})
