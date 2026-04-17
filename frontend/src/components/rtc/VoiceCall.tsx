/**
 * VoiceCall - 语音通话组件
 *
 * 纯音频通话模式，集成 AI 旁听助手面板和实时字幕。
 */

import { useState, useCallback } from'react'
import { useParams, useNavigate, useSearchParams } from'react-router-dom'
import {
 LiveKitRoom,
 RoomAudioRenderer,
 useParticipants,
 useRoomContext,
 useTracks,
 TrackToggle,
 DisconnectButton,
} from'@livekit/components-react'
import'@livekit/components-styles'
import { Track } from'livekit-client'
import { icons } from'@/lib/icons'
import { rtcApi } from'@/lib/api'
import TranscriptOverlay from'./TranscriptOverlay'
import AIAssistantPanel from'@/components/im/AIAssistantPanel'

function CallControls({ conversationId }: { conversationId: string }) {
 const [showAssistant, setShowAssistant] = useState(false)
 const participants = useParticipants()
 const navigate = useNavigate()

 return (
 <div className="flex h-full">
 {/* 主区域 */}
 <div className="flex-1 flex flex-col relative bg-gradient-to-b from-slate-900 to-slate-800">
 {/* 参与者列表 */}
 <div className="flex-1 flex items-center justify-center">
 <div className="flex gap-8">
 {participants.map((p) => (
 <div key={p.identity} className="flex flex-col items-center gap-3">
 <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center border-2 border-primary/40">
 <icons.User className="w-10 h-10 text-primary" />
 </div>
 <span className="text-white text-sm font-medium">{p.name || p.identity}</span>
 <span className="text-white/50 text-xs">
 {p.isSpeaking ?'正在说话...' :'已连接'}
 </span>
 </div>
 ))}
 </div>
 </div>

 {/* 实时字幕 */}
 <TranscriptOverlay />

 {/* 底部控制栏 */}
 <div className="flex items-center justify-center gap-4 py-6">
 <TrackToggle
 source={Track.Source.Microphone}
 className="w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
 />
 <button
 onClick={() => setShowAssistant(!showAssistant)}
 className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
 showAssistant ?'bg-primary text-primary-foreground' :'bg-white/10 hover:bg-white/20 text-white'
 }`}
 title="AI 法律助手"
 >
 <icons.Bot className="w-5 h-5" />
 </button>
 <DisconnectButton
 className="w-14 h-14 rounded-full bg-destructive hover:bg-destructive/20 flex items-center justify-center text-destructive-foreground transition-colors"
 onClick={() => navigate(-1)}
 >
 <icons.PhoneOff className="w-6 h-6" />
 </DisconnectButton>
 </div>

 <RoomAudioRenderer />
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

export default function VoiceCall() {
 const { roomName } = useParams<{ roomName: string }>()
 const [searchParams] = useSearchParams()
 const token = searchParams.get('token') ||''
 const serverUrl = searchParams.get('server') ||''
 const conversationId = searchParams.get('conv') || roomName ||''

 if (!token || !serverUrl) {
 return (
 <div className="h-screen flex items-center justify-center bg-slate-900 text-white">
 <p>缺少通话参数，请从对话中发起通话</p>
 </div>
 )
 }

 return (
 <div className="h-screen">
 <LiveKitRoom
 token={token}
 serverUrl={serverUrl}
 connect={true}
 audio={true}
 video={false}
 data-lk-theme="default"
 >
 <CallControls conversationId={conversationId} />
 </LiveKitRoom>
 </div>
 )
}
