/**
 * TranscriptOverlay - 实时字幕覆盖层
 *
 * 订阅 LiveKit text stream 或 transcription 事件，
 * 在通话界面底部显示实时转录字幕。
 */

import { useState, useEffect, useRef } from 'react'
import { useRoomContext } from '@livekit/components-react'
import { RoomEvent, TranscriptionSegment } from 'livekit-client'

interface TranscriptLine {
  id: string
  text: string
  speaker: string
  timestamp: number
  isFinal: boolean
}

export default function TranscriptOverlay() {
  const room = useRoomContext()
  const [lines, setLines] = useState<TranscriptLine[]>([])
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!room) return

    const handleTranscription = (
      segments: TranscriptionSegment[],
      participant: any,
    ) => {
      for (const seg of segments) {
        const line: TranscriptLine = {
          id: seg.id,
          text: seg.text,
          speaker: participant?.name || participant?.identity || '未知',
          timestamp: Date.now(),
          isFinal: seg.final,
        }

        setLines((prev) => {
          // 更新已有的临时行或添加新行
          const existing = prev.findIndex((l) => l.id === seg.id)
          if (existing >= 0) {
            const updated = [...prev]
            updated[existing] = line
            return updated
          }
          // 只保留最近 20 行
          return [...prev.slice(-19), line]
        })
      }
    }

    room.on(RoomEvent.TranscriptionReceived, handleTranscription)

    return () => {
      room.off(RoomEvent.TranscriptionReceived, handleTranscription)
    }
  }, [room])

  // 自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [lines])

  if (lines.length === 0) return null

  return (
    <div
      ref={containerRef}
      className="absolute bottom-20 left-4 right-4 max-h-32 overflow-y-auto rounded-lg bg-black/60 backdrop-blur-sm px-4 py-2 space-y-1"
    >
      {lines.filter((l) => l.isFinal).slice(-5).map((line) => (
        <div key={line.id} className="text-sm">
          <span className="text-white/60 text-xs mr-2">{line.speaker}</span>
          <span className="text-white">{line.text}</span>
        </div>
      ))}
      {/* 显示当前正在说的（非 final） */}
      {lines.filter((l) => !l.isFinal).map((line) => (
        <div key={line.id} className="text-sm opacity-60">
          <span className="text-white/40 text-xs mr-2">{line.speaker}</span>
          <span className="text-white/70 italic">{line.text}...</span>
        </div>
      ))}
    </div>
  )
}
