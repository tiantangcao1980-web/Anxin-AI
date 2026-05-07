import { useState, useEffect } from 'react'
import { View, Text, Input } from '@tarojs/components'
import Taro, { usePullDownRefresh } from '@tarojs/taro'
import { api } from '../../services/api'
import './index.scss'

const quickActions = [
  { icon: '🤖', title: 'AI法律咨询', desc: '智能问答', path: '/pages/chat/index' },
  { icon: '📄', title: '合同审查', desc: '风险识别', path: '' },
  { icon: '👨‍⚖️', title: '找律师', desc: '专业匹配', path: '' },
  { icon: '✅', title: '合规自检', desc: '快速筛查', path: '' },
]

interface NewsItem {
  id: string
  title: string
  date: string
  tag: string
}

export default function Index() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [newsLoading, setNewsLoading] = useState(true)
  const [newsError, setNewsError] = useState('')

  useEffect(() => {
    loadNews()
  }, [])

  // 下拉刷新
  usePullDownRefresh(() => {
    loadNews().finally(() => {
      Taro.stopPullDownRefresh()
    })
  })

  const loadNews = async () => {
    setNewsLoading(true)
    try {
      const data = await api.get<NewsItem[]>('/news/latest')
      const items = Array.isArray(data) ? data : []
      setNewsItems(items)
      setNewsError(items.length > 0 ? '' : '暂无资讯，下拉刷新重试')
    } catch (error) {
      console.warn('资讯加载失败', error)
      setNewsItems([])
      setNewsError('资讯加载失败，下拉刷新重试')
    } finally {
      setNewsLoading(false)
    }
  }

  const handleSearch = () => {
    Taro.switchTab({ url: '/pages/chat/index' })
  }

  // tabBar 页面路径列表，用于判断跳转方式
  const tabBarPaths = ['/pages/index/index', '/pages/chat/index', '/pages/profile/index']

  const handleQuickAction = (action: typeof quickActions[0]) => {
    if (action.path) {
      if (tabBarPaths.includes(action.path)) {
        Taro.switchTab({ url: action.path })
      } else {
        Taro.navigateTo({ url: action.path })
      }
    } else {
      Taro.showToast({ title: '功能开发中', icon: 'none' })
    }
  }

  const handleNewsClick = (item: NewsItem) => {
    // tabBar 页不支持 navigateTo 传参，通过 storage 中转
    Taro.setStorageSync('pending_question', item.title)
    Taro.switchTab({ url: '/pages/chat/index' })
  }

  return (
    <View className='index-page'>
      {/* 搜索栏 */}
      <View className='search-bar' onClick={handleSearch}>
        <View className='search-input-wrapper'>
          <Text className='search-icon'>🔍</Text>
          <Input
            className='search-input'
            placeholder='搜索法律问题、法规、案例...'
            disabled
          />
        </View>
      </View>

      {/* 快捷功能入口 */}
      <View className='quick-actions'>
        {quickActions.map((action, idx) => (
          <View
            key={idx}
            className='action-item'
            onClick={() => handleQuickAction(action)}
          >
            <View className='action-icon'>{action.icon}</View>
            <Text className='action-title'>{action.title}</Text>
            <Text className='action-desc'>{action.desc}</Text>
          </View>
        ))}
      </View>

      {/* 热门法律资讯 */}
      <View className='news-section'>
        <View className='section-header'>
          <Text className='section-title'>热门法律资讯</Text>
          <Text className='section-more'>查看更多 &gt;</Text>
        </View>
        <View className='news-list'>
          {newsLoading ? (
            // 加载占位
            [1, 2, 3].map((i) => (
              <View key={i} className='news-item news-skeleton'>
                <View className='news-content'>
                  <View className='skeleton-tag' />
                  <View className='skeleton-title' />
                  <View className='skeleton-date' />
                </View>
              </View>
            ))
          ) : newsItems.length === 0 ? (
            <View className='news-empty'>
              <Text className='news-empty-title'>暂无资讯</Text>
              <Text className='news-empty-desc'>{newsError || '下拉刷新重试'}</Text>
            </View>
          ) : (
            newsItems.map((item) => (
              <View
                key={item.id}
                className='news-item'
                onClick={() => handleNewsClick(item)}
              >
                <View className='news-content'>
                  <Text className='news-tag'>{item.tag}</Text>
                  <Text className='news-title'>{item.title}</Text>
                  <Text className='news-date'>{item.date}</Text>
                </View>
              </View>
            ))
          )}
        </View>
      </View>
    </View>
  )
}
