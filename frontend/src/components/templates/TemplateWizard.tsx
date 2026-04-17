/**
 * 智能合同模板向导
 *
 * 分步填写表单，根据合同类型动态生成条款，实时预览合同内容。
 * 支持条件分支（如付款方式切换、争议解决方式选择）。
 */

import { useState, useEffect, useMemo } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { cn } from'@/lib/utils';
import { toast } from'sonner';
import ReactMarkdown from'react-markdown';

// ==================== Types ====================

interface TemplateField {
 key: string;
 label: string;
 field_type: string;
 required: boolean;
 default: any;
 placeholder: string;
 options: { value: string; label: string }[];
 group: string;
 help_text: string;
 condition: string | null;
}

interface TemplateInfo {
 id: string;
 name: string;
 category: string;
 description: string;
 version: string;
 fields: TemplateField[];
 clauses: { id: string; title: string; required: boolean; condition: string | null }[];
}

interface TemplateWizardProps {
 templateId: string;
 onGenerate: (text: string) => void;
 onClose: () => void;
 apiBaseUrl?: string;
}

// ==================== Field Components ====================

function FormField({
 field,
 value,
 onChange,
}: {
 field: TemplateField;
 value: any;
 onChange: (val: any) => void;
}) {
 const baseInputClass = cn(
'w-full px-3 py-2 bg-background border border-border rounded-lg',
'text-sm text-foreground placeholder:text-muted-foreground',
'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
'transition-colors'
 );

 switch (field.field_type) {
 case'select':
 return (
 <select
 value={value || field.default ||''}
 onChange={(e) => onChange(e.target.value)}
 className={baseInputClass}
 >
 <option value="">请选择...</option>
 {field.options.map((opt) => (
 <option key={opt.value} value={opt.value}>{opt.label}</option>
 ))}
 </select>
 );

 case'boolean':
 return (
 <div className="flex items-center gap-3">
 <button
 onClick={() => onChange(true)}
 className={cn(
'px-4 py-2 rounded-lg text-sm border transition-colors',
 value === true
 ?'bg-primary text-primary-foreground border-primary'
 :'bg-background border-border text-muted-foreground hover:border-primary/50'
 )}
 >
 是
 </button>
 <button
 onClick={() => onChange(false)}
 className={cn(
'px-4 py-2 rounded-lg text-sm border transition-colors',
 value === false
 ?'bg-primary text-primary-foreground border-primary'
 :'bg-background border-border text-muted-foreground hover:border-primary/50'
 )}
 >
 否
 </button>
 </div>
 );

 case'textarea':
 return (
 <textarea
 value={value ||''}
 onChange={(e) => onChange(e.target.value)}
 placeholder={field.placeholder || `请输入${field.label}`}
 rows={3}
 className={cn(baseInputClass,'resize-none')}
 />
 );

 case'number':
 case'money':
 case'percentage':
 return (
 <div className="relative">
 <input
 type="number"
 value={value ?? field.default ??''}
 onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
 placeholder={field.placeholder || `请输入${field.label}`}
 className={baseInputClass}
 />
 {field.field_type ==='money' && (
 <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">元</span>
 )}
 {field.field_type ==='percentage' && (
 <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">%</span>
 )}
 </div>
 );

 case'date':
 return (
 <input
 type="date"
 value={value ||''}
 onChange={(e) => onChange(e.target.value)}
 className={baseInputClass}
 />
 );

 default:
 return (
 <input
 type="text"
 value={value ||''}
 onChange={(e) => onChange(e.target.value)}
 placeholder={field.placeholder || `请输入${field.label}`}
 className={baseInputClass}
 />
 );
 }
}

// ==================== Main Component ====================

export function TemplateWizard({ templateId, onGenerate, onClose, apiBaseUrl ='' }: TemplateWizardProps) {
 const [template, setTemplate] = useState<TemplateInfo | null>(null);
 const [loading, setLoading] = useState(true);
 const [rendering, setRendering] = useState(false);
 const [variables, setVariables] = useState<Record<string, any>>({});
 const [previewText, setPreviewText] = useState('');
 const [showPreview, setShowPreview] = useState(false);
 const [currentGroup, setCurrentGroup] = useState('');

 // Load template detail
 useEffect(() => {
 const fetchTemplate = async () => {
 try {
 const token = localStorage.getItem('auth_token');
 const res = await fetch(`${apiBaseUrl}/api/v1/contracts/templates/${templateId}`, {
 headers: {'Authorization': `Bearer ${token}` },
 });
 const data = await res.json();
 if (data.success) {
 setTemplate(data.data);
 // Set defaults
 const defaults: Record<string, any> = {};
 data.data.fields.forEach((f: TemplateField) => {
 if (f.default !== null && f.default !== undefined) {
 defaults[f.key] = f.default;
 }
 });
 setVariables(defaults);
 // Set first group
 if (data.data.fields.length > 0) {
 setCurrentGroup(data.data.fields[0].group);
 }
 }
 } catch (err) {
 toast.error('模板加载失败');
 } finally {
 setLoading(false);
 }
 };
 fetchTemplate();
 }, [templateId]);

 // Evaluate condition (simple client-side)
 const evalCondition = (condition: string | null): boolean => {
 if (!condition) return true;
 try {
 const boolMatch = condition.match(/^(\w+)\s*==\s*(true|false)$/i);
 if (boolMatch) {
 return Boolean(variables[boolMatch[1]]) === (boolMatch[2].toLowerCase() ==='true');
 }
 const strMatch = condition.match(/^(\w+)\s*==\s*'([^']*)'$/);
 if (strMatch) {
 return String(variables[strMatch[1]] ||'') === strMatch[2];
 }
 return true;
 } catch { return true; }
 };

 // Visible fields (filtered by condition)
 const visibleFields = useMemo(() => {
 if (!template) return [];
 return template.fields.filter(f => evalCondition(f.condition));
 }, [template, variables]);

 // Groups
 const groups = useMemo(() => {
 const seen = new Set<string>();
 return visibleFields.filter(f => {
 if (seen.has(f.group)) return false;
 seen.add(f.group);
 return true;
 }).map(f => f.group);
 }, [visibleFields]);

 // Render template
 const handleRender = async () => {
 setRendering(true);
 try {
 const token = localStorage.getItem('auth_token');
 const res = await fetch(`${apiBaseUrl}/api/v1/contracts/templates/${templateId}/render`, {
 method:'POST',
 headers: {
'Authorization': `Bearer ${token}`,
'Content-Type':'application/json',
 },
 body: JSON.stringify({ variables }),
 });
 const data = await res.json();
 if (data.success) {
 setPreviewText(data.data.rendered_text);
 setShowPreview(true);
 toast.success(`合同已生成（${data.data.word_count}字）`);
 } else {
 toast.error(data.message ||'生成失败');
 }
 } catch (err) {
 toast.error('模板渲染失败');
 } finally {
 setRendering(false);
 }
 };

 // Completion percentage
 const completionPct = useMemo(() => {
 const required = visibleFields.filter(f => f.required);
 if (required.length === 0) return 100;
 const filled = required.filter(f => {
 const v = variables[f.key];
 return v !== null && v !== undefined && v !=='';
 });
 return Math.round((filled.length / required.length) * 100);
 }, [visibleFields, variables]);

 if (loading) {
 return (
 <div className="flex items-center justify-center h-64">
 <icons.Loader2 className="w-6 h-6 animate-spin text-primary" />
 <span className="ml-2 text-muted-foreground">加载模板...</span>
 </div>
 );
 }

 if (!template) {
 return (
 <div className="text-center py-12 text-muted-foreground">
 <icons.AlertCircle className="w-8 h-8 mx-auto mb-2" />
 <p>模板不存在</p>
 </div>
 );
 }

 return (
 <div className="flex flex-col h-full bg-background">
 {/* Header */}
 <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/30">
 <div>
 <h2 className="text-lg font-medium text-foreground">{template.name.replace(/\{\{.*?\}\}/g,'')}</h2>
 <p className="text-sm text-muted-foreground mt-0.5">{template.description}</p>
 </div>
 <div className="flex items-center gap-3">
 {/* Completion indicator */}
 <div className="flex items-center gap-2">
 <div className="w-24 h-1.5 bg-muted rounded-full overflow-hidden">
 <div
 className="h-full bg-primary rounded-full transition-[width] duration-300"
 style={{ width: `${completionPct}%` }}
 />
 </div>
 <span className="text-xs text-muted-foreground">{completionPct}%</span>
 </div>
 <button onClick={onClose} className="p-2 text-muted-foreground hover:bg-muted rounded-lg">
 <icons.X className="w-5 h-5" />
 </button>
 </div>
 </div>

 <div className="flex-1 flex overflow-hidden">
 {/* Left: Form */}
 <div className={cn('flex-1 overflow-y-auto p-6', showPreview &&'w-1/2')}>
 {/* Group tabs */}
 <div className="flex flex-wrap gap-2 mb-6">
 {groups.map(group => (
 <button
 key={group}
 onClick={() => setCurrentGroup(group)}
 className={cn(
'px-3 py-1.5 rounded-lg text-sm transition-colors',
 currentGroup === group
 ?'bg-primary text-primary-foreground'
 :'bg-muted text-muted-foreground hover:bg-muted/80'
 )}
 >
 {group}
 </button>
 ))}
 </div>

 {/* Fields */}
 <div className="space-y-4">
 {visibleFields
 .filter(f => f.group === currentGroup)
 .map(field => (
 <div key={field.key}>
 <label className="block text-sm font-medium text-foreground mb-1.5">
 {field.label}
 {field.required && <span className="text-destructive ml-0.5">*</span>}
 </label>
 <FormField
 field={field}
 value={variables[field.key]}
 onChange={(val) => setVariables(prev => ({ ...prev, [field.key]: val }))}
 />
 {field.help_text && (
 <p className="text-[11px] text-muted-foreground mt-1">{field.help_text}</p>
 )}
 </div>
 ))}
 </div>

 {/* Generate button */}
 <div className="mt-8 flex gap-3">
 <button
 onClick={handleRender}
 disabled={rendering || completionPct < 30}
 className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors text-sm font-medium"
 >
 {rendering ? (
 <icons.Loader2 className="w-4 h-4 animate-spin" />
 ) : (
 <icons.Sparkles className="w-4 h-4" />
 )}
 {showPreview ?'重新生成' :'生成合同'}
 </button>
 {showPreview && (
 <button
 onClick={() => onGenerate(previewText)}
 className="flex items-center gap-2 px-4 py-3 bg-success text-success-foreground rounded-lg hover:bg-success/20 transition-colors text-sm font-medium"
 >
 <icons.Check className="w-4 h-4" />
 使用此合同
 </button>
 )}
 </div>
 </div>

 {/* Right: Preview */}
 <AnimatePresence>
 {showPreview && (
 <motion.div
 initial={{ width: 0, opacity: 0 }}
 animate={{ width:'50%', opacity: 1 }}
 exit={{ width: 0, opacity: 0 }}
 className="border-l border-border overflow-hidden"
 >
 <div className="h-full overflow-y-auto p-6 bg-muted/20">
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-sm font-medium text-foreground">合同预览</h3>
 <button
 onClick={() => {
 navigator.clipboard.writeText(previewText);
 toast.success('已复制到剪贴板');
 }}
 className="text-xs text-primary hover:text-primary/80 flex items-center gap-1"
 >
 <icons.Copy className="w-3 h-3" />
 复制全文
 </button>
 </div>
 <div className="bg-background rounded-lg border border-border p-6 prose prose-sm max-w-none">
 <ReactMarkdown>{previewText}</ReactMarkdown>
 </div>
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 </div>
 );
}
