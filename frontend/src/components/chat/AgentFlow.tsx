import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, cardStyle, heading, statusColor, shadow, radius } from '@/lib/design-tokens';

const agents = [
  {
    id: 'search',
    name: 'Search Agent',
    icon: icons.Search,
    status: 'working',
    thought: '正在检索相关判例和法规...',
    color: 'blue',
  },
  {
    id: 'compliance',
    name: 'Compliance Agent',
    icon: icons.Shield,
    status: 'working',
    thought: '对照《民法典》进行合规性审查...',
    color: 'emerald',
  },
  {
    id: 'risk',
    name: 'Risk Agent',
    icon: icons.FileCheck,
    status: 'working',
    thought: '分析潜在法律风险点...',
    color: 'amber',
  },
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    icon: icons.Brain,
    status: 'coordinating',
    thought: '协调各智能体，整合分析结果...',
    color: 'purple',
  },
];

export function AgentFlow() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`bg-background ${radius.dialog} ${shadow.dialog} p-8 max-w-3xl w-full mx-4`}
      >
        <div className="text-center mb-8">
          <h3 className={`${heading.section} mb-2`}>Multi-Agent 协同分析中</h3>
          <p className={heading.muted}>多个智能体正在并行处理您的请求</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {agents.map((agent, index) => {
            const Icon = agent.icon;
            const colorClasses = {
              blue: statusColor.info,
              emerald: statusColor.success,
              amber: statusColor.warning,
              purple: statusColor.info,
            };

            return (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={cardStyle.compact}
              >
                <div className="flex items-start gap-3">
                  <div className={`${iconSize['2xl']} ${radius.button} flex items-center justify-center flex-shrink-0 ${colorClasses[agent.color as keyof typeof colorClasses]}`}>
                    <Icon className={iconSize.md} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className={heading.card}>{agent.name}</h4>
                      <icons.Loader2 className={`${iconSize.xs} animate-spin text-muted-foreground`} />
                    </div>
                    <p className={`${heading.micro} leading-relaxed`}>{agent.thought}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Connection Lines Animation */}
        <div className="mt-6 relative h-2">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: '100%' }}
            transition={{ duration: 2, repeat: Infinity }}
            className="h-full bg-primary rounded-full"
          />
        </div>
      </motion.div>
    </motion.div>
  );
}
