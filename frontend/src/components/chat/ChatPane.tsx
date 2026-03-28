import { useEffect, useRef } from 'react';
import { Message } from './ChatCanvas';
import { icons } from '@/lib/icons';
import { motion } from 'framer-motion';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble } from '@/lib/design-tokens';

interface ChatPaneProps {
  messages: Message[];
  isProcessing: boolean;
}

export function ChatPane({ messages, isProcessing }: ChatPaneProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <motion.div
          key={message.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[92%] sm:max-w-[80%] ${
              message.type === 'user'
                ? chatBubble.user
                : message.type === 'system'
                ? `${chatBubble.system} ${chatBubble.systemWarning}`
                : chatBubble.ai
            }`}
          >
            {message.attachment && (
              <div className="mb-2 flex items-center gap-2 pb-2 border-b border-white/20">
                {message.attachment.type === 'file' ? (
                  <icons.FileText className={iconSize.sm} />
                ) : (
                  <icons.Image className={iconSize.sm} />
                )}
                <div className="flex-1 min-w-0">
                  <p className={`${heading.card} truncate`}>{message.attachment.name}</p>
                  <p className={`${heading.micro} opacity-70`}>{message.attachment.size}</p>
                </div>
              </div>
            )}
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            <p
              className={`text-xs mt-1.5 ${
                message.type === 'user' ? 'text-primary/30' : 'text-muted-foreground'
              }`}
            >
              {message.timestamp.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </div>
        </motion.div>
      ))}
      
      {isProcessing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex justify-start"
        >
          <div className={`${chatBubble.ai} flex items-center gap-2`}>
            <icons.Loader2 className={`${iconSize.sm} animate-spin text-muted-foreground`} />
            <span className={heading.muted}>AI 正在思考...</span>
          </div>
        </motion.div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
}