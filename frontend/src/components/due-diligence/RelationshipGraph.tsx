import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { dueDiligenceApi } from '@/lib/api';

interface RelationshipGraphProps {
  companyName?: string;
}

const defaultRelationships = [
  { type: 'shareholder', name: '张某', percent: '45%', relation: '控股股东' },
  { type: 'shareholder', name: '李某', percent: '30%', relation: '股东' },
  { type: 'subsidiary', name: '子公司A', percent: '100%', relation: '全资子公司' },
  { type: 'subsidiary', name: '子公司B', percent: '51%', relation: '控股子公司' },
  { type: 'investment', name: '关联公司', percent: '15%', relation: '投资方' },
];

export function RelationshipGraph({ companyName }: RelationshipGraphProps) {
  const [relationships, setRelationships] = useState(defaultRelationships);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (companyName) {
      setLoading(true);
      dueDiligenceApi.getCompanyGraph(companyName)
        .then(data => {
          // 转换图谱数据为关系列表
          const rels = data.graph.edges.map((edge, i) => {
            const sourceNode = data.graph.nodes.find(n => n.id === edge.source);
            const targetNode = data.graph.nodes.find(n => n.id === edge.target);
            const name = sourceNode?.type === 'target' ? targetNode?.name : sourceNode?.name;
            return {
              type: sourceNode?.type || 'shareholder',
              name: name || `关联方${i+1}`,
              percent: edge.label || '',
              relation: edge.relation,
            };
          });
          if (rels.length > 0) {
            setRelationships(rels);
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [companyName]);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-background rounded-xl border border-border p-6"
    >
      <div className="flex items-center gap-2 mb-6">
        <icons.Network className="w-5 h-5 text-primary" />
        <div>
          <h3 className="font-semibold text-foreground">企业关系图谱</h3>
          <p className="text-sm text-muted-foreground">股权结构与关联企业</p>
        </div>
      </div>

      <div className="relative">
        {/* Center Company */}
        <div className="flex items-center justify-center mb-8">
          <div className="relative">
            <div className="w-32 h-32 bg-primary rounded-2xl flex items-center justify-center shadow-lg">
              <div className="text-center text-white">
                <icons.Building2 className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm font-medium">科技有限公司</p>
              </div>
            </div>
            {/* Pulse effect */}
            <div className="absolute inset-0 bg-primary rounded-2xl animate-ping opacity-20"></div>
          </div>
        </div>

        {/* Relationships */}
        <div className="grid grid-cols-3 gap-4">
          {relationships.map((rel, index) => {
            const typeIconMap = {
              shareholder: icons.User,
              subsidiary: icons.Building2,
              investment: icons.Share2,
            };
            const Icon = typeIconMap[rel.type as keyof typeof typeIconMap] || icons.Share2;
            const colors: Record<string, string> = {
              shareholder: 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
              subsidiary: 'bg-primary/10 text-primary border-primary/20',
              investment: 'bg-primary/10 text-primary border-primary/20',
            };

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                className={`relative p-4 rounded-xl border ${colors[rel.type] || 'bg-muted text-foreground border-border'}`}
              >
                {/* Connection line */}
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 w-0.5 h-8 bg-border"></div>
                
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4" />
                  <span className="font-medium text-sm">{rel.name}</span>
                </div>
                <div className="space-y-1">
                  <p className="text-xs opacity-75">{rel.relation}</p>
                  <p className="text-sm font-bold">{rel.percent}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
