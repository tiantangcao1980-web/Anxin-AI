import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import ReactMarkdown from 'react-markdown';
import { documentsApi, Document } from '@/lib/api';
import { toast } from 'sonner';

interface DocumentEditorProps {
  initialDoc?: Document | null; // Null means creating new
  onClose: () => void;
  onSave: (doc: Document) => void;
}

export function DocumentEditor({ initialDoc, onClose, onSave }: DocumentEditorProps) {
  const [title, setTitle] = useState(initialDoc?.name || '');
  const [content, setContent] = useState(initialDoc?.extracted_text || '');
  const [docType, setDocType] = useState(initialDoc?.doc_type || 'other');
  const [tags, setTags] = useState<string[]>(initialDoc?.tags || []);
  const [tagInput, setTagInput] = useState('');
  const [isPreview, setIsPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);

  // 如果是编辑模式，且 initialDoc 没有 content (列表接口可能不返回)，则获取详情
  useEffect(() => {
    if (initialDoc?.id && !initialDoc.extracted_text) {
        setLoadingContent(true);
        documentsApi.get(initialDoc.id)
            .then(doc => {
                setContent(doc.extracted_text || '');
                // 也可以同步更新 tags 等其他可能不完整的字段
                setTags(doc.tags || []);
            })
            .catch(err => {
                console.error('获取文档详情失败', err);
                toast.error('无法加载文档内容');
            })
            .finally(() => setLoadingContent(false));
    }
  }, [initialDoc]);

  const handleSave = async () => {
    if (!title.trim()) {
      toast.error('请输入文档标题');
      return;
    }
    if (!content.trim()) {
      toast.error('文档内容不能为空');
      return;
    }

    setSaving(true);
    try {
      let savedDoc: Document;
      if (initialDoc) {
        // 更新
        // 1. 更新元数据
        if (title !== initialDoc.name || JSON.stringify(tags) !== JSON.stringify(initialDoc.tags)) {
            await documentsApi.update(initialDoc.id, { name: title, tags });
        }
        // 2. 更新内容
        if (content !== initialDoc.extracted_text) {
            savedDoc = await documentsApi.updateContent(initialDoc.id, { content });
        } else {
            savedDoc = initialDoc; // 内容未变
        }
        toast.success('文档已更新');
      } else {
        // 新建
        savedDoc = await documentsApi.createText({
          name: title,
          content: content,
          doc_type: docType,
          tags: tags
        });
        toast.success('文档已创建');
      }
      onSave(savedDoc);
      onClose();
    } catch (error: any) {
      console.error('保存失败', error);
      toast.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const addTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const insertText = (before: string, after: string = '') => {
      const textarea = document.querySelector('textarea');
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selectedText = content.substring(start, end);
      const newText = content.substring(0, start) + before + selectedText + after + content.substring(end);

      setContent(newText);

      // Restore selection/cursor
      setTimeout(() => {
          textarea.focus();
          textarea.setSelectionRange(start + before.length, end + before.length);
      }, 0);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 lg:p-8"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-background rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/50">
          <div className="flex items-center gap-4 flex-1">
            <div className="p-2 bg-primary/10 text-primary rounded-lg">
              <icons.FileText className="w-5 h-5" />
            </div>
            <div className="flex-1 max-w-lg">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="输入文档标题..."
                className="w-full bg-transparent text-lg font-semibold text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
             <button
               onClick={() => setIsPreview(!isPreview)}
               className="p-2 text-muted-foreground hover:bg-muted rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
             >
               {isPreview ? <icons.Edit3 className="w-4 h-4" /> : <icons.Eye className="w-4 h-4" />}
               {isPreview ? '编辑' : '预览'}
             </button>
             <div className="h-6 w-px bg-border" />
             <button
               onClick={onClose}
               className="p-2 text-muted-foreground hover:bg-muted rounded-lg transition-colors"
             >
               <icons.X className="w-5 h-5" />
             </button>
             <button
               onClick={handleSave}
               disabled={saving || loadingContent}
               className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 text-sm font-medium disabled:opacity-50 shadow-sm"
             >
               {saving ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.Save className="w-4 h-4" />}
               保存
             </button>
          </div>
        </div>

        {/* Toolbar & Metadata */}
        <div className="px-6 py-3 border-b border-border flex items-center gap-4 bg-background flex-wrap">
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            >
                <option value="other">其他文档</option>
                <option value="contract">合同协议</option>
                <option value="letter">律师函件</option>
                <option value="litigation">诉讼文书</option>
                <option value="memo">备忘录</option>
            </select>

            <div className="h-6 w-px bg-border hidden lg:block" />

            {/* Markdown Toolbar */}
            {!isPreview && (
                <div className="flex items-center gap-1">
                    <button onClick={() => insertText('**', '**')} className="p-1.5 text-muted-foreground hover:bg-muted rounded hover:text-primary" title="加粗">
                        <icons.Bold className="w-4 h-4" />
                    </button>
                    <button onClick={() => insertText('*', '*')} className="p-1.5 text-muted-foreground hover:bg-muted rounded hover:text-primary" title="斜体">
                        <icons.Italic className="w-4 h-4" />
                    </button>
                    <div className="h-4 w-px bg-border mx-1" />
                    <button onClick={() => insertText('# ')} className="p-1.5 text-muted-foreground hover:bg-muted rounded hover:text-primary" title="一级标题">
                        <icons.Heading1 className="w-4 h-4" />
                    </button>
                    <button onClick={() => insertText('## ')} className="p-1.5 text-muted-foreground hover:bg-muted rounded hover:text-primary" title="二级标题">
                        <icons.Heading2 className="w-4 h-4" />
                    </button>
                    <div className="h-4 w-px bg-border mx-1" />
                    <button onClick={() => insertText('- ')} className="p-1.5 text-muted-foreground hover:bg-muted rounded hover:text-primary" title="列表">
                        <icons.List className="w-4 h-4" />
                    </button>
                </div>
            )}

            <div className="flex items-center gap-2 flex-1 justify-end">
                <icons.Tag className="w-4 h-4 text-muted-foreground" />
                <div className="flex items-center gap-2 flex-wrap justify-end">
                    {tags.map(tag => (
                        <span key={tag} className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs font-medium flex items-center gap-1 border border-primary/20">
                            {tag}
                            <button onClick={() => removeTag(tag)} className="hover:text-primary/80">
                                <icons.X className="w-3 h-3" />
                            </button>
                        </span>
                    ))}
                    <input
                        type="text"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addTag()}
                        placeholder="添加标签..."
                        className="text-sm bg-transparent border-none focus:ring-0 placeholder:text-muted-foreground min-w-[80px] text-right"
                    />
                </div>
            </div>
        </div>

        {/* Editor Area */}
        <div className="flex-1 flex overflow-hidden relative">
            {loadingContent && (
                <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center">
                    <icons.Loader2 className="w-8 h-8 text-primary animate-spin" />
                    <span className="ml-2 text-muted-foreground">加载文档内容...</span>
                </div>
            )}

            {isPreview ? (
                <div className="flex-1 p-8 overflow-y-auto prose prose-blue max-w-none bg-muted">
                    <ReactMarkdown>{content}</ReactMarkdown>
                </div>
            ) : (
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="在此输入文档内容 (支持 Markdown 格式)..."
                    className="flex-1 p-8 resize-none focus:outline-none text-foreground leading-relaxed font-mono text-base"
                />
            )}
        </div>

        <div className="px-6 py-2 border-t border-border bg-muted text-xs text-muted-foreground flex justify-between">
            <span>支持 Markdown 格式</span>
            <span>{content.length} 字符</span>
        </div>
      </motion.div>
    </motion.div>
  );
}
