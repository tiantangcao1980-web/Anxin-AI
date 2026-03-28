import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { contractsApi, documentsApi } from '@/lib/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

interface Template {
  id: string;
  name: string;
  category: string;
  description: string;
  downloads: number;
  rating: number;
  tags: string[];
}

const categories = ['all', '合同协议', '催告函件', '诉讼文书', '法律意见书', '调研报告', '其他'];

export function TemplateGallery() {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  // Mock template content since the API only returns metadata
  const getTemplateContent = (type: string, name: string) => {
    return `# ${name}\n\n## 1. 双方信息\n\n甲方：[请输入]\n乙方：[请输入]\n\n## 2. 协议内容\n\n鉴于...\n\n第一条 [条款名称]\n...\n\n## 3. 签署\n\n甲方（盖章）：________\n日期：________`;
  };

  const handleUseTemplate = async (template: Template) => {
    setProcessingId(template.id);
    try {
        // Create a new document from template
        const content = getTemplateContent(template.category, template.name);
        await documentsApi.createText({
            name: `${template.name}_${new Date().toISOString().split('T')[0]}`,
            content: content,
            doc_type: 'contract', // Simplified
            description: `基于模板 "${template.name}" 创建`,
            tags: ['模板', ...template.tags]
        });
        toast.success('已使用模板创建文档');
        navigate('/documents');
    } catch (error) {
        console.error('Failed to use template:', error);
        toast.error('创建失败');
    } finally {
        setProcessingId(null);
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await contractsApi.getTemplates();
      // 适配后端数据，如果后端返回格式不同，这里需要映射
      const mappedTemplates = response.templates.map((t: any) => ({
        id: t.id,
        name: t.name,
        category: t.category || '其他',
        description: t.description || '暂无描述',
        downloads: t.downloads || 0,
        rating: t.rating || 5.0,
        tags: t.tags || [],
      }));
      setTemplates(mappedTemplates);
    } catch (error) {
      console.error('Failed to load templates:', error);
      // Fallback to mock data if API fails (for demo purposes)
      setTemplates([
        {
          id: '1',
          name: '律师函模板',
          category: '催告函件',
          description: '用于债务催收、合同履行催告等场景',
          downloads: 1245,
          rating: 4.8,
          tags: ['合同', '催告'],
        },
        {
          id: '2',
          name: '技术服务合同',
          category: '合同协议',
          description: '软件开发、技术咨询等服务合同模板',
          downloads: 892,
          rating: 4.9,
          tags: ['合同', '技术'],
        },
        {
          id: '3',
          name: '民事起诉状',
          category: '诉讼文书',
          description: '民事诉讼起诉状标准模板',
          downloads: 2103,
          rating: 4.7,
          tags: ['诉讼', '民事'],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const filteredTemplates = templates.filter(
    (t) => selectedCategory === 'all' || t.category === selectedCategory
  );

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-muted">
        <icons.Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6 bg-muted">
      {/* Filters */}
      <div className="flex gap-2 mb-4 lg:mb-6 overflow-x-auto pb-2">
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
              selectedCategory === category
                ? 'bg-primary text-white shadow-sm'
                : 'bg-background text-foreground/80 hover:bg-muted border border-border'
            }`}
          >
            {category === 'all' ? '全部模板' : category}
          </button>
        ))}
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 lg:gap-4">
        {filteredTemplates.map((template, index) => (
          <motion.div
            key={template.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => handleUseTemplate(template)}
            className="bg-background border border-border rounded-2xl p-4 lg:p-5 hover:border-primary hover:shadow-lg transition-all cursor-pointer group active:scale-98"
          >
            {/* Icon */}
            <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-sm">
              <icons.FileText className="w-6 h-6 text-white" />
            </div>

            {/* Content */}
            <h3 className="font-semibold text-foreground mb-1">{template.name}</h3>
            <p className="text-xs text-muted-foreground mb-3">{template.category}</p>
            <p className="text-sm text-foreground/80 leading-relaxed mb-4 line-clamp-2">
              {template.description}
            </p>

            {/* Tags */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              {template.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 bg-muted text-muted-foreground rounded-full text-xs"
                >
                  {tag}
                </span>
              ))}
            </div>

            {/* Stats & Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-border">
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <icons.Download className="w-3 h-3" />
                  <span>{template.downloads}</span>
                </div>
                <div className="flex items-center gap-1">
                  <icons.Star className="w-3 h-3 fill-amber-500 text-amber-500" />
                  <span>{template.rating}</span>
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => handleUseTemplate(template)}
                  disabled={!!processingId}
                  className="p-1.5 hover:bg-primary/5 rounded-lg text-primary active:scale-95 transition-all flex items-center gap-1 px-2"
                >
                  {processingId === template.id ? (
                    <icons.Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <icons.Edit className="w-4 h-4" />
                      <span className="text-xs font-medium">使用</span>
                    </>
                  )}
                </button>
                <button className="p-1.5 hover:bg-primary/5 rounded-lg text-primary active:scale-95 transition-all">
                  <icons.Eye className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
