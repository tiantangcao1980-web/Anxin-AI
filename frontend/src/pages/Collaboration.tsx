import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
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
import { Skeleton } from '@/components/ui/skeleton';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { toast } from 'sonner';
import { icons } from '@/lib/icons';
import { collaborationApi, documentsApi, type CollaborationSession, type Collaborator } from '@/lib/api';
import { cardStyle, heading, iconSize, statusBadge, statusColor, buttonStyle, spacing } from '@/lib/design-tokens';
import { PageContainer } from '@/components/ui/PageContainer';

// WebSocket消息类型
interface WSMessage {
  type: 'init' | 'join' | 'leave' | 'edit' | 'edit_ack' | 'conflict' | 'cursor' | 'pong' | 'session_closed' | 'editing_status' | 'comment_added' | 'comment_resolved';
  user_id?: string;
  nickname?: string;
  color?: string;
  content?: string;
  version?: number;
  server_version?: number;
  position?: any;
  operation?: string;
  collaborators?: any[];
  message?: string;
  line_range?: { start: number; end: number };
  is_editing?: boolean;
  comment?: CollabComment;
}

// 编辑操作队列项
interface EditOperation {
  id: string;
  operation: 'replace';
  content: string;
  base_version: number;
  timestamp: number;
  status: 'pending' | 'sent' | 'acked';
}

// 版本快照
interface VersionSnapshot {
  id: string;
  version: number;
  content: string;
  description: string;
  created_by: string;
  created_by_name: string;
  created_at: string;
  type: 'manual' | 'auto';
}

// 评论
interface CollabComment {
  id: string;
  content: string;
  author_id: string;
  author_name: string;
  author_color: string;
  line_start: number;
  line_end: number;
  selected_text: string;
  created_at: string;
  resolved: boolean;
  resolved_by?: string;
  replies: CollabCommentReply[];
}

// 评论回复
interface CollabCommentReply {
  id: string;
  content: string;
  author_id: string;
  author_name: string;
  author_color: string;
  created_at: string;
}

// 版本对比行
interface DiffLine {
  type: 'added' | 'removed' | 'unchanged';
  content: string;
  oldLineNo?: number;
  newLineNo?: number;
}

// 编辑用户信息
interface EditingUserInfo {
  nickname: string;
  color: string;
  line_range?: { start: number; end: number };
}

// 保存状态
type SaveStatus = 'saved' | 'saving' | 'unsaved' | 'conflict';

// 侧边面板 Tab
type SidePanelTab = 'collaborators' | 'versions' | 'comments';

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
  const [error, setError] = useState<string | null>(null);

  // 版本控制
  const [showCommitDialog, setShowCommitDialog] = useState(false);
  const [commitMessage, setCommitMessage] = useState('');
  const [isCommitting, setIsCommitting] = useState(false);
  const [collabConfig, setCollabConfig] = useState<any>(null);

  // Delta 编辑模式 - 编辑队列与版本管理
  const [editQueue, setEditQueue] = useState<EditOperation[]>([]);
  const [localVersion, setLocalVersion] = useState(0);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('saved');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const editIdCounter = useRef(0);
  const offlineEditsRef = useRef<EditOperation[]>([]);

  // 版本管理
  const [versionHistory, setVersionHistory] = useState<VersionSnapshot[]>([]);
  const [showSnapshotDialog, setShowSnapshotDialog] = useState(false);
  const [snapshotDescription, setSnapshotDescription] = useState('');
  const [showDiffDialog, setShowDiffDialog] = useState(false);
  const [diffVersions, setDiffVersions] = useState<{ left: VersionSnapshot | null; right: VersionSnapshot | null }>({ left: null, right: null });
  const [diffLines, setDiffLines] = useState<DiffLine[]>([]);
  const [showRollbackConfirm, setShowRollbackConfirm] = useState(false);
  const [rollbackTarget, setRollbackTarget] = useState<VersionSnapshot | null>(null);
  const [isRollingBack, setIsRollingBack] = useState(false);

  // 协作增强
  const [editingUsers, setEditingUsers] = useState(new Map<string, EditingUserInfo>());
  const [showRoleDialog, setShowRoleDialog] = useState(false);
  const [selectedCollaborator, setSelectedCollaborator] = useState<Collaborator | null>(null);
  const [newRole, setNewRole] = useState<string>('editor');

  // 评论系统
  const [comments, setComments] = useState<CollabComment[]>([]);
  const [selectedText, setSelectedText] = useState('');
  const [selectedLineRange, setSelectedLineRange] = useState<{ start: number; end: number } | null>(null);
  const [showAddCommentDialog, setShowAddCommentDialog] = useState(false);
  const [newCommentContent, setNewCommentContent] = useState('');
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const [commentFilter, setCommentFilter] = useState<'all' | 'open' | 'resolved'>('all');

  // 侧边面板
  const [sidePanelTab, setSidePanelTab] = useState<SidePanelTab>('collaborators');

  // 关闭会话确认
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  // WebSocket
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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
    setLoading(true);
    setError(null);
    try {
      const session = await collaborationApi.getSession(id);
      setCurrentSession(session);
      setLocalVersion(session.current_version || 1);

      const collabs = await collaborationApi.getCollaborators(id);
      setCollaborators(collabs);

      // @mock-data FALLBACK - 版本历史
      const verCount = session.current_version || 1;
      const mockVersionHistory: VersionSnapshot[] = Array.from(
        { length: verCount },
        (_, i) => ({
          id: `ver_${i + 1}`,
          version: i + 1,
          content: i === 0 ? '初始版本内容...' : `版本 ${i + 1} 的内容...`,
          description: i === 0 ? '创建文档' : `第 ${i + 1} 次修订`,
          created_by: i % 2 === 0 ? userId.current : 'user_other',
          created_by_name: i % 2 === 0 ? nickname.current : '协作者A',
          created_at: new Date(Date.now() - (verCount - i) * 3600000).toISOString(),
          type: (i % 3 === 0 ? 'auto' : 'manual') as 'auto' | 'manual',
        })
      );
      setVersionHistory(mockVersionHistory);

      // @mock-data FALLBACK - 评论
      const mockComments: CollabComment[] = [
        {
          id: 'comment_1',
          content: '这一段的法律引用需要更新到最新版本',
          author_id: 'user_other',
          author_name: '协作者A',
          author_color: '#4ECDC4',
          line_start: 3,
          line_end: 5,
          selected_text: '根据民法典第一百四十三条',
          created_at: new Date(Date.now() - 7200000).toISOString(),
          resolved: false,
          replies: [
            {
              id: 'reply_1',
              content: '已更新，请确认',
              author_id: userId.current,
              author_name: nickname.current,
              author_color: userColor.current,
              created_at: new Date(Date.now() - 3600000).toISOString(),
            },
          ],
        },
        {
          id: 'comment_2',
          content: '格式不统一，建议统一使用全角标点',
          author_id: 'user_other2',
          author_name: '协作者B',
          author_color: '#45B7D1',
          line_start: 10,
          line_end: 10,
          selected_text: '第二条,甲方应当...',
          created_at: new Date(Date.now() - 1800000).toISOString(),
          resolved: true,
          resolved_by: '协作者B',
          replies: [],
        },
      ];
      setComments(mockComments);
    } catch (err: any) {
      setError(err.message || '加载会话失败');
      toast.error('加载会话失败');
      navigate('/collaboration');
    } finally {
      setLoading(false);
    }
  };

  // WebSocket连接
  const connectWebSocket = useCallback((id: string) => {
    const wsUrl = `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8002'}/api/v1/collaboration/ws/${id}?user_id=${userId.current}&nickname=${encodeURIComponent(nickname.current)}&color=${encodeURIComponent(userColor.current)}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket连接成功');
      setConnected(true);
      setError(null);
      reconnectCountRef.current = 0;

      // 恢复连接后批量发送离线编辑
      flushOfflineEdits();

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
      } catch (err) {
        console.error('解析消息失败:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket连接关闭');
      setConnected(false);

      // 指数退避重连（最大 30 秒）
      if (sessionId) {
        const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 30000);
        reconnectCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`尝试重连（第 ${reconnectCountRef.current} 次）...`);
          connectWebSocket(sessionId);
        }, delay);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket错误:', err);
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
        setContent(message.content || '');
        if (message.version !== undefined) {
          setLocalVersion(message.version);
        }
        if (message.collaborators) {
          setCollaborators(message.collaborators);
        }
        setSaveStatus('saved');
        setLastSavedAt(new Date());
        break;

      case 'join':
        toast.info(`${message.nickname} 加入了协作`);
        if (message.collaborators) {
          setCollaborators(message.collaborators);
        }
        break;

      case 'leave':
        toast.info(`${message.nickname} 离开了协作`);
        if (message.collaborators) {
          setCollaborators(message.collaborators);
        }
        if (message.user_id) {
          setEditingUsers((prev) => {
            const next = new Map(prev);
            next.delete(message.user_id!);
            return next;
          });
        }
        break;

      case 'edit':
        handleRemoteEdit(message);
        break;

      case 'edit_ack':
        handleEditAck(message);
        break;

      case 'conflict':
        handleConflict(message);
        break;

      case 'editing_status':
        handleEditingStatus(message);
        break;

      case 'cursor':
        break;

      case 'comment_added':
        if (message.comment) {
          setComments((prev) => [...prev, message.comment!]);
          toast.info(`${message.nickname} 添加了新评论`);
        }
        break;

      case 'comment_resolved':
        if (message.comment) {
          setComments((prev) => prev.map((c) => c.id === message.comment!.id ? { ...c, resolved: true, resolved_by: message.nickname } : c));
        }
        break;

      case 'session_closed':
        toast.warning('协作会话已关闭');
        navigate('/collaboration');
        break;
    }
  };

  const handleRemoteEdit = (message: WSMessage) => {
    if (message.operation === 'replace' && message.content) {
      setContent(message.content);
      if (message.server_version !== undefined) {
        setLocalVersion(message.server_version);
      }
    }
  };

  const handleEditAck = (message: WSMessage) => {
    if (message.server_version !== undefined) {
      setLocalVersion(message.server_version);
      setEditQueue((prev) => prev.filter((op) => op.status !== 'sent'));
      setSaveStatus('saved');
      setLastSavedAt(new Date());
    }
  };

  const handleConflict = (message: WSMessage) => {
    setSaveStatus('conflict');
    toast.warning('编辑冲突：其他用户同时修改了此内容，已自动合并为服务端版本', {
      duration: 5000,
      action: {
        label: '了解',
        onClick: () => {},
      },
    });
    if (message.content) {
      setContent(message.content);
    }
    if (message.server_version !== undefined) {
      setLocalVersion(message.server_version);
    }
    setEditQueue([]);
  };

  const handleEditingStatus = (message: WSMessage) => {
    if (message.user_id && message.user_id !== userId.current) {
      setEditingUsers((prev) => {
        const next = new Map(prev);
        if (message.is_editing) {
          next.set(message.user_id!, {
            nickname: message.nickname || '匿名用户',
            color: message.color || '#999',
            line_range: message.line_range,
          });
        } else {
          next.delete(message.user_id!);
        }
        return next;
      });
    }
  };

  const sendEdit = (newContent: string) => {
    const opId = `op_${++editIdCounter.current}_${Date.now()}`;
    const operation: EditOperation = {
      id: opId,
      operation: 'replace',
      content: newContent,
      base_version: localVersion,
      timestamp: Date.now(),
      status: 'pending',
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      operation.status = 'sent';
      wsRef.current.send(JSON.stringify({
        type: 'edit',
        operation: 'replace',
        content: newContent,
        base_version: localVersion,
        op_id: opId,
        position: { start: 0, end: content.length },
      }));
      setEditQueue((prev) => [...prev, operation]);
      setSaveStatus('saving');
    } else {
      operation.status = 'pending';
      offlineEditsRef.current.push(operation);
      setEditQueue((prev) => [...prev, operation]);
      setSaveStatus('unsaved');
    }
  };

  const flushOfflineEdits = useCallback(() => {
    if (offlineEditsRef.current.length === 0) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const edits = offlineEditsRef.current;
    offlineEditsRef.current = [];

    const lastEdit = edits[edits.length - 1];
    if (lastEdit) {
      wsRef.current.send(JSON.stringify({
        type: 'edit',
        operation: 'replace',
        content: lastEdit.content,
        base_version: localVersion,
        op_id: lastEdit.id,
        position: { start: 0, end: 0 },
        is_offline_sync: true,
      }));
      setSaveStatus('saving');
      toast.info(`已同步 ${edits.length} 条离线编辑`);
    }
  }, [localVersion, content]);

  const sendEditingStatus = useCallback((isEditing: boolean, lineRange?: { start: number; end: number }) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'editing_status',
        user_id: userId.current,
        nickname: nickname.current,
        color: userColor.current,
        is_editing: isEditing,
        line_range: lineRange,
      }));
    }
  }, []);

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    setSaveStatus('unsaved');

    const cursorPos = e.target.selectionStart;
    const textBefore = newContent.substring(0, cursorPos);
    const currentLine = textBefore.split('\n').length;
    sendEditingStatus(true, { start: currentLine, end: currentLine });

    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      sendEdit(newContent);
      setTimeout(() => sendEditingStatus(false), 2000);
    }, 300);
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
      setShowCloseConfirm(false);
      navigate('/collaboration');
    } catch (err) {
      toast.error('关闭失败');
    }
  };

  // ===== 版本管理功能 =====

  const computeDiff = useCallback((oldText: string, newText: string): DiffLine[] => {
    const oldLines = oldText.split('\n');
    const newLines = newText.split('\n');
    const result: DiffLine[] = [];
    let oldIdx = 0;
    let newIdx = 0;

    while (oldIdx < oldLines.length || newIdx < newLines.length) {
      if (oldIdx < oldLines.length && newIdx < newLines.length) {
        if (oldLines[oldIdx] === newLines[newIdx]) {
          result.push({ type: 'unchanged', content: oldLines[oldIdx], oldLineNo: oldIdx + 1, newLineNo: newIdx + 1 });
          oldIdx++;
          newIdx++;
        } else {
          result.push({ type: 'removed', content: oldLines[oldIdx], oldLineNo: oldIdx + 1 });
          result.push({ type: 'added', content: newLines[newIdx], newLineNo: newIdx + 1 });
          oldIdx++;
          newIdx++;
        }
      } else if (oldIdx < oldLines.length) {
        result.push({ type: 'removed', content: oldLines[oldIdx], oldLineNo: oldIdx + 1 });
        oldIdx++;
      } else {
        result.push({ type: 'added', content: newLines[newIdx], newLineNo: newIdx + 1 });
        newIdx++;
      }
    }
    return result;
  }, []);

  const handleCreateSnapshot = async () => {
    if (!snapshotDescription.trim()) {
      toast.error('请输入快照描述');
      return;
    }
    setIsCommitting(true);
    try {
      // @mock-data FALLBACK
      const newVersion = localVersion + 1;
      const snapshot: VersionSnapshot = {
        id: `ver_${newVersion}`,
        version: newVersion,
        content: content,
        description: snapshotDescription,
        created_by: userId.current,
        created_by_name: nickname.current,
        created_at: new Date().toISOString(),
        type: 'manual',
      };
      setVersionHistory((prev) => [...prev, snapshot]);
      setLocalVersion(newVersion);
      setSaveStatus('saved');
      setLastSavedAt(new Date());
      toast.success(`快照 v${newVersion} 创建成功`);
      setShowSnapshotDialog(false);
      setSnapshotDescription('');
    } catch (err: any) {
      toast.error(err.message || '创建快照失败');
    } finally {
      setIsCommitting(false);
    }
  };

  const openDiffView = (left: VersionSnapshot, right: VersionSnapshot) => {
    const lines = computeDiff(left.content, right.content);
    setDiffVersions({ left, right });
    setDiffLines(lines);
    setShowDiffDialog(true);
  };

  const handleRollback = async () => {
    if (!rollbackTarget) return;
    setIsRollingBack(true);
    try {
      // @mock-data FALLBACK
      setContent(rollbackTarget.content);
      setLocalVersion(rollbackTarget.version);
      toast.success(`已回滚到 v${rollbackTarget.version}`);
      setShowRollbackConfirm(false);
      setRollbackTarget(null);
    } catch (err: any) {
      toast.error(err.message || '回滚失败');
    } finally {
      setIsRollingBack(false);
    }
  };

  // ===== 评论功能 =====

  const handleAddComment = () => {
    if (!newCommentContent.trim()) {
      toast.error('请输入评论内容');
      return;
    }
    // @mock-data FALLBACK
    const newComment: CollabComment = {
      id: `comment_${Date.now()}`,
      content: newCommentContent,
      author_id: userId.current,
      author_name: nickname.current,
      author_color: userColor.current,
      line_start: selectedLineRange?.start || 1,
      line_end: selectedLineRange?.end || 1,
      selected_text: selectedText,
      created_at: new Date().toISOString(),
      resolved: false,
      replies: [],
    };
    setComments((prev) => [...prev, newComment]);
    setNewCommentContent('');
    setShowAddCommentDialog(false);
    setSelectedText('');
    setSelectedLineRange(null);
    toast.success('评论已添加');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'comment_added', comment: newComment, nickname: nickname.current }));
    }
  };

  const handleReplyComment = (commentId: string) => {
    if (!replyContent.trim()) return;
    const reply: CollabCommentReply = {
      id: `reply_${Date.now()}`,
      content: replyContent,
      author_id: userId.current,
      author_name: nickname.current,
      author_color: userColor.current,
      created_at: new Date().toISOString(),
    };
    setComments((prev) => prev.map((c) => c.id === commentId ? { ...c, replies: [...c.replies, reply] } : c));
    setReplyContent('');
    setReplyingTo(null);
    toast.success('回复已发送');
  };

  const handleResolveComment = (commentId: string) => {
    setComments((prev) => prev.map((c) => c.id === commentId ? { ...c, resolved: true, resolved_by: nickname.current } : c));
    toast.success('评论已标记为已解决');
  };

  const handleTextSelection = () => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    if (start === end) return;

    const selected = content.substring(start, end);
    if (selected.trim().length === 0) return;

    const textBefore = content.substring(0, start);
    const lineStart = textBefore.split('\n').length;
    const textToEnd = content.substring(0, end);
    const lineEnd = textToEnd.split('\n').length;

    setSelectedText(selected);
    setSelectedLineRange({ start: lineStart, end: lineEnd });
  };

  const handleChangeRole = async () => {
    if (!selectedCollaborator || !sessionId) return;
    try {
      // @mock-data FALLBACK
      setCollaborators((prev) =>
        prev.map((c) => c.user_id === selectedCollaborator.user_id ? { ...c, role: newRole } : c)
      );
      toast.success(`已将 ${selectedCollaborator.nickname} 的角色更改为 ${newRole === 'editor' ? '编辑者' : newRole === 'commenter' ? '评论者' : '查看者'}`);
      setShowRoleDialog(false);
      setSelectedCollaborator(null);
    } catch (err: any) {
      toast.error('角色更改失败');
    }
  };

  // 计算派生数据
  const onlineCollaborators = useMemo(() => collaborators.filter((c) => c.is_online), [collaborators]);
  const unresolvedCommentCount = useMemo(() => comments.filter((c) => !c.resolved).length, [comments]);
  const filteredComments = useMemo(() => {
    if (commentFilter === 'all') return comments;
    if (commentFilter === 'open') return comments.filter((c) => !c.resolved);
    return comments.filter((c) => c.resolved);
  }, [comments, commentFilter]);
  const isOwner = useMemo(() => {
    return collaborators.some((c) => c.user_id === userId.current && c.role === 'owner');
  }, [collaborators]);

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
      loadSession(sessionId);
    } catch (error: any) {
      toast.error(error.message || '提交失败');
    } finally {
      setIsCommitting(false);
    }
  };

  const copyInviteLink = () => {
    const link = `${window.location.origin}/collaboration/${sessionId}`;
    navigator.clipboard.writeText(link);
    toast.success('邀请链接已复制');
  };

  // ===== 会话列表视图 =====
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

  // ===== Loading 骨架屏 =====
  if (loading && !currentSession) {
    return (
      <div className="h-screen flex flex-col">
        <div className="border-b p-3 flex items-center gap-4 bg-background">
          <Skeleton className="h-8 w-16" />
          <div className="space-y-1">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
          <div className="flex-1" />
          <div className="flex gap-2">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-8 w-8 rounded-full" />
          </div>
        </div>
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 p-6 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-full" />
          </div>
          <div className="w-72 border-l p-4 space-y-4 bg-muted/30">
            <Skeleton className="h-5 w-24" />
            <div className="space-y-2">
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
            <Skeleton className="h-5 w-24" />
            <div className="space-y-2">
              <Skeleton className="h-12 w-full rounded" />
              <Skeleton className="h-12 w-full rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ===== Error 状态 =====
  if (error && !currentSession) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className={`mx-auto p-4 rounded-full ${statusColor.error} w-fit`}>
            <icons.AlertCircle className={iconSize.xl} />
          </div>
          <h2 className={heading.section}>加载失败</h2>
          <p className={heading.muted}>{error}</p>
          <div className="flex gap-2 justify-center">
            <Button variant="outline" onClick={() => navigate('/collaboration')}>
              <icons.ArrowLeft className={`${iconSize.sm} mr-2`} />
              返回列表
            </Button>
            <Button onClick={() => sessionId && loadSession(sessionId)}>
              <icons.RefreshCw className={`${iconSize.sm} mr-2`} />
              重试
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ===== 协作编辑视图 =====
  return (
    <div className="h-screen flex flex-col">
      {/* WebSocket 断开警告条 */}
      {!connected && currentSession && (
        <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
            <icons.WifiOff className={iconSize.sm} />
            <span className="text-sm font-medium">连接已断开，编辑内容将在恢复连接后自动同步</span>
            {offlineEditsRef.current.length > 0 && (
              <Badge className={statusBadge.warning}>{offlineEditsRef.current.length} 条待同步</Badge>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            className="text-amber-700 border-amber-300"
            onClick={() => sessionId && connectWebSocket(sessionId)}
          >
            <icons.RefreshCw className={`${iconSize.sm} mr-1`} />
            重新连接
          </Button>
        </div>
      )}

      {/* 冲突提示条 */}
      {saveStatus === 'conflict' && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-950/30 border-b border-red-200 dark:border-red-800 flex items-center gap-2 text-red-700 dark:text-red-400">
          <icons.AlertTriangle className={iconSize.sm} />
          <span className="text-sm font-medium">检测到编辑冲突，内容已同步为服务端最新版本</span>
          <Button variant="ghost" size="sm" onClick={() => setSaveStatus('saved')}>
            <icons.X className={iconSize.xs} />
          </Button>
        </div>
      )}

      {/* 顶部工具栏 */}
      <div className="border-b p-3 flex items-center justify-between bg-background">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/collaboration')}>
            <icons.ArrowLeft className={`${iconSize.sm} mr-2`} />
            返回
          </Button>
          <div>
            <h1 className="font-medium">{currentSession?.name || '协作编辑'}</h1>
            <p className="text-xs text-muted-foreground">v{localVersion}</p>
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

          {/* 在线协作者头像列表 */}
          <div className="flex items-center -space-x-2">
            <TooltipProvider>
              {onlineCollaborators.slice(0, 5).map((collab, index) => (
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
                      {collab.role === 'owner' ? '所有者' : collab.role === 'editor' ? '编辑者' : collab.role === 'commenter' ? '评论者' : '查看者'} - 在线
                    </p>
                  </TooltipContent>
                </Tooltip>
              ))}
              {onlineCollaborators.length > 5 && (
                <Avatar className="h-8 w-8 border-2 border-background bg-muted">
                  <AvatarFallback className="text-xs">+{onlineCollaborators.length - 5}</AvatarFallback>
                </Avatar>
              )}
            </TooltipProvider>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-2">
            <Dialog open={showSnapshotDialog} onOpenChange={setShowSnapshotDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <icons.Camera className={`${iconSize.sm} mr-2`} />
                  创建快照
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>创建版本快照</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>快照描述</Label>
                    <Textarea
                      placeholder="描述当前快照的内容变更..."
                      value={snapshotDescription}
                      onChange={(e) => setSnapshotDescription(e.target.value)}
                    />
                  </div>
                  <p className={heading.micro}>当前版本：v{localVersion}，新快照将创建 v{localVersion + 1}</p>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowSnapshotDialog(false)}>取消</Button>
                  <Button onClick={handleCreateSnapshot} disabled={isCommitting}>
                    {isCommitting ? <icons.RefreshCw className={`${iconSize.sm} animate-spin mr-2`} /> : <icons.Camera className={`${iconSize.sm} mr-2`} />}
                    创建快照
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

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
            <Button variant="outline" size="sm" onClick={() => setShowCloseConfirm(true)}>
              <icons.X className={`${iconSize.sm} mr-2`} />
              关闭会话
            </Button>
          </div>
        </div>
      </div>

      {/* 正在编辑指示条 */}
      {editingUsers.size > 0 && (
        <div className="px-4 py-1.5 bg-primary/5 border-b border-primary/10 flex items-center gap-2">
          <icons.Edit className={`${iconSize.xs} text-primary animate-pulse`} />
          <span className="text-xs text-primary">
            {Array.from(editingUsers.values()).map((u) => u.nickname).join(', ')} 正在编辑...
          </span>
        </div>
      )}

      {/* 编辑区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 主编辑区 */}
        <div className="flex-1 flex flex-col bg-muted/10">
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
            <div className="flex-1 flex flex-col">
              {/* 编辑器顶栏 */}
              <div className="p-2 border-b bg-muted/5 flex items-center justify-between">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider px-2">内建协作编辑器 (BETA)</span>
                <div className="flex items-center gap-2">
                  {selectedText && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-[10px] h-6"
                      onClick={() => setShowAddCommentDialog(true)}
                    >
                      <icons.MessageSquare className={iconSize.xs} />
                      <span className="ml-1">添加评论</span>
                    </Button>
                  )}
                  <Badge variant="outline" className="text-[10px] font-mono">MD 支持</Badge>
                </div>
              </div>

              {/* 编辑器主体 */}
              <div className="flex-1 relative">
                {/* 其他用户编辑行高亮背景层 */}
                {editingUsers.size > 0 && (
                  <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden" style={{ padding: '24px' }}>
                    {Array.from(editingUsers.entries()).map(([uid, info]) => {
                      if (!info.line_range) return null;
                      const lineHeight = 20;
                      const top = (info.line_range.start - 1) * lineHeight;
                      const height = (info.line_range.end - info.line_range.start + 1) * lineHeight;
                      return (
                        <div
                          key={uid}
                          className="absolute left-0 right-0 rounded-sm transition-all"
                          style={{
                            top: `${top}px`,
                            height: `${height}px`,
                            backgroundColor: info.color + '15',
                            borderLeft: `3px solid ${info.color}40`,
                          }}
                        />
                      );
                    })}
                  </div>
                )}
                <Textarea
                  className="absolute inset-0 w-full h-full resize-none font-mono text-sm p-6 focus-visible:ring-0 border-0 bg-transparent z-10"
                  placeholder="在此输入合同正文..."
                  value={content}
                  onChange={handleContentChange}
                  onMouseUp={handleTextSelection}
                  onKeyUp={handleTextSelection}
                  disabled={!connected && offlineEditsRef.current.length > 50}
                />
              </div>

              {/* 底部状态栏 */}
              <div className="px-4 py-1.5 border-t bg-muted/5 flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    {saveStatus === 'saved' && (
                      <>
                        <icons.CheckCircle className={`${iconSize.xs} text-emerald-500`} />
                        <span className="text-emerald-600">已保存</span>
                      </>
                    )}
                    {saveStatus === 'saving' && (
                      <>
                        <icons.RefreshCw className={`${iconSize.xs} animate-spin text-primary`} />
                        <span className="text-primary">保存中...</span>
                      </>
                    )}
                    {saveStatus === 'unsaved' && (
                      <>
                        <icons.AlertTriangle className={`${iconSize.xs} text-amber-500`} />
                        <span className="text-amber-600">未保存</span>
                      </>
                    )}
                    {saveStatus === 'conflict' && (
                      <>
                        <icons.AlertCircle className={`${iconSize.xs} text-red-500`} />
                        <span className="text-red-600">冲突</span>
                      </>
                    )}
                  </span>
                  <span className="flex items-center gap-1">
                    <icons.GitBranch className={iconSize.xs} />
                    v{localVersion}
                  </span>
                  <span className="flex items-center gap-1">
                    <icons.Users className={iconSize.xs} />
                    {onlineCollaborators.length} 人在线
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  {editQueue.length > 0 && (
                    <span className="flex items-center gap-1 text-amber-600">
                      <icons.Upload className={iconSize.xs} />
                      {editQueue.length} 条待同步
                    </span>
                  )}
                  {lastSavedAt && (
                    <span>最后保存：{lastSavedAt.toLocaleTimeString()}</span>
                  )}
                  <span>{content.split('\n').length} 行</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 侧边栏 - 带 Tab 切换 */}
        <div className="w-72 border-l flex flex-col bg-muted/30">
          <div className="flex border-b">
            <button
              className={`flex-1 px-3 py-2.5 text-xs font-medium transition-colors flex items-center justify-center gap-1 ${sidePanelTab === 'collaborators' ? 'text-primary border-b-2 border-primary bg-primary/5' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setSidePanelTab('collaborators')}
            >
              <icons.Users className={iconSize.xs} />
              协作者
            </button>
            <button
              className={`flex-1 px-3 py-2.5 text-xs font-medium transition-colors flex items-center justify-center gap-1 ${sidePanelTab === 'versions' ? 'text-primary border-b-2 border-primary bg-primary/5' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setSidePanelTab('versions')}
            >
              <icons.Clock className={iconSize.xs} />
              版本
            </button>
            <button
              className={`flex-1 px-3 py-2.5 text-xs font-medium transition-colors flex items-center justify-center gap-1 relative ${sidePanelTab === 'comments' ? 'text-primary border-b-2 border-primary bg-primary/5' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setSidePanelTab('comments')}
            >
              <icons.MessageSquare className={iconSize.xs} />
              评论
              {unresolvedCommentCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center px-1">
                  {unresolvedCommentCount}
                </span>
              )}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* 协作者面板 */}
            {sidePanelTab === 'collaborators' && (
              <>
                <div>
                  <h3 className={`${heading.card} mb-2 flex items-center gap-2`}>
                    <icons.Users className={iconSize.sm} />
                    协作者 ({collaborators.length})
                  </h3>
                  <div className="space-y-2">
                    {collaborators.map((collab, index) => (
                      <div
                        key={collab.user_id || index}
                        className="flex items-center gap-2 p-2 rounded-lg bg-background group"
                      >
                        <Avatar className="h-6 w-6" style={{ backgroundColor: collab.color }}>
                          <AvatarFallback className="text-white text-xs">
                            {(collab.nickname || '用户').substring(0, 1)}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate">{collab.nickname || '匿名用户'}</p>
                          <p className="text-xs text-muted-foreground">
                            {collab.role === 'owner' ? '所有者' : collab.role === 'editor' ? '编辑者' : collab.role === 'commenter' ? '评论者' : '查看者'}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          {isOwner && collab.user_id !== userId.current && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={() => {
                                setSelectedCollaborator(collab);
                                setNewRole(collab.role || 'editor');
                                setShowRoleDialog(true);
                              }}
                            >
                              <icons.Edit className={iconSize.xs} />
                            </Button>
                          )}
                          <div className={`h-2 w-2 rounded-full ${collab.is_online ? 'bg-emerald-500' : 'bg-muted'}`} />
                        </div>
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
                    <p>当前版本: v{localVersion}</p>
                    <p>创建时间: {currentSession?.created_at ? new Date(currentSession.created_at).toLocaleString() : '-'}</p>
                  </div>
                </div>
              </>
            )}

            {/* 版本管理面板 */}
            {sidePanelTab === 'versions' && (
              <>
                <div className="flex items-center justify-between">
                  <h3 className={`${heading.card} flex items-center gap-2`}>
                    <icons.Clock className={iconSize.sm} />
                    版本历史
                  </h3>
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setShowSnapshotDialog(true)}>
                    <icons.Plus className={iconSize.xs} />
                  </Button>
                </div>
                <div className="relative">
                  <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />
                  <div className="space-y-1">
                    {[...versionHistory].reverse().map((ver, idx) => (
                      <div key={ver.id} className="relative pl-8 group">
                        <div className={`absolute left-1.5 top-3 w-3 h-3 rounded-full border-2 ${idx === 0 ? 'bg-primary border-primary' : 'bg-background border-border group-hover:border-primary/50'} transition-colors`} />
                        <div className="p-2 rounded-lg bg-background border border-transparent hover:border-primary/20 transition-all cursor-pointer">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold text-primary">v{ver.version}</span>
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                              {ver.type === 'manual' ? '手动' : '自动'}
                            </Badge>
                          </div>
                          <p className="text-[11px] text-foreground truncate">{ver.description}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-muted-foreground">{ver.created_by_name}</span>
                            <span className="text-[10px] text-muted-foreground">{new Date(ver.created_at).toLocaleString()}</span>
                          </div>
                          <div className="flex gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                            {idx > 0 && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 text-[10px] px-1.5"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const prevVer = [...versionHistory].reverse()[idx - 1] || versionHistory[0];
                                  openDiffView(ver, prevVer);
                                }}
                              >
                                <icons.FileText className={iconSize.xs} />
                                <span className="ml-0.5">对比</span>
                              </Button>
                            )}
                            {idx > 0 && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 text-[10px] px-1.5 text-amber-600 hover:text-amber-700"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setRollbackTarget(ver);
                                  setShowRollbackConfirm(true);
                                }}
                              >
                                <icons.RotateCcw className={iconSize.xs} />
                                <span className="ml-0.5">回滚</span>
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* 评论面板 */}
            {sidePanelTab === 'comments' && (
              <>
                <div className="flex items-center justify-between">
                  <h3 className={`${heading.card} flex items-center gap-2`}>
                    <icons.MessageSquare className={iconSize.sm} />
                    评论 ({comments.length})
                  </h3>
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setShowAddCommentDialog(true)}>
                    <icons.Plus className={iconSize.xs} />
                  </Button>
                </div>
                <div className="flex gap-1">
                  {(['all', 'open', 'resolved'] as const).map((f) => (
                    <button
                      key={f}
                      className={`px-2 py-1 rounded text-[10px] font-medium transition-colors ${commentFilter === f ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                      onClick={() => setCommentFilter(f)}
                    >
                      {f === 'all' ? '全部' : f === 'open' ? '待解决' : '已解决'}
                    </button>
                  ))}
                </div>
                <div className="space-y-3">
                  {filteredComments.length === 0 && (
                    <div className="text-center py-6">
                      <icons.MessageSquare className={`${iconSize.lg} text-muted-foreground mx-auto mb-2`} />
                      <p className={heading.micro}>暂无评论</p>
                    </div>
                  )}
                  {filteredComments.map((comment) => (
                    <div
                      key={comment.id}
                      className={`p-3 rounded-lg border ${comment.resolved ? 'bg-muted/30 border-border opacity-70' : 'bg-background border-border'}`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Avatar className="h-5 w-5" style={{ backgroundColor: comment.author_color }}>
                          <AvatarFallback className="text-white text-[8px]">
                            {comment.author_name.substring(0, 1)}
                          </AvatarFallback>
                        </Avatar>
                        <span className="text-xs font-medium">{comment.author_name}</span>
                        <span className="text-[10px] text-muted-foreground">{new Date(comment.created_at).toLocaleString()}</span>
                      </div>
                      {comment.selected_text && (
                        <div className="mb-2 px-2 py-1 bg-primary/5 border-l-2 border-primary/30 rounded text-[11px] text-muted-foreground italic truncate">
                          L{comment.line_start}-{comment.line_end}: {comment.selected_text}
                        </div>
                      )}
                      <p className="text-sm">{comment.content}</p>
                      {comment.resolved && (
                        <div className="mt-2 flex items-center gap-1 text-emerald-600">
                          <icons.CheckCircle className={iconSize.xs} />
                          <span className="text-[10px]">已由 {comment.resolved_by} 解决</span>
                        </div>
                      )}
                      {comment.replies.length > 0 && (
                        <div className="mt-2 pl-3 border-l-2 border-muted space-y-2">
                          {comment.replies.map((reply) => (
                            <div key={reply.id} className="space-y-1">
                              <div className="flex items-center gap-1">
                                <Avatar className="h-4 w-4" style={{ backgroundColor: reply.author_color }}>
                                  <AvatarFallback className="text-white text-[7px]">
                                    {reply.author_name.substring(0, 1)}
                                  </AvatarFallback>
                                </Avatar>
                                <span className="text-[10px] font-medium">{reply.author_name}</span>
                                <span className="text-[9px] text-muted-foreground">{new Date(reply.created_at).toLocaleString()}</span>
                              </div>
                              <p className="text-[11px]">{reply.content}</p>
                            </div>
                          ))}
                        </div>
                      )}
                      {!comment.resolved && (
                        <div className="mt-2 flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-[10px] px-2"
                            onClick={() => {
                              setReplyingTo(replyingTo === comment.id ? null : comment.id);
                              setReplyContent('');
                            }}
                          >
                            回复
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-[10px] px-2 text-emerald-600"
                            onClick={() => handleResolveComment(comment.id)}
                          >
                            <icons.Check className={iconSize.xs} />
                            <span className="ml-0.5">已解决</span>
                          </Button>
                        </div>
                      )}
                      {replyingTo === comment.id && (
                        <div className="mt-2 flex gap-1">
                          <Input
                            placeholder="输入回复..."
                            value={replyContent}
                            onChange={(e) => setReplyContent(e.target.value)}
                            className="h-7 text-xs"
                            onKeyDown={(e) => e.key === 'Enter' && handleReplyComment(comment.id)}
                          />
                          <Button size="sm" className="h-7 px-2 text-xs" onClick={() => handleReplyComment(comment.id)}>
                            <icons.Send className={iconSize.xs} />
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ===== 对话框集合 ===== */}

      {/* 添加评论对话框 */}
      <Dialog open={showAddCommentDialog} onOpenChange={setShowAddCommentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加评论</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedText && (
              <div className="px-3 py-2 bg-primary/5 border-l-2 border-primary/30 rounded text-sm text-muted-foreground italic">
                {selectedLineRange && <span className="font-mono text-xs mr-2">L{selectedLineRange.start}-{selectedLineRange.end}</span>}
                {selectedText.length > 100 ? selectedText.substring(0, 100) + '...' : selectedText}
              </div>
            )}
            <div className="space-y-2">
              <Label>评论内容</Label>
              <Textarea
                placeholder="输入评论..."
                value={newCommentContent}
                onChange={(e) => setNewCommentContent(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddCommentDialog(false)}>取消</Button>
            <Button onClick={handleAddComment}>
              <icons.Send className={`${iconSize.sm} mr-2`} />
              添加评论
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 角色修改对话框 */}
      <Dialog open={showRoleDialog} onOpenChange={setShowRoleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>修改角色 - {selectedCollaborator?.nickname}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>选择角色</Label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="editor">编辑者 - 可编辑文档</SelectItem>
                  <SelectItem value="commenter">评论者 - 仅可评论</SelectItem>
                  <SelectItem value="viewer">查看者 - 仅可查看</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRoleDialog(false)}>取消</Button>
            <Button onClick={handleChangeRole}>确认修改</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 版本对比对话框 */}
      <Dialog open={showDiffDialog} onOpenChange={setShowDiffDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>
              版本对比：v{diffVersions.left?.version} vs v{diffVersions.right?.version}
            </DialogTitle>
          </DialogHeader>
          <div className="flex gap-0 border rounded-lg overflow-hidden max-h-[60vh] overflow-y-auto">
            <div className="flex-1 font-mono text-xs">
              <div className="px-3 py-1.5 bg-muted border-b text-xs font-medium text-muted-foreground sticky top-0 z-10">
                v{diffVersions.left?.version} ({diffVersions.left?.description})
              </div>
              <div className="divide-y divide-border/50">
                {diffLines.map((line, i) => (
                  <div
                    key={`left-${i}`}
                    className={`flex ${
                      line.type === 'removed' ? 'bg-red-50 dark:bg-red-950/20' :
                      line.type === 'added' ? 'bg-transparent' :
                      ''
                    }`}
                  >
                    <span className="w-8 shrink-0 text-right pr-2 text-muted-foreground/50 select-none border-r">
                      {line.oldLineNo || ''}
                    </span>
                    <span className={`flex-1 px-2 py-0.5 whitespace-pre-wrap break-all ${line.type === 'added' ? 'invisible' : ''}`}>
                      {line.type === 'removed' && <span className="text-red-600 font-bold mr-1">-</span>}
                      {line.content}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="w-px bg-border" />
            <div className="flex-1 font-mono text-xs">
              <div className="px-3 py-1.5 bg-muted border-b text-xs font-medium text-muted-foreground sticky top-0 z-10">
                v{diffVersions.right?.version} ({diffVersions.right?.description})
              </div>
              <div className="divide-y divide-border/50">
                {diffLines.map((line, i) => (
                  <div
                    key={`right-${i}`}
                    className={`flex ${
                      line.type === 'added' ? 'bg-emerald-50 dark:bg-emerald-950/20' :
                      line.type === 'removed' ? 'bg-transparent' :
                      ''
                    }`}
                  >
                    <span className="w-8 shrink-0 text-right pr-2 text-muted-foreground/50 select-none border-r">
                      {line.newLineNo || ''}
                    </span>
                    <span className={`flex-1 px-2 py-0.5 whitespace-pre-wrap break-all ${line.type === 'removed' ? 'invisible' : ''}`}>
                      {line.type === 'added' && <span className="text-emerald-600 font-bold mr-1">+</span>}
                      {line.content}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDiffDialog(false)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 回滚确认 */}
      <ConfirmDialog
        open={showRollbackConfirm}
        onOpenChange={setShowRollbackConfirm}
        title="确认回滚"
        description={`确定要将文档回滚到 v${rollbackTarget?.version} 吗？当前未保存的修改将丢失。`}
        confirmText="确认回滚"
        onConfirm={handleRollback}
        destructive
        loading={isRollingBack}
      />

      {/* 关闭会话确认 */}
      <ConfirmDialog
        open={showCloseConfirm}
        onOpenChange={setShowCloseConfirm}
        title="关闭协作会话"
        description="关闭后所有协作者将断开连接，未保存的更改可能丢失。确定要关闭此会话吗？"
        confirmText="关闭会话"
        onConfirm={handleCloseSession}
        destructive
      />
    </div>
  );
}
