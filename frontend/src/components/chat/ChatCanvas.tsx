import { useState, useRef, useEffect } from 'react';
import { ChatPane } from './ChatPane';
import { ContextPane } from './ContextPane';
import { MultiModalInput } from './MultiModalInput';
import { AgentFlow } from './AgentFlow';
import { Resizable } from 're-resizable';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, buttonStyle, shadow } from '@/lib/design-tokens';
import { chatApi } from '@/lib/api';
import { toast } from 'sonner';

export interface Message {
  id: string;
  type: 'user' | 'ai' | 'system';
  content: string;
  timestamp: Date;
  attachment?: {
    type: 'file' | 'image';
    name: string;
    size: string;
  };
}

export interface ContextContent {
  type: 'idle' | 'document-preview' | 'risk-radar' | 'document-diff' | 'report' | 'a2ui';
  data?: any;
}

export function ChatCanvas() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'ai',
      content: '您好！我是您的 安心智能助手。我可以帮您进行合同审查、尽职调查、法律咨询等工作。请告诉我您需要什么帮助？',
      timestamp: new Date(),
    },
  ]);
  
  const [contextContent, setContextContent] = useState<ContextContent>({ type: 'idle' });
  const [showAgentFlow, setShowAgentFlow] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [chatWidth, setChatWidth] = useState(50); // 百分比
  const [isMobile, setIsMobile] = useState(false);
  const [mobileView, setMobileView] = useState<'chat' | 'context'>('chat');
  const [showContextPanel, setShowContextPanel] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => 'session-' + Date.now());
  const wsRef = useRef<WebSocket | null>(null);

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // WebSocket 连接
  useEffect(() => {
    const ws = chatApi.connectWebSocket(sessionId, (data) => {
      handleWebSocketMessage(data);
    });
    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionId]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'agent_thinking':
        setIsProcessing(true);
        break;
        
      case 'agent_start':
        setShowAgentFlow(true);
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: 'ai',
          content: `${data.agent}: ${data.message}`,
          timestamp: new Date(),
        }]);
        break;
        
      case 'agent_response':
        setIsProcessing(false);
        setShowAgentFlow(false);
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: 'ai',
          content: data.content,
          timestamp: new Date(),
        }]);
        break;
        
      case 'context_update':
        if (data.context_type === 'a2ui') {
          setContextContent({
            type: 'a2ui',
            data: data.data
          });
          if (isMobile) setShowContextPanel(true);
        }
        break;
        
      case 'error':
        setIsProcessing(false);
        toast.error(data.content || '发生错误');
        break;
    }
  };

  const handleSendMessage = async (content: string, file?: File) => {
    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: content || (file ? `上传了文件: ${file.name}` : ''),
      timestamp: new Date(),
      attachment: file ? {
        type: file.type.includes('image') ? 'image' : 'file',
        name: file.name,
        size: `${(file.size / 1024).toFixed(1)} KB`,
      } : undefined,
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);

    if (file) {
      // 如果有文件，先上传并触发分析 (这里简化处理，实际可能需要先上传文件API)
      try {
        // TODO: 调用文件上传 API
        // const doc = await documentsApi.upload(file, { ... });
        // content = `请分析这份文件: ${doc.id}`;
      } catch (e) {
        toast.error('文件上传失败');
        setIsProcessing(false);
        return;
      }
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        content: content,
        session_id: sessionId
      }));
    } else {
      // Fallback to HTTP if WS is not open
      try {
        const response = await chatApi.sendMessage({
          content,
          conversation_id: sessionId
        });
        setMessages(prev => [...prev, {
          id: response.message_id,
          type: 'ai',
          content: response.content,
          timestamp: new Date(),
        }]);
        setIsProcessing(false);
      } catch (e) {
        toast.error('发送失败');
        setIsProcessing(false);
      }
    }
  };

  // 移动端布局
  if (isMobile) {
    return (
      <div className="h-full flex flex-col bg-background">
        {/* Agent Flow Overlay */}
        {showAgentFlow && <AgentFlow />}

        {/* Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <ChatPane messages={messages} isProcessing={isProcessing} />
          <MultiModalInput onSend={handleSendMessage} disabled={isProcessing} />
        </div>

        {/* Context Bottom Sheet */}
        <AnimatePresence>
          {showContextPanel && contextContent.type !== 'idle' && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setShowContextPanel(false)}
                className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
              />
              
              {/* Bottom Sheet */}
              <motion.div
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                exit={{ y: '100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="fixed inset-x-0 bottom-0 z-50 bg-background rounded-t-3xl shadow-2xl max-h-[85vh] flex flex-col"
              >
                {/* Handle */}
                <div className="flex items-center justify-center py-3 border-b border-border">
                  <div className="w-10 h-1 bg-muted-foreground/30 rounded-full" />
                </div>

                {/* Header */}
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <h3 className="font-semibold text-foreground">分析结果</h3>
                  <button
                    onClick={() => setShowContextPanel(false)}
                    className={buttonStyle.icon}
                  >
                    <icons.X className={`${iconSize.md} text-muted-foreground`} />
                  </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto">
                  <ContextPane content={contextContent} />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* Floating Action Button - Show when context available */}
        {contextContent.type !== 'idle' && !showContextPanel && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            onClick={() => setShowContextPanel(true)}
            className={`fixed bottom-20 right-4 w-14 h-14 bg-primary rounded-full ${shadow.dropdown} flex items-center justify-center text-primary-foreground z-30 active:scale-95 transition-transform`}
          >
            <icons.FileText className={iconSize.lg} />
            {contextContent.data?.detectedIssues && (
              <span className={`absolute -top-1 -right-1 ${iconSize.lg} bg-destructive rounded-full text-xs font-bold flex items-center justify-center`}>
                {contextContent.data.detectedIssues}
              </span>
            )}
          </motion.button>
        )}
      </div>
    );
  }

  // 桌面端布局
  return (
    <div className="h-full flex flex-col">
      {/* Agent Flow Overlay */}
      {showAgentFlow && <AgentFlow />}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Chat Pane - Resizable */}
        <Resizable
          size={{ width: `${chatWidth}%`, height: '100%' }}
          onResizeStop={(e, direction, ref, d) => {
            const newWidth = chatWidth + (d.width / ref.parentElement!.offsetWidth) * 100;
            setChatWidth(Math.min(Math.max(newWidth, 30), 70)); // 限制在30%-70%
          }}
          minWidth="30%"
          maxWidth="70%"
          enable={{
            top: false,
            right: true,
            bottom: false,
            left: false,
            topRight: false,
            bottomRight: false,
            bottomLeft: false,
            topLeft: false,
          }}
          handleStyles={{
            right: {
              width: '4px',
              right: '-2px',
              cursor: 'col-resize',
            },
          }}
          handleClasses={{
            right: 'hover:bg-primary/90 transition-colors',
          }}
          className="border-r border-border flex flex-col bg-background"
        >
          <ChatPane messages={messages} isProcessing={isProcessing} />
          <MultiModalInput onSend={handleSendMessage} disabled={isProcessing} />
        </Resizable>

        {/* Right: Context Pane */}
        <div className="flex-1 bg-muted dark:bg-muted/20 overflow-hidden">
          <ContextPane content={contextContent} />
        </div>
      </div>
    </div>
  );
}
