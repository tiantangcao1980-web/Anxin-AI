import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { documentsApi, Document } from '@/lib/api';
import { toast } from 'sonner';
import { DocumentEditor } from './DocumentEditor';

const DOC_TYPE_LABELS: Record<string, string> = {
  contract: '合同协议',
  letter: '催告函件',
  litigation: '诉讼文书',
  opinion: '法律意见书',
  report: '调研报告',
  other: '其他文档',
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

function getFileType(mimeType?: string): string {
  if (!mimeType) return 'other';
  if (mimeType.includes('pdf')) return 'pdf';
  if (mimeType.includes('word') || mimeType.includes('document')) return 'docx';
  if (mimeType.includes('excel') || mimeType.includes('sheet')) return 'xlsx';
  return 'other';
}

export function MyDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Editor State
  const [showEditor, setShowEditor] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [searchQuery, filterType]); // Reload when search or filter changes

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const params: any = { page: 1, page_size: 50 };
      if (filterType !== 'all') {
          params.doc_type = filterType;
      }
      // Note: Backend list API might not support 'search' param yet,
      // if not, we might need to filter client-side or add backend support.
      // For now, let's assume we filter client-side if backend doesn't support it,
      // OR we just fetch all and filter.
      // But documentsApi.list supports doc_type.

      const response = await documentsApi.list(params);

      let items = response.items;
      if (searchQuery) {
          const lowerQuery = searchQuery.toLowerCase();
          items = items.filter(doc =>
              doc.name.toLowerCase().includes(lowerQuery) ||
              (doc.ai_summary && doc.ai_summary.toLowerCase().includes(lowerQuery))
          );
      }

      setDocuments(items);
      setTotal(response.total); // This might be inaccurate if we filter client-side
    } catch (error: any) {
      toast.error(error.message || '加载文档失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleCreateClick = () => {
    setEditingDoc(null);
    setShowEditor(true);
  };

  const handleEditClick = (doc: Document) => {
    setEditingDoc(doc);
    setShowEditor(true);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const newDoc = await documentsApi.upload(file, { doc_type: 'other' });
      setDocuments(prev => [newDoc, ...prev]);
      setTotal(prev => prev + 1);
      toast.success('文档上传成功');
    } catch (error: any) {
      toast.error(error.message || '上传失败');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个文档吗？')) return;

    try {
      await documentsApi.delete(id);
      setDocuments(prev => prev.filter(d => d.id !== id));
      setTotal(prev => prev - 1);
      toast.success('文档已删除');
    } catch (error: any) {
      toast.error(error.message || '删除失败');
    }
  };

  const handleAnalyze = async (id: string) => {
    setAnalyzingId(id);
    try {
      const result = await documentsApi.analyze(id);
      toast.success('文档分析完成');
      // 刷新文档列表以获取更新的摘要
      loadDocuments();
    } catch (error: any) {
      toast.error(error.message || '分析失败');
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleEditorSave = (savedDoc: Document) => {
    // 检查是新建还是更新
    setDocuments(prev => {
        const exists = prev.find(d => d.id === savedDoc.id);
        if (exists) {
            return prev.map(d => d.id === savedDoc.id ? savedDoc : d);
        } else {
            return [savedDoc, ...prev];
        }
    });
    if (!documents.find(d => d.id === savedDoc.id)) {
        setTotal(prev => prev + 1);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6 bg-muted">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.doc,.docx,.txt,.md,.xlsx,.xls,.csv"
        className="hidden"
      />

      {/* Editor Modal */}
      <AnimatePresence>
        {showEditor && (
            <DocumentEditor
                initialDoc={editingDoc}
                onClose={() => setShowEditor(false)}
                onSave={handleEditorSave}
            />
        )}
      </AnimatePresence>

      <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-4 lg:mb-6 gap-3">
        <div>
          <h3 className="font-semibold text-foreground">我的文档</h3>
          <p className="text-sm text-muted-foreground mt-1">{total} 个文档</p>
        </div>

        <div className="flex flex-1 max-w-xl gap-2 items-center">
            <div className="relative flex-1">
                <icons.Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                    type="text"
                    placeholder="搜索文档..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
            </div>
            <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-3 py-2 bg-background border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            >
                <option value="all">全部类型</option>
                {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                ))}
            </select>
        </div>

        <div className="flex gap-2">
          <button
            onClick={loadDocuments}
            disabled={loading}
            className="p-2.5 bg-background text-primary rounded-xl hover:bg-primary/5 transition-colors text-sm font-medium shadow-sm active:scale-98 disabled:opacity-50"
          >
            <icons.RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleCreateClick}
            className="px-4 py-2.5 bg-background text-primary border border-primary/20 rounded-xl hover:bg-primary/5 transition-colors text-sm font-medium flex items-center justify-center gap-2 shadow-sm active:scale-98"
          >
            <icons.Plus className="w-4 h-4" />
            新建文档
          </button>

          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="px-4 py-2.5 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 transition-colors text-sm font-medium flex items-center justify-center gap-2 shadow-sm active:scale-98 disabled:opacity-50"
          >
            {uploading ? (
              <icons.Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <icons.Upload className="w-4 h-4" />
            )}
            上传文档
          </button>
        </div>
      </div>

      {/* Documents List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <icons.Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 bg-background rounded-2xl border border-border">
          <icons.FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">暂无文档</p>
          <div className="flex justify-center gap-4 mt-4">
            <button
                onClick={handleCreateClick}
                className="text-primary hover:underline"
            >
                新建文档
            </button>
            <button
                onClick={handleUploadClick}
                className="text-primary hover:underline"
            >
                上传文件
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2 lg:space-y-3">
          {documents.map((doc, index) => {
            const fileType = getFileType(doc.mime_type);
            return (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between p-3 lg:p-4 bg-background border border-border rounded-2xl hover:border-primary hover:shadow-lg transition-all group active:scale-[0.99]"
              >
                <div className="flex items-center gap-3 lg:gap-4 flex-1 min-w-0">
                  {/* Icon */}
                  <div className={`w-10 h-10 lg:w-12 lg:h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    fileType === 'pdf' ? 'bg-destructive/10' : 'bg-primary/10'
                  }`}>
                    <icons.FileText className={`w-5 h-5 lg:w-6 lg:h-6 ${
                      fileType === 'pdf' ? 'text-destructive' : 'text-primary'
                    }`} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-foreground truncate text-sm lg:text-base">{doc.name}</h4>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1 flex-wrap">
                      <div className="flex items-center gap-1">
                        <icons.Folder className="w-3 h-3" />
                        <span>{DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}</span>
                      </div>
                      <span className="hidden lg:inline">·</span>
                      <span className="hidden lg:inline">{formatFileSize(doc.file_size)}</span>
                      <span className="hidden lg:inline">·</span>
                      <span>{formatDate(doc.created_at)}</span>
                    </div>
                    {doc.ai_summary && (
                      <p className="text-xs text-primary mt-1 truncate">{doc.ai_summary}</p>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleAnalyze(doc.id)}
                    disabled={analyzingId === doc.id}
                    className="p-2 hover:bg-primary/5 rounded-lg text-primary transition-colors active:scale-95 disabled:opacity-50"
                    title="AI分析"
                  >
                    {analyzingId === doc.id ? (
                      <icons.Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <icons.Sparkles className="w-4 h-4" />
                    )}
                  </button>
                  <button className="p-2 hover:bg-primary/5 rounded-lg text-primary transition-colors active:scale-95">
                    <icons.Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleEditClick(doc)}
                    className="hidden lg:block p-2 hover:bg-primary/5 rounded-lg text-primary transition-colors active:scale-95"
                  >
                    <icons.Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="hidden lg:block p-2 hover:bg-destructive/5 rounded-lg text-destructive transition-colors active:scale-95"
                  >
                    <icons.Trash2 className="w-4 h-4" />
                  </button>
                  <button className="lg:hidden p-2 hover:bg-muted rounded-lg text-muted-foreground transition-colors active:scale-95">
                    <icons.MoreVertical className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
