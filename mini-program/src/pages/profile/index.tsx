import { useState } from 'react'
import { View, Text, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { api } from '../../services/api'
import './index.scss'

const menuItems = [
  { icon: '💬', title: '我的咨询', desc: '查看咨询记录', path: '/pages/chat/index' },
  { icon: '📄', title: '我的合同', desc: '合同管理', path: '' },
  { icon: '📁', title: '我的案件', desc: '案件进度跟踪', path: '' },
  { icon: '👨‍⚖️', title: '联系律师', desc: '专业律师对接', path: '' },
]

interface UserInfo {
  nickname: string
  avatar_url: string
}

export default function Profile() {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => !!Taro.getStorageSync('token'))
  const [userName, setUserName] = useState<string>(() => {
    try {
      const info = Taro.getStorageSync('user_info')
      return info?.nickname || '未登录'
    } catch {
      return '未登录'
    }
  })
  const [avatarUrl, setAvatarUrl] = useState<string>('')

  // 每次页面显示时同步登录状态（从其他页面返回时）
  useDidShow(() => {
    const token = Taro.getStorageSync('token')
    setIsLoggedIn(!!token)
    if (token) {
      try {
        const info = Taro.getStorageSync('user_info')
        if (info?.nickname) setUserName(info.nickname)
        if (info?.avatar_url) setAvatarUrl(info.avatar_url)
      } catch {}
    } else {
      setUserName('未登录')
      setAvatarUrl('')
    }
  })

  const handleLogin = async () => {
    try {
      const loginRes = await Taro.login()
      if (!loginRes.code) {
        Taro.showToast({ title: '微信登录失败', icon: 'none' })
        return
      }

      try {
        // 尝试调用后端微信登录接口
        const data = await api.post<{
          access_token: string
          refresh_token?: string
          user: UserInfo
        }>('/auth/wechat-login', { code: loginRes.code })

        Taro.setStorageSync('token', data.access_token)
        if (data.refresh_token) {
          Taro.setStorageSync('refresh_token', data.refresh_token)
        }
        Taro.setStorageSync('user_info', data.user)
        setIsLoggedIn(true)
        setUserName(data.user.nickname || '微信用户')
        setAvatarUrl(data.user.avatar_url || '')
        Taro.showToast({ title: '登录成功', icon: 'success' })
      } catch {
        // 后端接口不可用时，降级为 mock 登录
        const mockUser: UserInfo = { nickname: '安心用户', avatar_url: '' }
        Taro.setStorageSync('token', `mock_token_${Date.now()}`)
        Taro.setStorageSync('user_info', mockUser)
        setIsLoggedIn(true)
        setUserName(mockUser.nickname)
        setAvatarUrl('')
        Taro.showToast({ title: '登录成功（体验模式）', icon: 'success' })
      }
    } catch (e: any) {
      Taro.showToast({ title: e.message || '登录失败', icon: 'none' })
    }
  }

  const handleLogout = () => {
    Taro.showModal({
      title: '确认退出',
      content: '退出后需要重新登录',
      success: (res) => {
        if (res.confirm) {
          Taro.removeStorageSync('token')
          Taro.removeStorageSync('refresh_token')
          Taro.removeStorageSync('user_info')
          setIsLoggedIn(false)
          setUserName('未登录')
          setAvatarUrl('')
          Taro.showToast({ title: '已退出登录', icon: 'none' })
        }
      },
    })
  }

  // tabBar 页面路径列表
  const tabBarPaths = ['/pages/index/index', '/pages/chat/index', '/pages/profile/index']

  const handleMenuClick = (item: typeof menuItems[0]) => {
    if (!isLoggedIn) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    if (item.path) {
      if (tabBarPaths.includes(item.path)) {
        Taro.switchTab({ url: item.path })
      } else {
        Taro.navigateTo({ url: item.path })
      }
    } else {
      Taro.showToast({ title: `${item.title} - 功能开发中`, icon: 'none' })
    }
  }

  const handleSettings = () => {
    Taro.showToast({ title: '设置功能开发中', icon: 'none' })
  }

  return (
    <View className='profile-page'>
      {/* 用户信息区 */}
      <View
        className='user-header'
        onClick={isLoggedIn ? handleLogout : handleLogin}
      >
        <View className='avatar-wrapper'>
          {avatarUrl ? (
            <Image className='avatar-image' src={avatarUrl} mode='aspectFill' />
          ) : (
            <View className='avatar-placeholder'>
              <Text className='avatar-icon'>👤</Text>
            </View>
          )}
        </View>
        <View className='user-info'>
          <Text className='user-name'>
            {isLoggedIn ? userName : '点击登录'}
          </Text>
          <Text className='user-desc'>
            {isLoggedIn ? '点击可退出登录' : '登录后享受完整法律服务'}
          </Text>
        </View>
        <Text className='arrow'>&gt;</Text>
      </View>

      {/* 功能列表 */}
      <View className='menu-section'>
        {menuItems.map((item, idx) => (
          <View
            key={idx}
            className='menu-item'
            onClick={() => handleMenuClick(item)}
          >
            <View className='menu-left'>
              <Text className='menu-icon'>{item.icon}</Text>
              <View className='menu-text'>
                <Text className='menu-title'>{item.title}</Text>
                <Text className='menu-desc'>{item.desc}</Text>
              </View>
            </View>
            <Text className='menu-arrow'>&gt;</Text>
          </View>
        ))}
      </View>

      {/* 设置入口 */}
      <View className='menu-section'>
        <View className='menu-item' onClick={handleSettings}>
          <View className='menu-left'>
            <Text className='menu-icon'>⚙️</Text>
            <View className='menu-text'>
              <Text className='menu-title'>设置</Text>
              <Text className='menu-desc'>账号安全、隐私、关于</Text>
            </View>
          </View>
          <Text className='menu-arrow'>&gt;</Text>
        </View>
      </View>
    </View>
  )
}
