import { useState, useRef } from 'react'
import { View, Text, ScrollView, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { api } from '../../services/api'
import './index.scss'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const welcomeMessage: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: '您好！我是安心法务AI助手，可以为您提供法律咨询、合同审查、法规查询等服务。请问有什么可以帮您？',
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const conversationId = useRef<string>('')

  const handleSend = async () => {
    const content = inputValue.trim()
    if (!content || loading) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    }

    setMessages((prev) => [...prev, userMsg])
    setInputValue('')
    setLoading(true)

    try {
      const data = await api.post<{
        reply: string
        conversation_id?: string
      }>('/chat/send', {
        message: content,
        conversation_id: conversationId.current || undefined,
      })

      if (data.conversation_id) {
        conversationId.current = data.conversation_id
      }

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: data.reply,
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch (e: any) {
      // API 不可用时降级为提示
      const fallbackMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: '抱歉，AI 服务暂时不可用，请稍后重试。如需紧急法律帮助，请通过"联系律师"功能直接对接专业律师。',
      }
      setMessages((prev) => [...prev, fallbackMsg])
      Taro.showToast({ title: '网络异常，请稍后重试', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const lastMsgId = messages[messages.length - 1]?.id

  return (
    <View className='chat-page'>
      <ScrollView
        className='message-list'
        scrollY
        scrollWithAnimation
        scrollIntoView={loading ? 'typing-indicator' : `msg-${lastMsgId}`}
      >
        {messages.map((msg) => (
          <View
            key={msg.id}
            id={`msg-${msg.id}`}
            className={`message-item ${msg.role}`}
          >
            <View className='avatar'>
              <Text>{msg.role === 'assistant' ? '🤖' : '👤'}</Text>
            </View>
            <View className='bubble'>
              <Text className='bubble-text'>{msg.content}</Text>
            </View>
          </View>
        ))}
        {loading && (
          <View id='typing-indicator' className='message-item assistant'>
            <View className='avatar'>
              <Text>🤖</Text>
            </View>
            <View className='bubble typing'>
              <Text className='bubble-text'>思考中...</Text>
            </View>
          </View>
        )}
      </ScrollView>

      <View className='input-bar'>
        <Input
          className='chat-input'
          placeholder='输入您的法律问题...'
          value={inputValue}
          onInput={(e) => setInputValue(e.detail.value)}
          onConfirm={handleSend}
          confirmType='send'
          disabled={loading}
        />
        <View
          className={`send-btn ${loading ? 'disabled' : ''}`}
          onClick={handleSend}
        >
          <Text className='send-text'>{loading ? '...' : '发送'}</Text>
        </View>
      </View>
    </View>
  )
}
