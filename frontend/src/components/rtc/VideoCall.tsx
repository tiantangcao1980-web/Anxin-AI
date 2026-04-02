/**
 * VideoCall - 视频通话组件
 *
 * 视频通话模式，集成 AI 旁听助手面板和实时字幕。
 */

import { useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  LiveKitRoom,
  VideoConference,
} from '@livekit/components-react'
import '@livekit/components-styles'
import { icons } from '@/lib/icons'
import TranscriptOverlay from './TranscriptOverlay'
import AIAssistantPanel from '@/components/im/AIAssistantPanel'

export default function VideoCall() {
  const { roomName } = useParams<{ roomName: string }>()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const serverUrl = searchParams.get('server') || ''
  const conversationId = searchParams.get('conv') || roomName || ''
  const [showAssistant, setShowAssistant] = useState(false)

  if (!token || !serverUrl) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-900 text-white">
        <p>缺少通话参数，请从对话中发起通话</p>
      </div>
    )
  }

  return (
    <div className="h-screen flex">
      <div className="flex-1 relative">
        <LiveKitRoom
          token={token}
          serverUrl={serverUrl}
          connect={true}
          audio={true}
          video={true}
          data-lk-theme="default"
          style={{ height: '100%' }}
        >
          <VideoConference />
          <TranscriptOverlay />
        </LiveKitRoom>

        {/* AI 助手浮动按钮 */}
        <button
          onClick={() => setShowAssistant(!showAssistant)}
          className={`absolute top-4 right-4 z-50 w-10 h-10 rounded-full flex items-center justify-center transition-colors shadow-lg ${
            showAssistant ? 'bg-primary text-primary-foreground' : 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-sm'
          }`}
          title="AI 法律助手"
        >
          <icons.Bot className="w-5 h-5" />
        </button>
      </div>

      {/* AI 助手面板 */}
      {showAssistant && (
        <AIAssistantPanel
          conversationId={conversationId}
          conversationType="im"
          onClose={() => setShowAssistant(false)}
        />
      )}
    </div>
  )
}
