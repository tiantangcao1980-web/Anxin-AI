<template>
  <view class="chat-page">
    <!-- 消息列表 -->
    <scroll-view class="msg-list" scroll-y :scroll-into-view="lastMsgId">
      <view
        v-for="msg in messages"
        :key="msg.id"
        :id="'msg-' + msg.id"
        class="msg-wrap"
        :class="msg.role === 'user' ? 'msg-user' : 'msg-assistant'"
      >
        <view v-if="msg.role === 'assistant'" class="msg-avatar">{{ personaEmoji }}</view>
        <view class="msg-bubble">
          <text>{{ msg.content }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- 输入框 -->
    <view class="input-bar">
      <input
        v-model="input"
        class="input"
        placeholder="向 AI 提问..."
        confirm-type="send"
        @confirm="send"
      />
      <button class="send-btn" :disabled="!input.trim() || loading" @tap="send">
        {{ loading ? '...' : '发送' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const PERSONA_MAP: Record<string, { emoji: string; name: string; greeting: string }> = {
  legal_advisor: { emoji: '⚖️', name: '法律顾问', greeting: '您好，我是法律顾问。有什么合同或合规问题需要咨询？' },
  contract_steward: { emoji: '📄', name: '合同管家', greeting: '您好，我可以帮您起草、审查合同，识别风险条款。' },
  tax_finance: { emoji: '💰', name: '财税顾问', greeting: '您好，我是财税顾问，可以为您解答个税、企税、税务筹划问题。' },
  market_researcher: { emoji: '🔍', name: '市场研究员', greeting: '您好，我可以帮您调研公司、行业和竞品。' },
  content_director: { emoji: '✍️', name: '内容总监', greeting: '您好，我能生成文章、视频脚本、海报文案。' },
  ecommerce: { emoji: '🛒', name: '跨境电商', greeting: '您好，我可以协助选品、议价和合规审查。' },
}

const input = ref('')
const loading = ref(false)
const personaId = ref<string>('legal_advisor')
const messages = ref<Array<{ id: string; role: 'user' | 'assistant'; content: string }>>([])

const persona = computed(() => PERSONA_MAP[personaId.value] || PERSONA_MAP.legal_advisor)
const personaEmoji = computed(() => persona.value.emoji)
const lastMsgId = computed(() => (messages.value.length > 0 ? 'msg-' + messages.value[messages.value.length - 1].id : ''))

onMounted(() => {
  const pages = getCurrentPages()
  const current = pages[pages.length - 1] as any
  const query = current?.options || {}
  if (query.persona && PERSONA_MAP[query.persona]) {
    personaId.value = query.persona
  }
  uni.setNavigationBarTitle({ title: persona.value.name })
  messages.value.push({
    id: 'g-' + Date.now(),
    role: 'assistant',
    content: persona.value.greeting,
  })
})

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  const userMsg = { id: 'u-' + Date.now(), role: 'user' as const, content: text }
  messages.value.push(userMsg)
  input.value = ''
  loading.value = true

  // Demo 版：mock 响应（真实版调用 /api/v1/chat/send）
  setTimeout(() => {
    messages.value.push({
      id: 'a-' + Date.now(),
      role: 'assistant',
      content: `【演示模式】收到您的问题「${text}」。真实版会调用后端 ${persona.value.name} API 给出专业答复。`,
    })
    loading.value = false
  }, 800)
}
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f7f8fa;
}
.msg-list {
  flex: 1;
  padding: 24rpx;
}
.msg-wrap {
  display: flex;
  gap: 12rpx;
  margin-bottom: 24rpx;
}
.msg-user {
  flex-direction: row-reverse;
}
.msg-avatar {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  flex-shrink: 0;
}
.msg-bubble {
  max-width: 70%;
  padding: 18rpx 22rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.5;
}
.msg-user .msg-bubble {
  background: #2563eb;
  color: #fff;
}
.msg-assistant .msg-bubble {
  background: #fff;
  color: #1f2937;
}
.input-bar {
  display: flex;
  gap: 12rpx;
  padding: 16rpx 24rpx;
  background: #fff;
  border-top: 1rpx solid #e5e7eb;
}
.input {
  flex: 1;
  padding: 16rpx 20rpx;
  background: #f3f4f6;
  border-radius: 100rpx;
  font-size: 28rpx;
}
.send-btn {
  font-size: 26rpx;
  padding: 0 28rpx;
  background: #2563eb;
  color: #fff;
  border-radius: 100rpx;
  min-width: 100rpx;
}
.send-btn[disabled] {
  background: #9ca3af;
}
</style>
