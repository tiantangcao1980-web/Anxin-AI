import { useState, useEffect, useRef } from'react';
import { Progress } from'@/components/ui/progress';
import { Card, CardContent } from'@/components/ui/card';
import { Badge } from'@/components/ui/badge';
import { icons } from'@/lib/icons';
import { buildWebSocketUrl } from'@/lib/api';

interface CrawlProgressBarProps {
 taskId: string;
 onComplete?: () => void;
}

const FRIENDLY_MESSAGES: Record<string, string> = {
 starting:'正在初始化情报引擎...',
 crawling:'正在从公开信息源采集数据...',
 processing:'正在清洗和结构化数据...',
 storing:'正在将数据写入知识库...',
 completed:'情报采集完成',
 error:'情报采集暂不可用，调查将通过其他方式进行',
}

/** 将后端原始消息转换为用户友好的文本 */
function sanitizeMessage(rawMsg: string, status: string): string {
 if (status ==='error' || status ==='failed') return FRIENDLY_MESSAGES.error
 if (FRIENDLY_MESSAGES[status]) return FRIENDLY_MESSAGES[status]
 if (/playwright|browser|launch|executable|chromium/i.test(rawMsg)) return FRIENDLY_MESSAGES.error
 if (/timeout|timed out/i.test(rawMsg)) return'采集超时，跳过该步骤'
 if (rawMsg.length > 80) return rawMsg.slice(0, 60) +'...'
 return rawMsg
}

export function CrawlProgressBar({ taskId, onComplete }: CrawlProgressBarProps) {
 const [progress, setProgress] = useState(0);
 const [status, setStatus] = useState<string>('initializing');
 const [message, setMessage] = useState<string>('正在初始化情报引擎...');
 const [isConnected, setIsConnected] = useState(false);
 const [hidden, setHidden] = useState(false);
 const errorTimerRef = useRef<ReturnType<typeof setTimeout>>();

 useEffect(() => {
 if (!taskId) return;

 let socket: WebSocket | null = null;
 let connectTimeout: ReturnType<typeof setTimeout> | null = null;

 const connectTimer = window.setTimeout(() => {
 try {
 const wsUrl = buildWebSocketUrl(`/lic/ws/${taskId}`);
 socket = new WebSocket(wsUrl);
 } catch {
 setHidden(true);
 return;
 }

 connectTimeout = setTimeout(() => {
 setHidden((prevHidden) => prevHidden || !socket || socket.readyState !== WebSocket.OPEN);
 }, 8000);

 socket.onopen = () => {
 if (connectTimeout) clearTimeout(connectTimeout);
 setIsConnected(true);
 };

 socket.onmessage = (event) => {
 try {
 const data = JSON.parse(event.data);
 if (data.type ==='lic_progress') {
 const friendlyMsg = sanitizeMessage(data.message ||'', data.status ||'');
 setProgress(data.progress);
 setStatus(data.status);
 setMessage(friendlyMsg);

 if (data.status ==='completed') {
 onComplete?.();
 }

 if (data.status ==='error' || data.status ==='failed') {
 errorTimerRef.current = setTimeout(() => setHidden(true), 5000);
 }
 }
 } catch { /* 忽略解析错误 */ }
 };

 socket.onerror = () => {
 if (connectTimeout) clearTimeout(connectTimeout);
 setHidden(true);
 };

 socket.onclose = () => {
 setIsConnected(false);
 };
 }, 0);

 return () => {
 clearTimeout(connectTimer);
 if (connectTimeout) clearTimeout(connectTimeout);
 if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
 if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
 socket.close(1000,'component cleanup');
 }
 };
 }, [taskId, onComplete]);

 if (!taskId || hidden) return null;

 const isError = status ==='error' || status ==='failed';
 const isDone = status ==='completed';

 return (
 <Card className={`overflow-hidden transition-all duration-300 ${
 isError
 ?'border-warning/20 bg-warning/10/50'
 : isDone
 ?'border-success/20 bg-success/10'
 :'border-primary/20 bg-primary/5'
 }`}>
 <CardContent className="p-4">
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2 flex-1 min-w-0">
 <div className={`p-1.5 rounded-lg shrink-0 ${
 isError ?'bg-warning/10 text-warning'
 : isDone ?'bg-success/10 text-success'
 :'bg-primary/10 text-primary'
 }`}>
 {isError ? <icons.AlertTriangle className="h-4 w-4" />
 : isDone ? <icons.CheckCircle className="h-4 w-4" />
 : <icons.Globe className="h-4 w-4" />}
 </div>
 <div className="min-w-0 flex-1">
 <h4 className="text-sm font-medium text-foreground">
 {isError ?'情报采集（已跳过）' : isDone ?'情报采集完成' :'LIC 情报抓取引擎'}
 </h4>
 <p className="text-xs text-muted-foreground truncate">{message}</p>
 </div>
 </div>
 <Badge
 variant={isError ?'outline' : isDone ?'secondary' :'secondary'}
 className={`shrink-0 ml-2 ${isError ?'text-warning border-warning/20' :''}`}
 >
 {isDone ? (
 <span className="flex items-center gap-1">
 <icons.CheckCircle2 className="h-3 w-3" /> 完成
 </span>
 ) : isError ? (
 <span className="flex items-center gap-1">
 <icons.AlertCircle className="h-3 w-3" /> 跳过
 </span>
 ) : (
 <span className="flex items-center gap-1">
 <icons.Loader2 className="h-3 w-3 animate-spin" /> 采集中
 </span>
 )}
 </Badge>
 </div>
 {!isError && (
 <>
 <Progress value={progress} className="h-1.5 bg-primary/10" />
 <div className="mt-1.5 flex justify-between items-center">
 <span className="text-[10px] text-primary font-medium">进度: {progress}%</span>
 <span className="text-[10px] text-muted-foreground">
 {isConnected ?'● 实时连接中' :'○ 等待连接'}
 </span>
 </div>
 </>
 )}
 {isError && (
 <p className="text-[10px] text-warning mt-1">
 核心调查数据不受影响，AI 分析将正常进行
 </p>
 )}
 </CardContent>
 </Card>
 );
}
