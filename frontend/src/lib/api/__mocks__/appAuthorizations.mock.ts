/**
 * App Authorizations Mock 适配层
 *
 * 在 VITE_APP_AUTH_MOCK=true 时启用，供 P4-F 阶段在后端 P4-A/B/C/D/E 就绪前完成前端联调。
 *
 * 默认提供：
 *   - 32 个 provider，覆盖 8 个 category（office / office_storage / crm / ecommerce
 *     / info_source / design / compliance / finance）
 *   - 5 条已连接授权（飞书 / 钉钉 / Notion / Shopify / 法大大）
 *
 * Icon URL 策略：
 *   1) 优先使用 Wikimedia Commons 上的官方品牌 SVG（公开可用、CDN 稳定）
 *   2) 找不到稳定来源时使用内联 emoji-style data:image/svg+xml，避免 404
 */

import type {
  AppAuthorization,
  AppProvider,
} from '../appAuthorizations'

const now = () => new Date().toISOString()
const minutesAgo = (n: number) => new Date(Date.now() - n * 60_000).toISOString()
const daysAgo = (n: number) => new Date(Date.now() - n * 86_400_000).toISOString()

/** 生成一个圆角彩色 emoji-style fallback icon（base64 SVG） */
function emojiIcon(emoji: string, bg: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="${bg}"/><text x="50%" y="56%" text-anchor="middle" dominant-baseline="middle" font-size="34" font-family="Apple Color Emoji,Segoe UI Emoji,Noto Color Emoji,sans-serif">${emoji}</text></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

// ===== Provider 种子（32 个，覆盖 8 大分类） =====

const seedProviders: AppProvider[] = [
  // ----- 办公协作 office (5) -----
  {
    provider_id: 'feishu',
    display_name: '飞书',
    description: '字节跳动出品的企业协作平台 — 即时通讯、文档、日历、视频会议',
    category: 'office',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Lark_logo.svg/120px-Lark_logo.svg.png',
    default_scopes: ['contact:read', 'im:message:send_as_bot', 'docs:read'],
    documentation_url: 'https://open.feishu.cn/document',
  },
  {
    provider_id: 'dingtalk',
    display_name: '钉钉',
    description: '阿里巴巴企业级智能协同办公平台',
    category: 'office',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Dingtalk_logo.svg/120px-Dingtalk_logo.svg.png',
    default_scopes: ['contact.user.read', 'message.send'],
    documentation_url: 'https://open.dingtalk.com/document',
  },
  {
    provider_id: 'wecom',
    display_name: '企业微信',
    description: '腾讯企业微信 — 企业内部沟通、客户联系、办公自动化',
    category: 'office',
    icon_url: emojiIcon('💚', '#07C160'),
    default_scopes: ['user.read', 'message.send', 'contact.read'],
    documentation_url: 'https://developer.work.weixin.qq.com/',
  },
  {
    provider_id: 'slack',
    display_name: 'Slack',
    description: '全球流行的团队协作通讯平台',
    category: 'office',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Slack_icon_2019.svg/120px-Slack_icon_2019.svg.png',
    default_scopes: ['channels:read', 'chat:write', 'users:read'],
    documentation_url: 'https://api.slack.com/',
  },
  {
    provider_id: 'outlook',
    display_name: 'Outlook',
    description: '微软邮箱 — 收发邮件、日历事件、联系人',
    category: 'office',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Microsoft_Office_Outlook_%282018%E2%80%93present%29.svg/120px-Microsoft_Office_Outlook_%282018%E2%80%93present%29.svg.png',
    default_scopes: ['Mail.Read', 'Mail.Send', 'Calendars.ReadWrite'],
    documentation_url: 'https://learn.microsoft.com/graph/outlook',
  },

  // ----- 文档存储 office_storage (5) -----
  {
    provider_id: 'notion',
    display_name: 'Notion',
    description: '一体化笔记、知识库、项目管理工作空间',
    category: 'office_storage',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Notion_app_logo.png/120px-Notion_app_logo.png',
    default_scopes: ['read_content', 'update_content'],
    documentation_url: 'https://developers.notion.com/',
  },
  {
    provider_id: 'baidu_netdisk',
    display_name: '百度网盘',
    description: '中国主流个人云存储 — 文件读写、分享',
    category: 'office_storage',
    icon_url: emojiIcon('🐻', '#2A6BD9'),
    default_scopes: ['basic', 'netdisk'],
    documentation_url: 'https://pan.baidu.com/union/document/basic',
  },
  {
    provider_id: 'google_drive',
    display_name: 'Google Drive',
    description: 'Google 云端硬盘 — 文档、表格、幻灯片、文件存储',
    category: 'office_storage',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Google_Drive_icon_%282020%29.svg/120px-Google_Drive_icon_%282020%29.svg.png',
    default_scopes: ['drive.file', 'drive.readonly'],
    documentation_url: 'https://developers.google.com/drive',
  },
  {
    provider_id: 'dropbox',
    display_name: 'Dropbox',
    description: '老牌跨平台云文件同步 — 文件、共享链接、协作',
    category: 'office_storage',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Dropbox_Icon.svg/120px-Dropbox_Icon.svg.png',
    default_scopes: ['files.content.read', 'files.content.write'],
    documentation_url: 'https://www.dropbox.com/developers',
  },
  {
    provider_id: 'office365',
    display_name: 'Office 365',
    description: '微软 365 — Word/Excel/PowerPoint/OneDrive 文档生态',
    category: 'office_storage',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Microsoft_Office_logo_%282019%E2%80%93present%29.svg/120px-Microsoft_Office_logo_%282019%E2%80%93present%29.svg.png',
    default_scopes: ['Files.ReadWrite', 'Sites.Read.All'],
    documentation_url: 'https://learn.microsoft.com/graph/overview',
  },

  // ----- CRM 销售 crm (4) -----
  {
    provider_id: 'salesforce',
    display_name: 'Salesforce',
    description: '全球领先的 SaaS CRM — 客户、商机、订单、报表',
    category: 'crm',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Salesforce.com_logo.svg/120px-Salesforce.com_logo.svg.png',
    default_scopes: ['api', 'refresh_token'],
    documentation_url: 'https://developer.salesforce.com/',
  },
  {
    provider_id: 'hubspot',
    display_name: 'HubSpot',
    description: '免费起步的 CRM 与营销自动化平台',
    category: 'crm',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/HubSpot_Logo.svg/120px-HubSpot_Logo.svg.png',
    default_scopes: ['crm.objects.contacts.read', 'crm.objects.deals.read'],
    documentation_url: 'https://developers.hubspot.com/',
  },
  {
    provider_id: 'zoho',
    display_name: 'Zoho CRM',
    description: 'Zoho 出品的 CRM 系统 — 客户/销售管线/工单',
    category: 'crm',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Zoho_logo.svg/120px-Zoho_logo.svg.png',
    default_scopes: ['ZohoCRM.modules.ALL', 'ZohoCRM.users.READ'],
    documentation_url: 'https://www.zoho.com/crm/developer/docs/',
  },
  {
    provider_id: 'pipedrive',
    display_name: 'Pipedrive',
    description: '可视化销售管线 CRM — 适合中小销售团队',
    category: 'crm',
    icon_url: emojiIcon('🟩', '#1A1A1A'),
    default_scopes: ['deals:read', 'deals:write', 'persons:read'],
    documentation_url: 'https://developers.pipedrive.com/',
  },

  // ----- 跨境电商 ecommerce (5) -----
  {
    provider_id: 'shopify',
    display_name: 'Shopify',
    description: '全球独立站 SaaS — 商品、订单、库存、客户',
    category: 'ecommerce',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Shopify_logo_2018.svg/120px-Shopify_logo_2018.svg.png',
    default_scopes: ['read_products', 'read_orders', 'read_customers'],
    documentation_url: 'https://shopify.dev/docs',
  },
  {
    provider_id: 'shopee',
    display_name: 'Shopee',
    description: '东南亚与拉美主流跨境电商平台',
    category: 'ecommerce',
    icon_url: emojiIcon('🛍️', '#EE4D2D'),
    default_scopes: ['shop.basic', 'order.read', 'product.read'],
    documentation_url: 'https://open.shopee.com/documents',
  },
  {
    provider_id: 'tiktok_shop',
    display_name: 'TikTok Shop',
    description: '抖音 / TikTok 内容电商 — 商品、订单、达人合作',
    category: 'ecommerce',
    icon_url: emojiIcon('🎵', '#000000'),
    default_scopes: ['product.read', 'order.read', 'fulfillment.read'],
    documentation_url: 'https://partner.tiktokshop.com/docv2',
  },
  {
    provider_id: 'amazon_sp',
    display_name: 'Amazon SP-API',
    description: '亚马逊卖家 SP-API — 库存、订单、报告、广告',
    category: 'ecommerce',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/120px-Amazon_logo.svg.png',
    default_scopes: ['sellingpartnerapi::orders', 'sellingpartnerapi::inventory'],
    documentation_url: 'https://developer-docs.amazon.com/sp-api/',
  },
  {
    provider_id: 'alibaba_1688',
    display_name: '1688',
    description: '阿里巴巴中国站 — 批发采购、商品、订单',
    category: 'ecommerce',
    icon_url: emojiIcon('🅰️', '#FF6A00'),
    default_scopes: ['member_basic', 'trade_read', 'product_read'],
    documentation_url: 'https://open.1688.com/',
  },

  // ----- 信息源 info_source (5) -----
  {
    provider_id: 'reddit',
    display_name: 'Reddit',
    description: '全球最大兴趣社区 — 帖子、评论、社区订阅',
    category: 'info_source',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/en/thumb/5/58/Reddit_logo_new.svg/120px-Reddit_logo_new.svg.png',
    default_scopes: ['identity', 'read', 'submit'],
    documentation_url: 'https://www.reddit.com/dev/api',
  },
  {
    provider_id: 'twitter_x',
    display_name: 'X (Twitter)',
    description: 'X / Twitter — 推文、关注、列表、空间',
    category: 'info_source',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/X_icon_2.svg/120px-X_icon_2.svg.png',
    default_scopes: ['tweet.read', 'users.read', 'follows.read'],
    documentation_url: 'https://developer.x.com/en/docs',
  },
  {
    provider_id: 'linkedin',
    display_name: 'LinkedIn',
    description: '全球职业社交网络 — 个人档案、公司、动态',
    category: 'info_source',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/LinkedIn_logo_initials.png/120px-LinkedIn_logo_initials.png',
    default_scopes: ['r_liteprofile', 'r_emailaddress', 'w_member_social'],
    documentation_url: 'https://learn.microsoft.com/linkedin/',
  },
  {
    provider_id: 'youtube',
    display_name: 'YouTube',
    description: 'YouTube Data API — 视频、频道、播放列表、评论',
    category: 'info_source',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/120px-YouTube_full-color_icon_%282017%29.svg.png',
    default_scopes: ['youtube.readonly', 'youtube.upload'],
    documentation_url: 'https://developers.google.com/youtube/v3',
  },
  {
    provider_id: 'tiktok',
    display_name: 'TikTok',
    description: 'TikTok 内容 API — 视频、用户信息、数据洞察',
    category: 'info_source',
    icon_url: emojiIcon('🎬', '#010101'),
    default_scopes: ['user.info.basic', 'video.list'],
    documentation_url: 'https://developers.tiktok.com/',
  },

  // ----- 设计创作 design (3) -----
  {
    provider_id: 'figma',
    display_name: 'Figma',
    description: '协同设计 — 文件、组件、样式、原型',
    category: 'design',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Figma-logo.svg/120px-Figma-logo.svg.png',
    default_scopes: ['files:read', 'file_comments:write'],
    documentation_url: 'https://www.figma.com/developers',
  },
  {
    provider_id: 'canva',
    display_name: 'Canva',
    description: '在线平面设计 — 海报、社媒、品牌素材',
    category: 'design',
    icon_url: emojiIcon('🎨', '#00C4CC'),
    default_scopes: ['design:meta:read', 'asset:read'],
    documentation_url: 'https://www.canva.dev/docs/connect/',
  },
  {
    provider_id: 'higgsfield',
    display_name: 'Higgsfield',
    description: 'AI 视频生成平台 — 文生视频、图生视频',
    category: 'design',
    icon_url: emojiIcon('✨', '#7C3AED'),
    default_scopes: ['video.generate', 'asset.read'],
    documentation_url: 'https://higgsfield.ai',
  },

  // ----- 法务合规 compliance (4) -----
  {
    provider_id: 'fadada',
    display_name: '法大大',
    description: '电子签约 SaaS — 合同发起、签署、存证',
    category: 'compliance',
    icon_url: emojiIcon('📜', '#F25222'),
    default_scopes: ['contract.create', 'contract.sign', 'evidence.read'],
    documentation_url: 'https://open.fadada.com/',
  },
  {
    provider_id: 'esign',
    display_name: 'e签宝',
    description: '杭州天谷电子签 — 合同、印章、身份核验',
    category: 'compliance',
    icon_url: emojiIcon('✍️', '#1677FF'),
    default_scopes: ['sign.create', 'seal.read'],
    documentation_url: 'https://open.esign.cn/',
  },
  {
    provider_id: 'pkulaw',
    display_name: '北大法宝',
    description: '北大法宝 — 法律法规 / 案例 / 论文 / 司法观点检索',
    category: 'compliance',
    icon_url: emojiIcon('⚖️', '#B91C1C'),
    default_scopes: ['law.search', 'case.search'],
    documentation_url: 'https://www.pkulaw.com/',
  },
  {
    provider_id: 'wkinfo',
    display_name: '威科先行',
    description: '威科先行 — 法律法规、税务、人力合规知识库',
    category: 'compliance',
    icon_url: emojiIcon('🏛️', '#0F4C81'),
    default_scopes: ['law.read', 'compliance.search'],
    documentation_url: 'https://law.wkinfo.com.cn/',
  },

  // ----- 税务财务 finance (4) -----
  {
    provider_id: 'kingdee',
    display_name: '金蝶',
    description: '金蝶云 ERP — 总账、应收应付、报表、税务',
    category: 'finance',
    icon_url: emojiIcon('💎', '#0066CC'),
    default_scopes: ['ledger.read', 'voucher.write'],
    documentation_url: 'https://open.kingdee.com/',
  },
  {
    provider_id: 'yonyou',
    display_name: '用友',
    description: '用友 NC/U8 — 财务、供应链、人力',
    category: 'finance',
    icon_url: emojiIcon('🏢', '#D32027'),
    default_scopes: ['finance.read', 'invoice.read'],
    documentation_url: 'https://developer.yonyou.com/',
  },
  {
    provider_id: 'xero',
    display_name: 'Xero',
    description: '新西兰云端会计 — 适用于 SMB 跨境记账',
    category: 'finance',
    icon_url:
      'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Xero_software_logo.svg/120px-Xero_software_logo.svg.png',
    default_scopes: ['accounting.transactions', 'accounting.contacts.read'],
    documentation_url: 'https://developer.xero.com/',
  },
  {
    provider_id: 'quickbooks',
    display_name: 'QuickBooks',
    description: 'Intuit QuickBooks — 北美主流 SMB 财务系统',
    category: 'finance',
    icon_url: emojiIcon('📊', '#2CA01C'),
    default_scopes: ['com.intuit.quickbooks.accounting'],
    documentation_url: 'https://developer.intuit.com/app/developer/qbo/docs/develop',
  },
]

// ===== Authorization 种子（5 条已连接） =====

const seedAuthorizations: AppAuthorization[] = [
  {
    id: 'auth-feishu-1',
    user_id: 'user-mock-1',
    provider_id: 'feishu',
    status: 'connected',
    scopes: ['contact:read', 'im:message:send_as_bot', 'docs:read'],
    connected_at: daysAgo(12),
    last_refresh_at: daysAgo(1),
    error_message: null,
    account_label: 'wenyu@example.com',
  },
  {
    id: 'auth-dingtalk-1',
    user_id: 'user-mock-1',
    provider_id: 'dingtalk',
    status: 'connected',
    scopes: ['contact.user.read', 'message.send'],
    connected_at: daysAgo(20),
    last_refresh_at: daysAgo(2),
    error_message: null,
    account_label: '安心智能助手 · 北京总部',
  },
  {
    id: 'auth-notion-1',
    user_id: 'user-mock-1',
    provider_id: 'notion',
    status: 'connected',
    scopes: ['read_content', 'update_content'],
    connected_at: daysAgo(45),
    last_refresh_at: daysAgo(3),
    error_message: null,
    account_label: 'Anxin Workspace',
  },
  {
    id: 'auth-shopify-1',
    user_id: 'user-mock-1',
    provider_id: 'shopify',
    status: 'connected',
    scopes: ['read_products', 'read_orders', 'read_customers'],
    connected_at: daysAgo(8),
    last_refresh_at: minutesAgo(30),
    error_message: null,
    account_label: 'anxin-store.myshopify.com',
  },
  {
    id: 'auth-fadada-1',
    user_id: 'user-mock-1',
    provider_id: 'fadada',
    status: 'connected',
    scopes: ['contract.create', 'contract.sign', 'evidence.read'],
    connected_at: daysAgo(60),
    last_refresh_at: daysAgo(5),
    error_message: null,
    account_label: '安心智能法律服务（深圳）有限公司',
  },
]

// ===== 可变态（模拟服务端持久化） =====

const providers: AppProvider[] = [...seedProviders]
const authorizations: AppAuthorization[] = [...seedAuthorizations]

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

// ===== Mock 实现 =====

export async function mockListProviders(): Promise<AppProvider[]> {
  await new Promise((r) => setTimeout(r, 120))
  return clone(providers)
}

export async function mockListAuthorizations(): Promise<AppAuthorization[]> {
  await new Promise((r) => setTimeout(r, 140))
  return clone(authorizations)
}

export async function mockStartConnect(
  providerId: string,
): Promise<{ authorize_url: string; state: string }> {
  await new Promise((r) => setTimeout(r, 200))
  const provider = providers.find((p) => p.provider_id === providerId)
  if (!provider) throw new Error(`provider not found: ${providerId}`)
  const state = `mock-state-${providerId}-${Date.now()}`
  return {
    authorize_url: `https://mock.oauth.example.com/${providerId}/authorize?state=${state}`,
    state,
  }
}

/**
 * 在 mock 模式下，"完成 OAuth" 由 ConnectDialog 倒计时后调用此方法直接落库。
 * 真实环境是 callback 回写，此处为前端联调便利。
 */
export async function mockCompleteConnect(
  providerId: string,
): Promise<AppAuthorization> {
  await new Promise((r) => setTimeout(r, 120))
  const provider = providers.find((p) => p.provider_id === providerId)
  if (!provider) throw new Error(`provider not found: ${providerId}`)

  const existing = authorizations.find((a) => a.provider_id === providerId)
  if (existing) {
    existing.status = 'connected'
    existing.last_refresh_at = now()
    existing.error_message = null
    return clone(existing)
  }
  const fresh: AppAuthorization = {
    id: `auth-${providerId}-${Date.now()}`,
    user_id: 'user-mock-1',
    provider_id: providerId,
    status: 'connected',
    scopes: provider.default_scopes,
    connected_at: now(),
    last_refresh_at: now(),
    error_message: null,
    account_label: `${provider.display_name} · 体验账号`,
  }
  authorizations.push(fresh)
  return clone(fresh)
}

export async function mockRefresh(id: string): Promise<AppAuthorization> {
  await new Promise((r) => setTimeout(r, 220))
  const auth = authorizations.find((a) => a.id === id)
  if (!auth) throw new Error(`authorization not found: ${id}`)
  auth.status = 'connected'
  auth.last_refresh_at = now()
  auth.error_message = null
  return clone(auth)
}

export async function mockDisconnect(id: string): Promise<void> {
  await new Promise((r) => setTimeout(r, 160))
  const idx = authorizations.findIndex((a) => a.id === id)
  if (idx === -1) throw new Error(`authorization not found: ${id}`)
  authorizations.splice(idx, 1)
}
