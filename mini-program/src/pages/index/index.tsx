import { useState, useEffect } from 'react'
import { View, Text, Input, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
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

const fallbackNews: NewsItem[] = [
  { id: '1', title: '最高法发布2026年度十大知识产权案例', date: '2026-03-25', tag: '知产' },
  { id: '2', title: '新《公司法》实施细则解读：注册资本五年实缴制', date: '2026-03-24', tag: '公司法' },
  { id: '3', title: '劳动合同法修订草案：灵活用工新规定', date: '2026-03-22', tag: '劳动法' },
  { id: '4', title: '数据安全法合规指南：企业必须知道的十件事', date: '2026-03-20', tag: '数据安全' },
]

export default function Index() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [newsLoading, setNewsLoading] = useState(true)

  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    setNewsLoading(true)
    try {
      const data = await api.get<NewsItem[]>('/news/latest')
      setNewsItems(data && data.length > 0 ? data : fallbackNews)
    } catch {
      // API 不可用时使用 mock 数据
      setNewsItems(fallbackNews)
    } finally {
      setNewsLoading(false)
    }
  }

  const handleSearch = () => {
    Taro.navigateTo({ url: '/pages/chat/index' })
  }

  const handleQuickAction = (action: typeof quickActions[0]) => {
    if (action.path) {
      // chat 页面是 tabBar 页面则用 switchTab，否则 navigateTo
      if (action.path.includes('/pages/chat/')) {
        Taro.switchTab({ url: action.path }).catch(() => {
          // switchTab 失败则尝试 navigateTo（可能不是 tabBar 页面）
          Taro.navigateTo({ url: action.path })
        })
      } else {
        Taro.navigateTo({ url: action.path })
      }
    } else {
      Taro.showToast({ title: '功能开发中', icon: 'none' })
    }
  }

  const handleNewsClick = (item: NewsItem) => {
    Taro.navigateTo({ url: `/pages/chat/index?question=${encodeURIComponent(item.title)}` })
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
