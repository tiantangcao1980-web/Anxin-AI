/**
 * AnonymousChatRoom - 匿名咨询聊天室
 *
 * 用户与律师在匹配后通过匿名聊天室沟通，
 * 双方同意后才揭示身份信息。
 *
 * 使用 WebSocket 实时通信。
 */

import { useState, useEffect, useRef, useCallback } from'react';
import { icons } from'@/lib/icons';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble } from'@/lib/design-tokens';
import { anonymousChatApi } from'@/lib/api';
import { toast } from'sonner';

interface ChatMessage {
 id: string;
 sender:'user' |'lawyer' |'system';
 content: string;
 timestamp: string;
 type:'text' |'system';
}

interface RevealInfo {
 user_name?: string;
 lawyer_name?: string;
 user_contact?: string;
 lawyer_contact?: string;
}

interface AnonymousChatRoomProps {
 roomId: string;
 token: string;
 role:'user' |'lawyer';
 onClose?: () => void;
}

export default function AnonymousChatRoom({ roomId, token, role, onClose }: AnonymousChatRoomProps) {
 const [messages, setMessages] = useState<ChatMessage[]>([]);
 const [inputValue, setInputValue] = useState('');
 const [connected, setConnected] = useState(false);
 const [revealed, setRevealed] = useState(false);
 const [revealInfo, setRevealInfo] = useState<RevealInfo>({});
 const [revealRequested, setRevealRequested] = useState(false);
 const [elapsedSeconds, setElapsedSeconds] = useState(0);

 const wsRef = useRef<WebSocket | null>(null);
 const messagesEndRef = useRef<HTMLDivElement>(null);
 const inputRef = useRef<HTMLTextAreaElement>(null);
 const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

 // 自动滚动到底部
 const scrollToBottom = useCallback(() => {
 messagesEndRef.current?.scrollIntoView({ behavior:'smooth' });
 }, []);

 useEffect(() => {
 scrollToBottom();
 }, [messages, scrollToBottom]);

 // 计时器
 useEffect(() => {
 timerRef.current = setInterval(() => {
 setElapsedSeconds(prev => prev + 1);
 }, 1000);
 return () => {
 if (timerRef.current) clearInterval(timerRef.current);
 };
 }, []);

 const formatTime = (secs: number) => {
 const m = Math.floor(secs / 60);
 const s = secs % 60;
 return `${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
 };

 // WebSocket 连接
 useEffect(() => {
 const wsProtocol = window.location.protocol ==='https:' ?'wss:' :'ws:';
 const wsHost = import.meta.env.VITE_WS_HOST || window.location.host;
 const wsUrl = `${wsProtocol}//${wsHost}/api/v1/anonymous-chat/ws/${roomId}?token=${token}`;

 const ws = new WebSocket(wsUrl);
 wsRef.current = ws;

 ws.onopen = () => {
 setConnected(true);
 };

 ws.onmessage = (event) => {
 try {
 const data = JSON.parse(event.data);

 if (data.type ==='history') {
 // 历史消息
 setMessages(data.messages || []);
 if (data.revealed) {
 setRevealed(true);
 }
 } else if (data.type ==='message' || data.type ==='system') {
 // 新消息
 setMessages(prev => [...prev, data.message]);
 } else if (data.type ==='reveal') {
 // 身份揭示
 setRevealed(true);
 setRevealInfo({
 user_name: data.user_name,
 lawyer_name: data.lawyer_name,
 user_contact: data.user_contact,
 lawyer_contact: data.lawyer_contact,
 });
 setMessages(prev => [...prev, data.message]);
 toast.success('身份信息已揭示');
 }
 } catch (e) {
 console.error('WebSocket 消息解析失败:', e);
 }
 };

 ws.onclose = () => {
 setConnected(false);
 };

 ws.onerror = () => {
 setConnected(false);
 toast.error('聊天连接异常');
 };

 return () => {
 ws.close();
 };
 }, [roomId, token]);

 // 发送消息
 const sendMessage = useCallback(() => {
 const content = inputValue.trim();
 if (!content || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

 wsRef.current.send(JSON.stringify({ content }));
 setInputValue('');
 inputRef.current?.focus();
 }, [inputValue]);

 // 键盘快捷键
 const handleKeyDown = (e: React.KeyboardEvent) => {
 if (e.key ==='Enter' && !e.shiftKey) {
 e.preventDefault();
 sendMessage();
 }
 };

 // 请求揭示身份
 const handleReveal = async () => {
 try {
 const result = await anonymousChatApi.revealIdentity(roomId, token);
 setRevealRequested(true);
 if (result.revealed) {
 setRevealed(true);
 setRevealInfo({
 user_name: result.user_name,
 lawyer_name: result.lawyer_name,
 user_contact: result.user_contact,
 lawyer_contact: result.lawyer_contact,
 });
 } else {
 toast.info(result.message);
 }
 } catch (e: any) {
 toast.error(e.message ||'操作失败');
 }
 };

 // 格式化消息时间
 const formatMsgTime = (ts: string) => {
 try {
 const d = new Date(ts);
 return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
 } catch {
 return'';
 }
 };

 const otherParty = role ==='user' ?'律师' :'用户';

 return (
 <div className="flex flex-col h-full bg-background">
 {/* 头部 */}
 <div className={`flex items-center justify-between px-4 py-3 border-b border-border bg-background`}>
 <div className="flex items-center gap-3">
 {onClose && (
 <button onClick={onClose} className={buttonStyle.icon}>
 <icons.ArrowLeft className={iconSize.md} />
 </button>
 )}
 <div>
 <h2 className={heading.section}>
 <icons.ShieldCheck className={`${iconSize.sm} inline mr-1.5 text-primary`} />
 匿名咨询室
 </h2>
 <div className="flex items-center gap-2 mt-0.5">
 <span className={`inline-block w-1.5 h-1.5 rounded-full ${connected ?'bg-success' :'bg-muted-foreground/30'}`} />
 <span className="text-xs text-muted-foreground">
 {connected ?'已连接' :'连接中...'}
 </span>
 <span className="text-xs text-muted-foreground">
 <icons.Clock className="w-3 h-3 inline mr-0.5" />
 {formatTime(elapsedSeconds)}
 </span>
 </div>
 </div>
 </div>

 <div className="flex items-center gap-2">
 {!revealed && (
 <button
 onClick={handleReveal}
 disabled={revealRequested}
 className={`${buttonStyle.sm} ${revealRequested
 ?'bg-muted text-muted-foreground cursor-not-allowed'
 :'bg-primary text-primary-foreground hover:bg-primary/90'
 }`}
 >
 <icons.Eye className="w-3.5 h-3.5 inline mr-1" />
 {revealRequested ?'等待对方确认' :'揭示身份'}
 </button>
 )}
 </div>
 </div>

 {/* 身份揭示成功横幅 */}
 {revealed && (
 <div className="mx-4 mt-3 p-3 bg-success/10 border border-success/20 rounded-xl">
 <div className="flex items-center gap-2 mb-1.5">
 <icons.CheckCircle className={`${iconSize.sm} text-success`} />
 <span className="text-sm font-medium text-success">身份已揭示</span>
 </div>
 <div className="text-xs text-success space-y-0.5">
 {revealInfo.lawyer_name && (
 <p>律师：{revealInfo.lawyer_name} {revealInfo.lawyer_contact && `| ${revealInfo.lawyer_contact}`}</p>
 )}
 {revealInfo.user_name && (
 <p>用户：{revealInfo.user_name} {revealInfo.user_contact && `| ${revealInfo.user_contact}`}</p>
 )}
 </div>
 </div>
 )}

 {/* 消息列表 */}
 <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
 {messages.map((msg) => {
 // 系统消息
 if (msg.type ==='system' || msg.sender ==='system') {
 return (
 <div key={msg.id} className="flex justify-center">
 <span className={`${chatBubble.system} bg-muted/60 text-muted-foreground border border-border`}>
 {msg.content}
 </span>
 </div>
 );
 }

 const isMe = msg.sender === role;

 return (
 <div key={msg.id} className={`flex ${isMe ?'justify-end' :'justify-start'}`}>
 <div className={`max-w-[75%] ${isMe ?'order-2' :'order-1'}`}>
 {/* 角色标签 */}
 <p className={`text-[10px] text-muted-foreground mb-1 ${isMe ?'text-right' :'text-left'}`}>
 {isMe ?'我' : `匿名${otherParty}`}
 </p>
 {/* 气泡 */}
 <div className={isMe ? chatBubble.user : chatBubble.ai}>
 <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
 </div>
 {/* 时间 */}
 <p className={`text-[10px] text-muted-foreground mt-1 ${isMe ?'text-right' :'text-left'}`}>
 {formatMsgTime(msg.timestamp)}
 </p>
 </div>
 </div>
 );
 })}
 <div ref={messagesEndRef} />
 </div>

 {/* 输入区域 */}
 <div className="px-4 py-3 border-t border-border bg-background">
 <div className="flex items-end gap-2">
 <div className="flex-1 relative bg-muted/50 rounded-2xl border border-border focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10 transition-all">
 <textarea
 ref={inputRef}
 value={inputValue}
 onChange={(e) => setInputValue(e.target.value)}
 onKeyDown={handleKeyDown}
 placeholder={connected ? `发送消息给匿名${otherParty}...` :'连接中...'}
 disabled={!connected}
 rows={1}
 className="w-full py-2.5 px-4 bg-transparent border-none resize-none focus:outline-none text-foreground placeholder:text-muted-foreground text-sm leading-relaxed max-h-32"
 style={{ minHeight:'40px' }}
 />
 </div>
 <button
 onClick={sendMessage}
 disabled={!connected || !inputValue.trim()}
 className={`${buttonStyle.primary} p-2.5 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed`}
 >
 <icons.Send className={iconSize.md} />
 </button>
 </div>
 <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
 <icons.Lock className="w-3 h-3 inline mr-0.5" />
 消息已加密传输 · 身份信息在双方同意前完全隐藏
 </p>
 </div>
 </div>
 );
}
