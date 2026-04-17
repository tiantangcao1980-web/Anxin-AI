/**
 * ChatMessages Component
 * 负责渲染消息列表
 */

import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import ReactMarkdown from'react-markdown';
import { ThinkingChain } from'./ThinkingChain';
import { StreamingMessage } from'./StreamingMessage';
import { ClarificationBubble } from'./ClarificationBubble';
import { CitationList } from'./CitationList';
import { LongMessage } from'./LongMessage';
import type { Message } from'@/hooks';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble, proseStyle } from'@/lib/design-tokens';

interface ChatMessagesProps {
 messages: Message[];
 isLoadingHistory: boolean;
 isProcessing: boolean;
 thinkingSteps: any[];
 streamingContent: string;
 streamingAgent: string;
 streamingMessageId: string | null;
 onFeedback?: (message: Message, rating: number) => void;
 onClarificationResponse?: (originalContent: string, selections: Record<string, string>) => void;
}

export function ChatMessages({
 messages,
 isLoadingHistory,
 isProcessing,
 thinkingSteps,
 streamingContent,
 streamingAgent,
 streamingMessageId,
 onFeedback,
 onClarificationResponse,
}: ChatMessagesProps) {
 /**
 * 渲染单条消息
 */
 function renderMessage(message: Message) {
 // 引导式问答气泡
 if (message.type ==='clarification') {
 return (
 <ClarificationBubble
 key={message.id}
 message={message.content}
 questions={message.clarification!.questions}
 originalContent={message.clarification!.original_content}
 onSubmit={onClarificationResponse}
 disabled={isProcessing}
 />
 );
 }

 // 系统消息
 if (message.type ==='system') {
 const isError = message.metadata?.isError;
 return (
 <motion.div
 key={message.id}
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="flex justify-center"
 >
 <div
 className={`${chatBubble.system} mx-auto flex items-center gap-2 ${
 isError ? chatBubble.systemError : chatBubble.systemWarning
 }`}
 >
 <span>{message.content}</span>
 </div>
 </motion.div>
 );
 }

 const isUser = message.type ==='user';

 return (
 <motion.div
 initial={{ opacity: 0, y: 8 }}
 animate={{ opacity: 1, y: 0 }}
 key={message.id}
 className={`group ${isUser ?'flex justify-end' :''}`}
 >
 <div className={`max-w-[85%]`}>
 {/* V2: AI 消息绑定的思考过程 — 渲染在答案上方（DeepSeek/o1 风格） */}
 {!isUser && message.thinkingSteps && message.thinkingSteps.length > 0 && (
 <div className="mb-2">
 <ThinkingChain steps={message.thinkingSteps} isThinking={false} />
 </div>
 )}

 {/* AI 消息 - Agent 标签 */}
 {!isUser && message.agent && (
 <div className={`flex items-center gap-1.5 ${heading.micro} font-medium mb-1.5 ml-0.5`}>
 <icons.Bot className={iconSize.xs} />
 {message.agent}
 </div>
 )}

 {/* 消息气泡 */}
 <div
 className={`leading-relaxed text-sm ${
 isUser ? chatBubble.user : chatBubble.ai
 }`}
 >
 {/* 附件 */}
 {message.attachment && (
 <div
 className={`flex items-center gap-2.5 mb-2.5 p-2 rounded-lg ${
 isUser ?'bg-primary-foreground/15' :'bg-muted border border-border'
 }`}
 >
 <div
 className={`p-1.5 rounded ${isUser ?'bg-primary-foreground/20' :'bg-background shadow-sm'}`}
 >
 <icons.FileText
 className={`${iconSize.sm} ${isUser ?'text-primary-foreground' :'text-primary'}`}
 />
 </div>
 <div className="flex flex-col min-w-0">
 <span className="text-xs font-medium truncate">{message.attachment.name}</span>
 {message.attachment.size && (
 <span
 className={`text-[10px] ${isUser ?'text-primary-foreground/70' :'text-muted-foreground'}`}
 >
 {message.attachment.size}
 </span>
 )}
 </div>
 </div>
 )}

 {/* 消息内容 — V2：AI 消息用 LongMessage（长文折叠 + 法律文书卡片化） */}
 {isUser ? (
 <p className="whitespace-pre-wrap">{message.content}</p>
 ) : (
 <LongMessage
 content={message.content}
 isHistorical={!!message.memory_id}
 />
 )}
 </div>

 {/* AI 消息引用来源 */}
 {!isUser && message.sources && message.sources.length > 0 && (
 <CitationList sources={message.sources} />
 )}

 {/* AI 消息底部操作栏 */}
 {!isUser && (
 <div className="flex items-center gap-2 mt-1.5 ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
 <span className="text-[10px] text-muted-foreground">
 {message.timestamp.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </span>
 {message.memory_id && onFeedback && (
 <div className="flex items-center gap-0.5">
 <button
 onClick={() => onFeedback(message, 5)}
 disabled={!!message.feedback}
 className={`p-1 rounded-md hover:bg-muted transition-colors ${
 message.feedback ==='up' ?'text-success' :'text-muted-foreground hover:text-success'
 }`}
 title="有帮助"
 >
 <icons.ThumbsUp className={iconSize.xs} />
 </button>
 <button
 onClick={() => onFeedback(message, 1)}
 disabled={!!message.feedback}
 className={`p-1 rounded-md hover:bg-muted transition-colors ${
 message.feedback ==='down' ?'text-destructive' :'text-muted-foreground hover:text-destructive'
 }`}
 title="需改进"
 >
 <icons.ThumbsDown className={iconSize.xs} />
 </button>
 </div>
 )}
 </div>
 )}
 </div>
 </motion.div>
 );
 }

 return (
 <div className="space-y-6">
 {/* 加载历史 */}
 {isLoadingHistory && (
 <div className="flex items-center justify-center py-8">
 <icons.Loader2 className={`${iconSize.md} animate-spin text-muted-foreground mr-2`} />
 <span className={heading.muted}>正在加载对话历史...</span>
 </div>
 )}

 {/* 消息列表 */}
 {messages.map(renderMessage)}

 {/* 正在进行中的思考链 — V2：作为当前流式回答的"头部"显示 */}
 {thinkingSteps.length > 0 && isProcessing && (
 <div className="mb-2">
 <ThinkingChain steps={thinkingSteps} isThinking={true} />
 </div>
 )}

 {/* 流式消息（显示在思考链下方） */}
 {streamingMessageId && (
 <StreamingMessage content={streamingContent} agent={streamingAgent} isStreaming={true} />
 )}

 {/* 处理中指示 */}
 {isProcessing && !streamingMessageId && thinkingSteps.length === 0 && (
 <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
 <div className={`${chatBubble.ai} flex items-center gap-2`}>
 <icons.Loader2 className={`${iconSize.sm} animate-spin text-muted-foreground`} />
 <span className={heading.muted}>AI 正在思考...</span>
 </div>
 </motion.div>
 )}
 </div>
 );
}
