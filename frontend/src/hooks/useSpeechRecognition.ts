/**
 * useSpeechRecognition - 浏览器原生语音识别 Hook
 *
 * 使用 Web Speech API (SpeechRecognition)，纯前端 ASR，无后端依赖。
 * 支持：Chrome/Edge 完整支持，Safari 部分支持，Firefox 不支持。
 */

import { useState, useRef, useCallback, useEffect } from 'react';

interface SpeechRecognitionResult {
  /** 是否正在录音 */
  isListening: boolean;
  /** 最终识别文本 */
  transcript: string;
  /** 实时中间识别文本 */
  interimTranscript: string;
  /** 浏览器是否支持 */
  isSupported: boolean;
  /** 错误信息 */
  error: string | null;
  /** 开始识别 */
  startListening: () => void;
  /** 停止识别 */
  stopListening: () => void;
  /** 清空识别结果 */
  resetTranscript: () => void;
}

export function useSpeechRecognition(): SpeechRecognitionResult {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const SpeechRecognition =
    typeof window !== 'undefined'
      ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      : null;

  const isSupported = !!SpeechRecognition;

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  const startListening = useCallback(() => {
    if (!SpeechRecognition) {
      setError('当前浏览器不支持语音识别，请使用 Chrome 或 Edge');
      return;
    }

    setError(null);
    setTranscript('');
    setInterimTranscript('');

    const recognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      let finalText = '';
      let interimText = '';

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interimText += result[0].transcript;
        }
      }

      if (finalText) setTranscript(finalText);
      setInterimTranscript(interimText);

      // 重置自动停止计时器（每次有结果就续命）
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => {
        stopListening();
      }, 8000);
    };

    recognition.onerror = (event: any) => {
      const errMap: Record<string, string> = {
        'not-allowed': '麦克风权限被拒绝，请在浏览器设置中允许',
        'no-speech': '未检测到语音，请对着麦克风说话',
        'audio-capture': '无法访问麦克风，请检查设备连接',
        'network': '网络错误，语音识别服务不可用',
      };
      setError(errMap[event.error] || `语音识别错误: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimTranscript('');
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);

    // 10 秒无语音自动停止
    timeoutRef.current = setTimeout(() => {
      stopListening();
    }, 10000);
  }, [SpeechRecognition, stopListening]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    isSupported,
    error,
    startListening,
    stopListening,
    resetTranscript,
  };
}
