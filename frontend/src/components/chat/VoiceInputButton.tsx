/**
 * VoiceInputButton - 语音输入按钮
 *
 * 使用浏览器原生 Web Speech API 进行语音转文字。
 * 三种状态：默认 / 录音中（红色脉冲）/ 不支持（灰色禁用）
 */

import { useEffect } from 'react';
import { icons } from '@/lib/icons';
import { toolbarButton } from '@/lib/design-tokens';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { toast } from 'sonner';

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export function VoiceInputButton({ onTranscript, disabled = false }: VoiceInputButtonProps) {
  const {
    isListening,
    transcript,
    interimTranscript,
    isSupported,
    error,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition();

  // 识别完成后输出文本
  useEffect(() => {
    if (!isListening && transcript) {
      onTranscript(transcript);
      resetTranscript();
    }
  }, [isListening, transcript, onTranscript, resetTranscript]);

  // 错误提示
  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);

  const handleClick = () => {
    if (!isSupported) {
      toast.error('当前浏览器不支持语音识别，请使用 Chrome 或 Edge');
      return;
    }
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleClick}
        disabled={disabled || !isSupported}
        className={`${toolbarButton.base} ${
          isListening
            ? 'text-destructive bg-destructive/10 animate-pulse'
            : !isSupported
            ? 'opacity-40 cursor-not-allowed'
            : ''
        }`}
        title={
          !isSupported
            ? '浏览器不支持语音识别'
            : isListening
            ? '点击停止录音'
            : '语音输入'
        }
      >
        {isListening ? (
          <icons.MicOff className="w-4 h-4" />
        ) : (
          <icons.Mic className="w-4 h-4" />
        )}
      </button>

      {/* 实时转写浮层 */}
      {isListening && (interimTranscript || transcript) && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-popover border border-border rounded-lg shadow-lg px-3 py-2 text-xs text-foreground max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis z-50">
          {interimTranscript || transcript}
        </div>
      )}
    </div>
  );
}
