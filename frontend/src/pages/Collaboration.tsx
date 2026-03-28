import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { icons } from '@/lib/icons';
import { collaborationApi, documentsApi, type CollaborationSession, type Collaborator } from '@/lib/api';
import { cardStyle, heading, iconSize, statusBadge, buttonStyle } from '@/lib/design-tokens';
import { PageContainer } from '@/components/ui/PageContainer';

// WebSocket消息类型
interface WSMessage {
  type: 'init' | 'join' | 'leave' | 'edit' | 'cursor' | 'pong' | 'session_closed';
  user_id?: string;
  nickname?: string;
  color?: string;
  content?: string;
  version?: number;
  position?: any;
  operation?: string;
  collaborators?: any[];
  message?: string;
}

// 协作者颜色
const collaboratorColors = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DFE6E9', '#74B9FF', '#A29BFE',
  '#FD79A8', '#00B894', '#E17055', '#6C5CE7',
];

export default function Collaboration() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  
  const [sessions, setSessions] = useState<CollaborationSession[]>([]);
  const [currentSession, setCurrentSession] = useState<CollaborationSession | null>(null);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);
  
  // 版本控制
  const [showCommitDialog, setShowCommitDialog] = useState(false);
  const [commitMessage, setCommitMessage] = useState('');
  const [isCommitting, setIsCommitting] = useState(false);
  const [collabConfig, setCollabConfig] = useState<any>(null);
  
  // WebSocket
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // 创建会话对话框
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newSession, setNewSession] = useState({
    documentId: '',
    name: '',
  });
  
  // 用户信息
  const userId = useRef(localStorage.getItem('user_id') || `user_${Math.random().toString(36).substring(7)}`);
  const userColor = useRef(collaboratorColors[Math.floor(Math.random() * collaboratorColors.length)]);
  const nickname = useRef(localStorage.getItem('username') || `用户${userId.current.substring(0, 4)}`);

  // 加载会话列表
  useEffect(() => {
    loadSessions();
    loadDocuments();
    loadCollabConfig();
  }, []);

  const loadCollabConfig = async () => {
    try {
      const config = await collaborationApi.getConfig();
      setCollabConfig(config);
    } catch (e) {
      console.error('加载协作配置失败');
    }
  };

  // 加载指定会话
  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId);
      connectWebSocket(sessionId);
    }
    
    return () => {
      disconnectWebSocket();
    };
  }, [sessionId]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await collaborationApi.listSessions();
      setSessions(response.items);
    } catch (error) {
      console.error('加载会话列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const response = await documentsApi.list();
      setDocuments(response.items);
    } catch (error) {
      console.error('加载文档列表失败:', error);
    }
  };

  const loadSession = async (id: string) => {
    try {
      const session = await collaborationApi.getSession(id);
      setCurrentSession(session);
      
      const collabs = await collaborationApi.getCollaborators(id);
      setCollaborators(collabs);
    } catch (error) {
      toast.error('加载会话失败');
      navigate('/collaboration');
    }
  };

  // WebSocket连接
  const connectWebSocket = useCallback((id: string) => {
    const wsUrl = `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8002'}/api/v1/collaboration/ws/${id}?user_id=${userId.current}&nickname=${encodeURIComponent(nickname.current)}&color=${encodeURIComponent(userColor.current)}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket连接成功');
      setConnected(true);
      
      // 开始心跳
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
      
      ws.addEventListener('close', () => clearInterval(pingInterval));
    };
    
    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        handleWSMessage(message);
      } catch (error) {
        console.error('解析消息失败:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket连接关闭');
      setConnected(false);
      
      // 尝试重连
      if (sessionId) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('尝试重连...');
          connectWebSocket(sessionId);
        }, 3000);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };
    
    wsRef.current = ws;
  }, [sessionId]);

  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const handleWSMessage = (message: WSMessage) => {
    switch (message.type) {
      case 'init':
        // 初始化内容
        setContent(message.content || '');
        if (message.collaborators) {
          setCollaborators(message.collaborators);
        }
        break;
        
      case 'join':
        // 用户加入
        toast.info(`${message.nickname} 加入了协作`);
        if (message.collaborators) {
          setCollaborators(message.collaborators);
        }
        break;
        
      case 'leave':
        // 用户离开
        toast.info(`${message.nickname} 离开了协作`);
        if (message.collaborators) {
          setCollaborators(message.collaborators);
        }
        break;
        
      case 'edit':
        // 编辑操作
        handleRemoteEdit(message);
        break;
        
      case 'cursor':
        // 光标移动（可用于显示他人光标位置）
        break;
        
      case 'session_closed':
        toast.warning('协作会话已关闭');
        navigate('/collaboration');
        break;
    }
  };

  const handleRemoteEdit = (message: WSMessage) => {
    // 简化处理：直接使用接收到的内容
    // 实际应用中应该使用操作转换(OT)或CRDT来处理冲突
    if (message.operation === 'replace' && message.content) {
      setContent(message.content);
    }
  };

  const sendEdit = (newContent: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'edit',
        operation: 'replace',
        content: newContent,
        position: { start: 0, end: content.length },
      }));
    }
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    sendEdit(newContent);
  };

  // 创建会话
  const handleCreateSession = async () => {
    if (!newSession.documentId) {
      toast.error('请选择文档');
      return;
    }
    
    try {
      const session = await collaborationApi.createSession({
        document_id: newSession.documentId,
        name: newSession.name || undefined,
      });
      toast.success('协作会话创建成功');
      setShowCreateDialog(false);
      setNewSession({ documentId: '', name: '' });
      navigate(`/collaboration/${session.id}`);
    } catch (error) {
      toast.error('创建失败');
    }
  };

  // 关闭会话
  const handleCloseSession = async () => {
    if (!sessionId) return;
    
    try {
      await collaborationApi.closeSession(sessionId);
      toast.success('协作会话已关闭');
      navigate('/collaboration');
    } catch (error) {
      toast.error('关闭失败');
    }
  };

  // 提交版本
  const handleCommit = async () => {
    if (!sessionId || !commitMessage.trim()) {
      toast.error('请输入版本说明');
      return;
    }
    
    setIsCommitting(true);
    try {
      const result = await collaborationApi.commit(sessionId, commitMessage);
      toast.success(`版本 ${result.version} 提交成功`);
      setShowCommitDialog(false);
      setCommitMessage('');
      loadSession(sessionId); // 刷新版本号
    } catch (error: any) {
      toast.error(error.message || '提交失败');
    } finally {
      setIsCommitting(false);
    }
  };

  // 复制邀请链接
  const copyInviteLink = () => {
    const link = `${window.location.origin}/collaboration/${sessionId}`;
    navigator.clipboard.writeText(link);
    toast.success('邀请链接已复制');
  };

  // 会话列表视图
  if (!sessionId) {
    return (
      <PageContainer
        title="协作编辑"
        description="实时多人协作编辑文档"
        actions={
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <icons.Plus className={`${iconSize.sm} mr-2`} />
                新建协作
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建协作会话</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>选择文档</Label>
                  <Select
                    value={newSession.documentId}
                    onValueChange={(value) => setNewSession({ ...newSession, documentId: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择要协作的文档" />
                    </SelectTrigger>
                    <SelectContent>
                      {documents.map((doc) => (
                        <SelectItem key={doc.id} value={doc.id}>
                          {doc.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>会话名称（可选）</Label>
                  <Input
                    placeholder="如：合同审查协作"
                    value={newSession.name}
                    onChange={(e) => setNewSession({ ...newSession, name: e.target.value })}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>取消</Button>
                <Button onClick={handleCreateSession}>创建</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      >
        {/* 会话列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={cardStyle.interactive}
              onClick={() => navigate(`/collaboration/${session.id}`)}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className={heading.card}>{session.name || '未命名会话'}</h3>
                  <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md ${session.status === 'active' ? statusBadge.success : statusBadge.neutral}`}>
                    {session.status === 'active' ? '进行中' : '已关闭'}
                  </span>
                </div>
                <p className={heading.micro}>
                  文档ID: {session.document_id.substring(0, 8)}...
                </p>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <icons.Users className={iconSize.sm} />
                    <span>{session.active_collaborators} 人协作</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <icons.Clock className={iconSize.sm} />
                    <span>{new Date(session.last_activity_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className={`${cardStyle.base} col-span-full`}>
              <div className="flex flex-col items-center justify-center py-12">
                <icons.FileText className={`${iconSize['2xl']} text-muted-foreground mb-4`} />
                <p className={heading.muted}>暂无协作会话</p>
                <Button className="mt-4" onClick={() => setShowCreateDialog(true)}>
                  <icons.Plus className={`${iconSize.sm} mr-2`} />
                  创建第一个协作会话
                </Button>
              </div>
            </div>
          )}
        </div>
      </PageContainer>
    );
  }

  // 协作编辑视图
  return (
    <div className="h-screen flex flex-col">
      {/* 顶部工具栏 */}
      <div className="border-b p-3 flex items-center justify-between bg-background">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/collaboration')}>
            <icons.ArrowLeft className={`${iconSize.sm} mr-2`} />
            返回
          </Button>
          <div>
            <h1 className="font-medium">{currentSession?.name || '协作编辑'}</h1>
            <p className="text-xs text-muted-foreground">版本 {currentSession?.current_version || 1}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {/* 连接状态 */}
          <div className="flex items-center gap-2">
            {connected ? (
              <Badge className={statusBadge.success}>
                <icons.Wifi className={`${iconSize.xs} mr-1`} />
                已连接
              </Badge>
            ) : (
              <Badge className={statusBadge.error}>
                <icons.WifiOff className={`${iconSize.xs} mr-1`} />
                未连接
              </Badge>
            )}
          </div>
          
          {/* 协作者头像 */}
          <div className="flex items-center -space-x-2">
            <TooltipProvider>
              {collaborators.slice(0, 5).map((collab, index) => (
                <Tooltip key={collab.user_id || index}>
                  <TooltipTrigger asChild>
                    <Avatar
                      className="h-8 w-8 border-2 border-background"
                      style={{ backgroundColor: collab.color }}
                    >
                      <AvatarFallback className="text-white text-xs">
                        {(collab.nickname || '用户').substring(0, 2)}
                      </AvatarFallback>
                    </Avatar>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{collab.nickname || '匿名用户'}</p>
                    <p className="text-xs text-muted-foreground">
                      {collab.is_online ? '在线' : '离线'}
                    </p>
                  </TooltipContent>
                </Tooltip>
              ))}
              {collaborators.length > 5 && (
                <Avatar className="h-8 w-8 border-2 border-background bg-muted">
                  <AvatarFallback className="text-xs">+{collaborators.length - 5}</AvatarFallback>
                </Avatar>
              )}
            </TooltipProvider>
          </div>
          
          {/* 操作按钮 */}
          <div className="flex items-center gap-2">
            <Dialog open={showCommitDialog} onOpenChange={setShowCommitDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className={statusBadge.info}>
                  <icons.Save className={`${iconSize.sm} mr-2`} />
                  提交版本
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>提交新版本 (Git-like Commit)</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>版本说明</Label>
                    <Textarea
                      placeholder="描述本次修订的主要内容..."
                      value={commitMessage}
                      onChange={(e) => setCommitMessage(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCommitDialog(false)}>取消</Button>
                  <Button 
                    onClick={handleCommit} 
                    disabled={isCommitting}
                    className="bg-primary hover:bg-primary/90"
                  >
                    {isCommitting ? <icons.RefreshCw className={`${iconSize.sm} animate-spin mr-2`} /> : <icons.Save className={`${iconSize.sm} mr-2`} />}
                    提交快照
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Button variant="outline" size="sm" onClick={copyInviteLink}>
              <icons.Users className={`${iconSize.sm} mr-2`} />
              邀请
            </Button>
            <Button variant="outline" size="sm" onClick={handleCloseSession}>
              <icons.X className={`${iconSize.sm} mr-2`} />
              关闭会话
            </Button>
          </div>
        </div>
      </div>

      {/* 编辑区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 主编辑区 */}
        <div className="flex-1 bg-muted/10">
          {collabConfig?.enabled ? (
            <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="p-4 bg-primary/5 rounded-full text-primary">
                <icons.Edit3 className={iconSize['2xl']} />
              </div>
              <div>
                <h3 className="text-lg font-bold">Docmost 协作编辑器已就绪</h3>
                <p className="text-sm text-muted-foreground">正在加载外部协作环境...</p>
              </div>
              <iframe 
                src={`${collabConfig.url}/e/${sessionId}?token=temporary_token`}
                className="w-full h-full border-0 rounded-lg shadow-inner bg-background"
                title="Docmost Editor"
              />
            </div>
          ) : (
            <div className="h-full flex flex-col">
              <div className="p-2 border-b bg-muted/5 flex items-center justify-between">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider px-2">内建协作编辑器 (BETA)</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px] font-mono">MD 支持</Badge>
                </div>
              </div>
              <Textarea
                className="flex-1 w-full resize-none font-mono text-sm p-6 focus-visible:ring-0 border-0"
                placeholder="在此输入合同正文或点击“提交版本”保存快照..."
                value={content}
                onChange={handleContentChange}
                disabled={!connected}
              />
            </div>
          )}
        </div>

        {/* 侧边栏 */}
        <div className="w-64 border-l p-4 space-y-4 bg-muted/30">
          <div>
            <h3 className={`${heading.card} mb-2 flex items-center gap-2`}>
              <icons.Users className={iconSize.sm} />
              协作者 ({collaborators.length})
            </h3>
            <div className="space-y-2">
              {collaborators.map((collab, index) => (
                <div
                  key={collab.user_id || index}
                  className="flex items-center gap-2 p-2 rounded-lg bg-background"
                >
                  <Avatar className="h-6 w-6" style={{ backgroundColor: collab.color }}>
                    <AvatarFallback className="text-white text-xs">
                      {(collab.nickname || '用户').substring(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{collab.nickname || '匿名用户'}</p>
                    <p className="text-xs text-muted-foreground">
                      {collab.role === 'owner' ? '所有者' : '编辑者'}
                    </p>
                  </div>
                  <div className={`h-2 w-2 rounded-full ${collab.is_online ? 'bg-emerald-500' : 'bg-muted'}`} />
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className={`${heading.card} mb-2 flex items-center gap-2`}>
              <icons.Clock className={iconSize.sm} />
              版本快照
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
              {[...(Array(currentSession?.current_version || 1))].map((_, i) => (
                <div key={i} className="p-2 rounded border bg-background flex items-center justify-between group cursor-pointer hover:border-primary/30">
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-primary">v{i + 1}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{i === (currentSession?.current_version || 1) - 1 ? '当前工作版本' : '历史快照'}</p>
                  </div>
                  <icons.Eye className={`${iconSize.xs} text-muted-foreground group-hover:text-primary transition-colors`} />
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className={`${heading.card} mb-2 flex items-center gap-2`}>
              <icons.Edit3 className={iconSize.sm} />
              会话信息
            </h3>
            <div className="text-sm space-y-1 text-muted-foreground">
              <p>编辑次数: {currentSession?.total_edits || 0}</p>
              <p>当前版本: {currentSession?.current_version || 1}</p>
              <p>创建时间: {currentSession?.created_at ? new Date(currentSession.created_at).toLocaleString() : '-'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
