import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import ReactMarkdown from 'react-markdown';
import { documentsApi, Document } from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { VersionHistory } from './VersionHistory';

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
  const [showVersionHistory, setShowVersionHistory] = useState(false);

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

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [slashOpen, setSlashOpen] = useState(false);
  const [slashQuery, setSlashQuery] = useState('');
  const [slashPos, setSlashPos] = useState({ top: 0, left: 0 });
  const [slashIndex, setSlashIndex] = useState(0);

  // Markdown slash command templates
  const MARKDOWN_COMMANDS = [
    { title: '合同标题', icon: '契', desc: '插入合同标题和编号', text: '# 【合同名称】\n\n合同编号：【    】\n\n' },
    { title: '甲乙方信息', icon: '方', desc: '当事方基本信息', text: '**甲方（全称）：** 【    】\n统一社会信用代码/身份证号：【    】\n法定代表人：【    】\n住所/地址：【    】\n联系方式：【    】\n\n**乙方（全称）：** 【    】\n统一社会信用代码/身份证号：【    】\n法定代表人：【    】\n住所/地址：【    】\n联系方式：【    】\n\n' },
    { title: '鉴于条款', icon: '鉴', desc: '鉴于（Whereas）条款', text: '**鉴于：**\n\n1. 甲方【背景说明】；\n2. 乙方【背景说明】；\n3. 双方经友好协商，就【合同目的】事宜达成如下协议：\n\n' },
    { title: '标准条款', icon: '条', desc: '带编号的合同条款', text: '## 第【  】条 【条款名称】\n\n【条款内容】\n\n' },
    { title: '违约责任', icon: '责', desc: '标准违约责任条款', text: '## 违约责任\n\n1. 甲方违约责任：甲方逾期支付款项的，应按逾期金额每日【  ‰】的标准向乙方支付违约金。\n2. 乙方违约责任：【具体违约情形及责任】\n3. 损害赔偿：违约方应赔偿守约方因此遭受的直接经济损失，但赔偿总额不超过本合同总价款的【  】%。\n\n' },
    { title: '争议解决', icon: '诉', desc: '争议解决条款', text: '## 争议解决\n\n1. 本合同的签订、履行、变更、解除和终止等有关的争议，双方应首先通过友好协商解决。\n2. 协商不成的，任何一方均有权向【    】人民法院提起诉讼 / 提交【    】仲裁委员会按其仲裁规则进行仲裁。\n\n' },
    { title: '不可抗力', icon: '力', desc: '不可抗力条款', text: '## 不可抗力\n\n1. 不可抗力是指不能预见、不能避免且不能克服的客观情况，包括但不限于自然灾害、战争、政府行为、法律法规变更等。\n2. 因不可抗力不能履行合同的，根据不可抗力的影响，部分或全部免除责任。\n3. 遭受不可抗力的一方应在不可抗力事件发生后【  】日内书面通知对方，并在【  】日内提供相关证明文件。\n\n' },
    { title: '保密条款', icon: '密', desc: '保密义务条款', text: '## 保密条款\n\n1. 保密信息范围：双方在合同履行过程中知悉的对方商业秘密、技术秘密及其他保密信息。\n2. 保密期限：本条保密义务自本合同签订之日起至合同终止后【  】年止。\n3. 例外情形：（1）公开渠道可获得的信息；（2）已为接收方合法拥有的信息；（3）经披露方书面同意披露的信息；（4）法律法规要求披露的信息。\n\n' },
    { title: '签署区', icon: '署', desc: '签署盖章区域', text: '\n（以下无正文）\n\n**甲方（盖章）：**                    **乙方（盖章）：**\n\n法定代表人/授权代表：              法定代表人/授权代表：\n\n签字：                            签字：\n\n日期：    年    月    日           日期：    年    月    日\n\n' },
    { title: '附件列表', icon: '附', desc: '附件清单', text: '**附件：**\n\n附件一：【    】\n附件二：【    】\n附件三：【    】\n\n' },
    { title: '分隔线', icon: '—', desc: '水平分割线', text: '\n---\n\n' },
    { title: '表格', icon: '田', desc: '3列表格', text: '| 列1 | 列2 | 列3 |\n|------|------|------|\n| 内容 | 内容 | 内容 |\n| 内容 | 内容 | 内容 |\n\n' },
  ];

  const filteredCommands = MARKDOWN_COMMANDS.filter(
    cmd => cmd.title.includes(slashQuery) || cmd.desc.includes(slashQuery)
  );

  const insertText = (before: string, after: string = '') => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selectedText = content.substring(start, end);
      const newText = content.substring(0, start) + before + selectedText + after + content.substring(end);

      setContent(newText);

      setTimeout(() => {
          textarea.focus();
          textarea.setSelectionRange(start + before.length, end + before.length);
      }, 0);
  };

  const insertSlashCommand = useCallback((cmd: typeof MARKDOWN_COMMANDS[0]) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    // Find the "/" position
    const textBefore = content.substring(0, cursorPos);
    const slashIdx = textBefore.lastIndexOf('/');
    if (slashIdx < 0) return;

    const newContent = content.substring(0, slashIdx) + cmd.text + content.substring(cursorPos);
    setContent(newContent);
    setSlashOpen(false);
    setSlashQuery('');

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(slashIdx + cmd.text.length, slashIdx + cmd.text.length);
    }, 0);
  }, [content]);

  // Handle textarea input for slash detection
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setContent(val);

    const pos = e.target.selectionStart;
    const textBefore = val.substring(0, pos);
    const match = textBefore.match(/(?:^|\n)\/([\u4e00-\u9fa5\w]*)$/);

    if (match) {
      setSlashQuery(match[1] || '');
      setSlashIndex(0);
      setSlashOpen(true);

      // Approximate position
      const rect = e.target.getBoundingClientRect();
      const linesBefore = textBefore.split('\n').length;
      setSlashPos({
        top: rect.top + Math.min(linesBefore * 22, rect.height - 40),
        left: rect.left + 40,
      });
    } else {
      setSlashOpen(false);
    }
  };

  // Keyboard nav for slash menu
  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!slashOpen || filteredCommands.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSlashIndex(prev => (prev + 1) % filteredCommands.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSlashIndex(prev => (prev - 1 + filteredCommands.length) % filteredCommands.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      insertSlashCommand(filteredCommands[slashIndex]);
    } else if (e.key === 'Escape') {
      setSlashOpen(false);
    }
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
             {/* 版本历史按钮 */}
             {initialDoc?.id && (
               <button
                 onClick={() => setShowVersionHistory(true)}
                 className="p-2 text-muted-foreground hover:bg-muted hover:text-foreground rounded-lg transition-colors"
                 title="版本历史"
               >
                 <icons.Clock className="w-5 h-5" />
               </button>
             )}
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
               className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 text-sm font-medium disabled:opacity-50 shadow-sm"
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
              className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
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
                <div className="relative flex-1 flex">
                  <textarea
                    ref={textareaRef}
                    value={content}
                    onChange={handleTextareaChange}
                    onKeyDown={handleTextareaKeyDown}
                    placeholder="在此输入文档内容 (支持 Markdown 格式)... 输入 / 可快速插入法律文书模块"
                    className="flex-1 p-8 resize-none focus:outline-none text-foreground leading-relaxed font-mono text-base"
                  />
                  {/* Slash Command Menu */}
                  {slashOpen && filteredCommands.length > 0 && (
                    <div
                      className="fixed z-[100] bg-popover border border-border rounded-lg shadow-xl overflow-hidden max-h-[280px] overflow-y-auto min-w-[260px] animate-in fade-in slide-in-from-top-1 duration-150"
                      style={{ top: slashPos.top, left: slashPos.left }}
                    >
                      <div className="px-3 py-1 border-b border-border bg-muted/50">
                        <span className="text-[10px] text-muted-foreground">方向键选择 · Enter 确认 · Esc 取消</span>
                      </div>
                      {filteredCommands.map((cmd, i) => (
                        <button
                          key={cmd.title}
                          onClick={() => insertSlashCommand(cmd)}
                          className={cn(
                            'w-full flex items-center gap-3 px-3 py-2 text-left transition-colors',
                            i === slashIndex ? 'bg-primary/10 text-primary' : 'hover:bg-accent text-foreground'
                          )}
                        >
                          <span className="w-7 h-7 rounded-md bg-muted flex items-center justify-center text-xs font-bold shrink-0 border border-border/50">
                            {cmd.icon}
                          </span>
                          <div className="min-w-0">
                            <div className="text-sm font-medium truncate">{cmd.title}</div>
                            <div className="text-[11px] text-muted-foreground truncate">{cmd.desc}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
            )}
        </div>

        <div className="px-6 py-2 border-t border-border bg-muted text-xs text-muted-foreground flex justify-between">
            <span>支持 Markdown 格式 · 输入 / 插入法律文书模块</span>
            <span>{content.replace(/\s/g, '').length} 字 · {content.length} 字符</span>
        </div>
      </motion.div>

      {/* 版本历史面板 */}
      {showVersionHistory && initialDoc?.id && (
        <VersionHistory
          documentId={initialDoc.id}
          onClose={() => setShowVersionHistory(false)}
          onRestore={() => {
            setShowVersionHistory(false);
            // 重新加载文档内容
            if (initialDoc.id) {
              documentsApi.get(initialDoc.id).then((doc) => {
                setContent(doc.extracted_text || '');
                setTags(doc.tags || []);
              });
            }
          }}
        />
      )}
    </motion.div>
  );
}
