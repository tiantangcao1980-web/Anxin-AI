/**
 * 官网 · 博客
 *
 * 占位骨架：静态文章数组 + 列表卡。
 * 真实内容化时建议接 MDX / CMS；当前只暴露列表，详情走外链或后续补充。
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { useDocumentMeta } from '@/components/marketing/useDocumentMeta'

interface Post {
  slug: string
  title: string
  excerpt: string
  date: string
  category: 'product' | 'engineering' | 'industry' | 'compliance'
  read_min: number
  href?: string  // 外链；为空时显示"准备中"
}

const POSTS: Post[] = [
  {
    slug: 'skills-sandbox-design',
    title: '把 Skill 沙箱做成"按需信任"的五分层模型',
    excerpt: '从 prompt-only 到容器再到远程 microVM —— 我们如何让每个 Skill 在对应的隔离层运行，而不是全员 Docker。',
    date: '2026-05-14',
    category: 'engineering',
    read_min: 12,
  },
  {
    slug: 'enterprise-cluster',
    title: '飞书式组织目录 + 部门继承 = 企业级权限的可读模型',
    excerpt: '六层权限闸门 / 部门树 / 角色绑定 / LDAP 双向同步 —— 让人事变更自动反映到能力授权。',
    date: '2026-05-14',
    category: 'engineering',
    read_min: 10,
  },
  {
    slug: 'multi-persona-rationale',
    title: '为什么我们不做"通用 AI 助手"',
    excerpt: '一个通才 Agent 跑所有任务听起来很美，落到企业里就是没人懂 —— 我们选 10 个专家而非 1 个全能选手的理由。',
    date: '2026-04-30',
    category: 'product',
    read_min: 6,
  },
  {
    slug: 'gbt35273-mapping',
    title: 'GB/T 35273-2020 落到代码：五级数据分类怎么写在 ORM 里',
    excerpt: '数据分级不是 PPT 上的标签 —— 我们用 column-level annotation + ORM hook 在 read/write 路径上强制执行。',
    date: '2026-04-10',
    category: 'compliance',
    read_min: 14,
  },
  {
    slug: 'on-prem-airgap',
    title: 'AirGap 部署清单 —— 怎样让 AI 助手在断网政企里也能跑',
    excerpt: '镜像离线打包、模型本地推理、Skill 包签名分发、时钟同步、备份恢复演练。',
    date: '2026-03-25',
    category: 'engineering',
    read_min: 8,
  },
]

const CATEGORY_LABEL: Record<Post['category'], string> = {
  product: '产品',
  engineering: '工程',
  industry: '行业',
  compliance: '合规',
}

export default function Blog() {
  useDocumentMeta({
    title: '博客 · 安心智能助手',
    description: '产品 / 工程 / 行业 / 合规 —— 我们怎么把 AI 装进真实业务。',
    ogUrl: 'https://anxin.ai/site/blog',
  })

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-16 space-y-10">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          博客
        </h1>
        <p className="mt-3 max-w-2xl mx-auto text-muted-foreground">
          产品 / 工程 / 行业 / 合规 —— 我们怎么把 AI 装进真实业务。
        </p>
      </header>

      <div className="space-y-3">
        {POSTS.map((p) => (
          <article
            key={p.slug}
            className="rounded-2xl border border-border bg-card p-5 hover:shadow-card transition-shadow"
          >
            <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
              <span className="px-2 py-0.5 rounded bg-muted">
                {CATEGORY_LABEL[p.category]}
              </span>
              <span>{p.date}</span>
              <span>·</span>
              <span>{p.read_min} 分钟阅读</span>
            </div>
            <h2 className="text-lg font-medium">
              {p.href ? (
                <a
                  href={p.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-primary"
                >
                  {p.title}
                </a>
              ) : (
                <span>{p.title}</span>
              )}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              {p.excerpt}
            </p>
            <div className="mt-3 text-xs">
              {p.href ? (
                <a
                  href={p.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary inline-flex items-center gap-1 hover:underline"
                >
                  阅读全文
                  <icons.ExternalLink className={iconSize.xs} />
                </a>
              ) : (
                <span className="text-muted-foreground">详细稿件准备中…</span>
              )}
            </div>
          </article>
        ))}
      </div>

      <section className="text-center text-sm text-muted-foreground">
        想第一时间看到新文章？欢迎{' '}
        <Link to="/site/contact" className="text-primary hover:underline">
          订阅更新
        </Link>
        。
      </section>
    </div>
  )
}
