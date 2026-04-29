// -*- coding: utf-8 -*-
/**
 * 登录页 —— 微信小程序授权登录入口
 *
 * 主流程：wx.login() → POST /auth/oauth/wechat/callback → 持久化 token → 跳 home
 * 备用：邮箱密码登录（开发体验，方便联调）
 */

import { useState } from 'react'
import { View, Text, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'

import { Screen } from '../../components/Layout'
import { wechatMiniprogramLogin, passwordLogin } from '../../utils/api/auth'
import { ApiError } from '../../utils/api/client'
import './index.scss'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [showEmail, setShowEmail] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [agreed, setAgreed] = useState(false)

  async function handleWechatLogin() {
    if (!agreed) {
      Taro.showToast({ title: '请先勾选用户协议', icon: 'none' })
      return
    }
    setLoading(true)
    try {
      await wechatMiniprogramLogin()
      Taro.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => Taro.reLaunch({ url: '/pages/index/index' }), 600)
    } catch (e) {
      const err = e as ApiError | Error
      const msg =
        err instanceof ApiError ? err.message : err?.message || '登录失败'
      Taro.showModal({
        title: '微信登录失败',
        content: `${msg}\n\n可改用邮箱密码登录（开发体验）`,
        confirmText: '邮箱登录',
        success: (r) => {
          if (r.confirm) setShowEmail(true)
        },
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleEmailLogin() {
    if (!agreed) {
      Taro.showToast({ title: '请先勾选用户协议', icon: 'none' })
      return
    }
    if (!email || !password) {
      Taro.showToast({ title: '请填写邮箱和密码', icon: 'none' })
      return
    }
    setLoading(true)
    try {
      await passwordLogin({ email, password })
      Taro.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => Taro.reLaunch({ url: '/pages/index/index' }), 600)
    } catch (e) {
      const err = e as ApiError | Error
      const msg =
        err instanceof ApiError ? err.message : err?.message || '登录失败'
      Taro.showToast({ title: msg, icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Screen padded={false} backgroundColor='#FFFFFF'>
      <View className='login-hero'>
        <View className='login-hero__logo'>
          <Text className='login-hero__logo-emoji'>🤖</Text>
        </View>
        <Text className='login-hero__title'>安心智能助手</Text>
        <Text className='login-hero__sub'>
          法 / 税 / 财 / 管理 + 调研 + 获客 + 内容 + 跨境
        </Text>
      </View>

      <View className='login-actions'>
        {!showEmail ? (
          <>
            <View
              className={`login-btn login-btn--primary ${loading ? 'login-btn--loading' : ''}`}
              onClick={handleWechatLogin}
            >
              <Text className='login-btn__text'>
                {loading ? '登录中…' : '微信一键登录'}
              </Text>
            </View>
            <View
              className='login-btn login-btn--ghost'
              onClick={() => setShowEmail(true)}
            >
              <Text className='login-btn__text login-btn__text--ghost'>
                邮箱密码登录（开发模式）
              </Text>
            </View>
          </>
        ) : (
          <View className='login-form'>
            <Input
              className='login-form__input'
              placeholder='邮箱'
              value={email}
              onInput={(e) => setEmail(e.detail.value)}
              type='text'
            />
            <Input
              className='login-form__input'
              placeholder='密码'
              value={password}
              onInput={(e) => setPassword(e.detail.value)}
              password
            />
            <View
              className={`login-btn login-btn--primary ${loading ? 'login-btn--loading' : ''}`}
              onClick={handleEmailLogin}
            >
              <Text className='login-btn__text'>
                {loading ? '登录中…' : '登录'}
              </Text>
            </View>
            <View
              className='login-btn login-btn--ghost'
              onClick={() => setShowEmail(false)}
            >
              <Text className='login-btn__text login-btn__text--ghost'>
                返回微信登录
              </Text>
            </View>
          </View>
        )}
      </View>

      <View className='login-agree'>
        <View
          className={`login-agree__check ${agreed ? 'login-agree__check--on' : ''}`}
          onClick={() => setAgreed((v) => !v)}
        />
        <Text className='login-agree__text'>
          我已阅读并同意
          <Text className='login-agree__link'> 用户协议 </Text>
          和
          <Text className='login-agree__link'> 隐私政策 </Text>
        </Text>
      </View>
    </Screen>
  )
}
