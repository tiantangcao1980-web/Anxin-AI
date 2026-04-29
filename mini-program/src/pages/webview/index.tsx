// -*- coding: utf-8 -*-
/**
 * 通用 H5 跳转壳
 *
 * 进入参数：
 *   - url: 目标 H5 URL（必须在 mp 后台「业务域名」白名单里）
 *   - title: 导航栏标题（可选）
 *
 * 用途：用户协议 / 隐私政策 / OAuth 第三方授权回跳。
 *
 * 注意：微信小程序 web-view 默认仅个人主体不允许使用，本壳页面适合企业主体。
 */

import { useEffect, useState } from 'react'
import { View, WebView, Text } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import './index.scss'

export default function WebviewPage() {
  const router = useRouter()
  const [src, setSrc] = useState('')

  useEffect(() => {
    const params = router.params || {}
    const url = decodeURIComponent(String(params.url || ''))
    const title = decodeURIComponent(String(params.title || '加载中'))
    if (title) {
      Taro.setNavigationBarTitle({ title })
    }
    if (url && /^https?:\/\//.test(url)) {
      setSrc(url)
    }
  }, [router.params])

  if (!src) {
    return (
      <View className='webview-empty'>
        <Text className='webview-empty__emoji'>🌐</Text>
        <Text className='webview-empty__title'>未提供有效 URL</Text>
        <Text className='webview-empty__sub'>
          请通过 ?url= 参数指定要打开的 H5 链接
        </Text>
      </View>
    )
  }

  return <WebView src={src} />
}
