/**
 * P21-C 智能体对话页（核心）
 *
 * - 顶部 NavBar：persona name + emoji + [详情] 按钮
 * - 消息流（ScrollView）：用户右对齐琥珀色 / persona 左对齐灰色 + emoji avatar
 * - 假流式：每 50ms 增加一个字符（mock，小程序无 SSE）
 * - 输入区：文本框 + 发送 + 上方 capability chips（点击插入提示词）
 * - "+" 按钮 ActionSheet（拍照 / 相册 / 文件 / 派远端）
 * - 底部 toolbar：清空 / 历史 / 设置
 * - 长按消息 ActionSheet（复制 / 转发 / 删除 / 重新生成）
 * - 模式开关：本地 / 云端（顶部右上角）
 */

import { useEffect, useRef, useState } from 'react'
import { View, Text, ScrollView, Input } from '@tarojs/components'
import Taro, { useRouter, useDidHide } from '@tarojs/taro'

import {
  chatWithPersona,
  fakeStream,
  getPersona,
  type FakeStreamHandle,
  type Persona,
} from '../_mock/index'

import './index.scss'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** 流式中：内容会实时增长 */
  streaming?: boolean
}

type RunMode = 'local' | 'cloud'

export default function PersonaChat() {
  const router = useRouter()
  const personaId = (router.params.personaId as string) || 'anxin_assistant'

  const [persona, setPersona] = useState<Persona | undefined>()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [pending, setPending] = useState(false)
  const [scrollIntoViewId, setScrollIntoViewId] = useState('')
  const [runMode, setRunMode] = useState<RunMode>('local')
  const [showCapChips, setShowCapChips] = useState(true)

  const streamRef = useRef<FakeStreamHandle | null>(null)
  const lastUserPromptRef = useRef<string>('')

  // 加载 persona + 欢迎消息
  useEffect(() => {
    let cancelled = false
    getPersona(personaId).then((p) => {
      if (cancelled || !p) return
      setPersona(p)
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `您好！我是${p.display_name} ${p.emoji}\n${p.description}\n\n您可以问我「${p.sample_dialogs[0]?.q ?? '任何问题'}」，或点击下方能力快速开始。`,
        },
      ])
    })
    return () => {
      cancelled = true
      // 离开页面取消流
      if (streamRef.current) streamRef.current.cancel()
    }
  }, [personaId])

  // 离开页面取消流
  useDidHide(() => {
    if (streamRef.current) {
      streamRef.current.cancel()
      streamRef.current = null
    }
  })

  const scrollToBottom = (id: string) => {
    setScrollIntoViewId('')
    setTimeout(() => setScrollIntoViewId(id), 0)
  }

  const startAssistantStream = (userPrompt: string) => {
    if (!persona) return
    setPending(true)
    lastUserPromptRef.current = userPrompt

    chatWithPersona(personaId, { message: userPrompt })
      .then((resp) => {
        const aiId = `ai-${Date.now()}`
        // 先插入空消息，然后逐字流入
        setMessages((prev) => [
          ...prev,
          { id: aiId, role: 'assistant', content: '', streaming: true },
        ])
        scrollToBottom(`msg-${aiId}`)

        if (streamRef.current) streamRef.current.cancel()
        streamRef.current = fakeStream(
          resp.content,
          (_chunk, fullText, done) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId
                  ? { ...m, content: fullText, streaming: !done }
                  : m,
              ),
            )
            if (done) {
              setPending(false)
              streamRef.current = null
            } else {
              scrollToBottom(`msg-${aiId}`)
            }
          },
          50,
        )
      })
      .catch(() => {
        const errId = `ai-${Date.now()}`
        setMessages((prev) => [
          ...prev,
          {
            id: errId,
            role: 'assistant',
            content: '抱歉，智能体暂不可用，请稍后再试。',
          },
        ])
        setPending(false)
        scrollToBottom(`msg-${errId}`)
      })
  }

  const handleSend = () => {
    const content = inputValue.trim()
    if (!content || pending) return
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    }
    setMessages((prev) => [...prev, userMsg])
    setInputValue('')
    setShowCapChips(false)
    scrollToBottom(`msg-${userMsg.id}`)
    startAssistantStream(content)
  }

  const handleCapTap = (cap: string) => {
    // 取首句作为提示词
    const firstClause = cap.split(/[（(]/)[0]
    setInputValue(firstClause)
  }

  const handlePlus = () => {
    Taro.showActionSheet({
      itemList: ['拍照', '从相册选择', '上传文件', '切换到远端模型'],
      success: (res) => {
        if (res.tapIndex === 3) {
          setRunMode('cloud')
          Taro.showToast({ title: '已切换到云端模式', icon: 'none' })
        } else {
          Taro.showToast({ title: '该入口开发中', icon: 'none' })
        }
      },
    })
  }

  const handleToolbar = (action: 'clear' | 'history' | 'setting') => {
    if (action === 'clear') {
      Taro.showModal({
        title: '清空对话',
        content: '确定清空当前会话吗？',
        success: (res) => {
          if (res.confirm) {
            setMessages([])
            setShowCapChips(true)
          }
        },
      })
    } else if (action === 'history') {
      Taro.showToast({ title: '历史记录开发中', icon: 'none' })
    } else if (action === 'setting') {
      if (persona) {
        Taro.navigateTo({
          url: `/subpackages/personas/detail/index?personaId=${persona.persona_id}`,
        })
      }
    }
  }

  const handleMessageLongPress = (msg: ChatMessage) => {
    const items = ['复制', '转发', '删除']
    if (msg.role === 'assistant') items.push('重新生成')
    Taro.showActionSheet({
      itemList: items,
      success: (res) => {
        if (res.tapIndex === 0) {
          Taro.setClipboardData({ data: msg.content })
        } else if (res.tapIndex === 1) {
          Taro.setClipboardData({ data: msg.content }).then(() => {
            Taro.showToast({ title: '已复制，可粘贴转发', icon: 'none' })
          })
        } else if (res.tapIndex === 2) {
          setMessages((prev) => prev.filter((m) => m.id !== msg.id))
        } else if (res.tapIndex === 3 && msg.role === 'assistant') {
          // 重新生成 — 用上一条用户消息再 stream 一次
          const prompt = lastUserPromptRef.current
          if (!prompt) {
            Taro.showToast({ title: '没有可重新生成的消息', icon: 'none' })
            return
          }
          // 删除当前 AI 消息再 stream
          setMessages((prev) => prev.filter((m) => m.id !== msg.id))
          setTimeout(() => startAssistantStream(prompt), 50)
        }
      },
    })
  }

  const handleToggleMode = () => {
    const next: RunMode = runMode === 'local' ? 'cloud' : 'local'
    setRunMode(next)
    Taro.showToast({
      title: next === 'local' ? '已切到本地模式' : '已切到云端模式',
      icon: 'none',
    })
  }

  const handleStop = () => {
    if (streamRef.current) {
      streamRef.current.cancel()
      streamRef.current = null
    }
    setPending(false)
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    )
  }

  return (
    <View className='persona-chat'>
      {/* 自定义顶栏 */}
      <View className='chat-nav'>
        <View
          className='nav-back'
          onClick={() => Taro.navigateBack({ delta: 1 })}
        >
          <Text>‹</Text>
        </View>
        <View className='nav-title'>
          <Text className='nav-emoji'>{persona?.emoji ?? '🤖'}</Text>
          <Text className='nav-name'>{persona?.display_name ?? '加载中'}</Text>
        </View>
        <View
          className={`nav-mode ${runMode}`}
          onClick={handleToggleMode}
        >
          <Text>{runMode === 'local' ? '本地' : '云端'}</Text>
        </View>
        <View
          className='nav-detail'
          onClick={() => {
            if (persona) {
              Taro.navigateTo({
                url: `/subpackages/personas/detail/index?personaId=${persona.persona_id}`,
              })
            }
          }}
        >
          <Text>详情</Text>
        </View>
      </View>

      {/* 消息流 */}
      <ScrollView
        className='message-list'
        scrollY
        scrollWithAnimation
        scrollIntoView={scrollIntoViewId}
        enhanced
        showScrollbar={false}
      >
        {messages.map((m) => (
          <View
            key={m.id}
            id={`msg-${m.id}`}
            className={`message-row ${m.role}`}
            onLongPress={() => handleMessageLongPress(m)}
          >
            {m.role === 'assistant' && (
              <View className='avatar'>
                <Text>{persona?.emoji ?? '🤖'}</Text>
              </View>
            )}
            <View className='bubble'>
              <Text className='bubble-text'>
                {m.content}
                {m.streaming ? <Text className='cursor'>▋</Text> : null}
              </Text>
            </View>
            {m.role === 'user' && (
              <View className='avatar avatar-user'>
                <Text>👤</Text>
              </View>
            )}
          </View>
        ))}
        {pending && messages.every((m) => !m.streaming) && (
          <View className='message-row assistant'>
            <View className='avatar'>
              <Text>{persona?.emoji ?? '🤖'}</Text>
            </View>
            <View className='bubble typing'>
              <Text className='bubble-text'>思考中...</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* capability chips */}
      {showCapChips && persona ? (
        <View className='cap-chips'>
          <ScrollView scrollX enhanced showScrollbar={false} className='chips-scroll'>
            <View className='chips-row'>
              {persona.capabilities.map((c, i) => (
                <View
                  key={i}
                  className='cap-chip'
                  onClick={() => handleCapTap(c)}
                >
                  <Text>{c.split(/[（(]/)[0]}</Text>
                </View>
              ))}
            </View>
          </ScrollView>
        </View>
      ) : null}

      {/* 输入区 */}
      <View className='input-area'>
        <View className='input-row'>
          <View className='plus-btn' onClick={handlePlus}>
            <Text>+</Text>
          </View>
          <Input
            className='chat-input'
            placeholder='向智能体提问...'
            value={inputValue}
            onInput={(e) => setInputValue(e.detail.value)}
            onConfirm={handleSend}
            confirmType='send'
            adjustPosition
            cursorSpacing={20}
          />
          {pending ? (
            <View className='stop-btn' onClick={handleStop}>
              <Text>停止</Text>
            </View>
          ) : (
            <View
              className={`send-btn ${inputValue.trim() ? '' : 'disabled'}`}
              onClick={handleSend}
            >
              <Text>发送</Text>
            </View>
          )}
        </View>
        <View className='toolbar'>
          <View className='tool-item' onClick={() => handleToolbar('clear')}>
            <Text className='tool-emoji'>🗑️</Text>
            <Text className='tool-label'>清空</Text>
          </View>
          <View className='tool-item' onClick={() => handleToolbar('history')}>
            <Text className='tool-emoji'>🕘</Text>
            <Text className='tool-label'>历史</Text>
          </View>
          <View className='tool-item' onClick={() => handleToolbar('setting')}>
            <Text className='tool-emoji'>⚙️</Text>
            <Text className='tool-label'>设置</Text>
          </View>
        </View>
      </View>
    </View>
  )
}
