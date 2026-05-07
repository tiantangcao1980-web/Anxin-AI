/**
 * PaymentPanel - 支付面板组件
 *
 * 在聊天/委托流程中展示支付信息，支持微信支付、支付宝渠道选择。
 * 包含订单摘要、支付方式选择、二维码展示区、支付状态指示。
 */

import { useState, useEffect, useCallback } from'react'
import { icons } from'@/lib/icons'
import { API_BASE_URL, buildApiHeaders } from'@/lib/api'
import { getTokenStorage } from'@/lib/platform/storage'
import {
 cardStyle,
 heading,
 buttonStyle,
 iconSize,
 statusBadge,
 spacing,
 radius,
 statusColor,
} from'@/lib/design-tokens'

// ========== 类型 ==========

type PaymentMethod ='wechat_pay' |'alipay'

type PaymentStatus ='idle' |'pending' |'success' |'failed'

interface OrderInfo {
 orderId?: string
 type: string
 amount: number
 description: string
 relatedId?: string
}

interface PaymentPanelProps {
 /** 订单信息 */
 order: OrderInfo
 /** 支付完成回调 */
 onPaymentComplete?: (orderId: string) => void
 /** 取消支付回调 */
 onCancel?: () => void
 /** 自定义 className */
 className?: string
}

// ========== 订单类型中文映射 ==========

const ORDER_TYPE_LABELS: Record<string, string> = {
 consultation_fee:'法律咨询费',
 delegation_deposit:'委托保证金',
 subscription:'会员订阅',
 contract_signing:'合同签署费',
}

// ========== 组件 ==========

export default function PaymentPanel({
 order,
 onPaymentComplete,
 onCancel,
 className ='',
}: PaymentPanelProps) {
 const paymentMethodStyle = {
 wechat_pay: {
 selected:'border-success/35 bg-success/10 text-success',
 idle:'border-border bg-background text-muted-foreground hover:border-success/30 hover:bg-success/5 hover:text-success',
 },
 alipay: {
 selected:'border-info/35 bg-info/10 text-info',
 idle:'border-border bg-background text-muted-foreground hover:border-info/30 hover:bg-info/5 hover:text-info',
 },
 } as const

 const [method, setMethod] = useState<PaymentMethod>('wechat_pay')
 const [status, setStatus] = useState<PaymentStatus>('idle')
 const [orderId, setOrderId] = useState<string | undefined>(order.orderId)
 const [qrCode, setQrCode] = useState<string | null>(null)
 const [polling, setPolling] = useState(false)

 // 模拟创建订单
 const handleConfirmPay = useCallback(async () => {
 setStatus('pending')

 try {
 const token = await getTokenStorage().getAccessToken()

 const res = await fetch(`${API_BASE_URL}/payments/orders`, {
 method:'POST',
 headers: buildApiHeaders(undefined, { token }),
 body: JSON.stringify({
 type: order.type,
 amount: order.amount,
 description: order.description,
 related_id: order.relatedId,
 provider: method,
 }),
 })

 if (!res.ok) {
 setStatus('failed')
 return
 }

 const data = await res.json()
 setOrderId(data.id)
 setQrCode(data.qr_code || null)
 setPolling(true)
 } catch {
 setStatus('failed')
 }
 }, [method, order])

 // 轮询支付状态
 useEffect(() => {
 if (!polling || !orderId) return

 const interval = setInterval(async () => {
 try {
 const token = await getTokenStorage().getAccessToken()

 const res = await fetch(`${API_BASE_URL}/payments/orders/${orderId}`, {
 headers: buildApiHeaders(undefined, { token, json: false }),
 })

 if (res.ok) {
 const data = await res.json()
 if (data.status ==='paid') {
 setStatus('success')
 setPolling(false)
 onPaymentComplete?.(orderId)
 } else if (data.status ==='failed' || data.status ==='closed') {
 setStatus('failed')
 setPolling(false)
 }
 }
 } catch {
 // 静默忽略轮询错误
 }
 }, 3000)

 return () => clearInterval(interval)
 }, [polling, orderId, onPaymentComplete])

 return (
 <div className={`${cardStyle.base} ${className}`}>
 {/* 标题 */}
 <div className="flex items-center gap-2 mb-4">
 <icons.CreditCard className={`${iconSize.md} text-primary`} />
 <h3 className={heading.section}>支付确认</h3>
 </div>

 {/* 订单摘要 */}
 <div className={`${cardStyle.flat} mb-4`}>
 <div className="flex justify-between items-center mb-2">
 <span className={heading.muted}>服务类型</span>
 <span className={heading.card}>
 {ORDER_TYPE_LABELS[order.type] || order.type}
 </span>
 </div>
 <div className="flex justify-between items-center mb-2">
 <span className={heading.muted}>订单描述</span>
 <span className={`${heading.card} max-w-[200px] truncate`}>
 {order.description}
 </span>
 </div>
 <div className="flex justify-between items-center pt-2 border-t border-border">
 <span className={heading.muted}>应付金额</span>
 <span className="text-lg font-semibold text-primary">
 &yen;{order.amount.toFixed(2)}
 </span>
 </div>
 </div>

 {/* 支付方式选择 */}
 {status ==='idle' && (
 <>
 <div className="mb-4">
 <p className={`${heading.muted} mb-3`}>选择支付方式</p>
 <div className="grid grid-cols-2 gap-3">
 {/* 微信支付 */}
 <button
 onClick={() => setMethod('wechat_pay')}
 className={`flex items-center justify-center gap-2 px-4 py-3 ${radius.button} border transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-success/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
 method ==='wechat_pay'
 ? paymentMethodStyle.wechat_pay.selected
 : paymentMethodStyle.wechat_pay.idle
 }`}
 >
 <svg viewBox="0 0 24 24" className={iconSize.md} fill="currentColor">
 <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05a6.46 6.46 0 0 1-.248-1.753c0-3.694 3.431-6.698 7.655-6.698.246 0 .487.018.728.037C16.862 4.684 13.084 2.188 8.691 2.188zm-2.87 4.401c.611 0 1.107.496 1.107 1.107 0 .612-.496 1.108-1.108 1.108-.611 0-1.107-.496-1.107-1.108 0-.611.496-1.107 1.107-1.107zm5.809 0c.612 0 1.107.496 1.107 1.107 0 .612-.495 1.108-1.107 1.108-.612 0-1.108-.496-1.108-1.108 0-.611.496-1.107 1.108-1.107zm3.28 4.078c-3.652 0-6.618 2.614-6.618 5.836 0 3.223 2.966 5.836 6.618 5.836a7.887 7.887 0 0 0 2.227-.318.669.669 0 0 1 .559.076l1.482.867a.254.254 0 0 0 .13.042.229.229 0 0 0 .226-.229c0-.056-.023-.111-.037-.166l-.304-1.152a.458.458 0 0 1 .166-.517c1.425-1.049 2.336-2.6 2.336-4.34 0-3.221-2.966-5.835-6.618-5.835h-.167zm-2.09 3.31c.475 0 .861.385.861.86 0 .476-.386.862-.861.862a.862.862 0 0 1-.862-.861c0-.476.386-.861.862-.861zm4.343 0c.475 0 .861.385.861.86 0 .476-.386.862-.861.862a.862.862 0 0 1-.862-.861c0-.476.386-.861.862-.861z" />
 </svg>
 <span className="text-sm font-medium">微信支付</span>
 </button>

 {/* 支付宝 */}
 <button
 onClick={() => setMethod('alipay')}
 className={`flex items-center justify-center gap-2 px-4 py-3 ${radius.button} border transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-info/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
 method ==='alipay'
 ? paymentMethodStyle.alipay.selected
 : paymentMethodStyle.alipay.idle
 }`}
 >
 <svg viewBox="0 0 24 24" className={iconSize.md} fill="currentColor">
 <path d="M21.422 15.358c-.6-.252-3.903-1.686-5.058-2.153.48-.876.87-1.828 1.142-2.842h-3.376v-1.17h4.073v-.676h-4.073V6.89h-1.678s.018-.405.018-.586c0 0-.72.12-.978.174v1.908H7.44v.676h4.042v1.17H7.846v.676h6.67c-.216.624-.486 1.212-.81 1.752-1.83-.702-3.87-1.272-5.388-.846-2.076.582-3.174 2.436-2.886 4.248.288 1.806 2.34 3.204 4.794 2.616 1.62-.39 3.072-1.65 4.242-3.39.978.516 4.524 2.25 4.524 2.25L21.422 15.358zM9.666 20.248c-2.07.6-3.792-.498-4.026-1.8-.234-1.302.576-2.784 2.268-3.258.522-.144 1.086-.162 1.686-.054 1.128.204 2.334.756 3.444 1.362-1.044 1.656-2.34 3.348-3.372 3.75z" />
 <path d="M22.5 0h-21A1.5 1.5 0 0 0 0 1.5v21A1.5 1.5 0 0 0 1.5 24h21a1.5 1.5 0 0 0 1.5-1.5v-21A1.5 1.5 0 0 0 22.5 0zm-1.078 17.544s-2.04-.87-3.072-1.326c-1.518 2.268-3.672 3.636-6.36 3.636-3.444 0-5.28-2.238-4.722-4.746.396-1.746 1.866-3.258 4.608-3.258 1.596 0 3.504.57 5.478 1.404.492-.924.852-1.926 1.068-2.988H8.4v-.676h4.56V8.42H7.44v-.676h5.52V5.982s.018-.342.072-.522c0 0 .774-.132 1.578-.132v2.416h5.52v.676h-5.52v1.17h4.5c-.294 1.482-.822 2.874-1.536 4.11 1.362.576 4.992 2.208 4.992 2.208l-1.644 1.636z" />
 </svg>
 <span className="text-sm font-medium">支付宝</span>
 </button>
 </div>
 </div>

 {/* 资金托管说明 */}
 <div className={`flex items-start gap-2 mb-4 p-3 ${statusColor.info} ${radius.badge}`}>
 <icons.Shield className={`${iconSize.sm} mt-0.5 shrink-0`} />
 <p className="text-xs leading-relaxed">
 资金将托管在平台，服务完成后释放给律师
 </p>
 </div>

 {/* 操作按钮 */}
 <div className="flex gap-3">
 {onCancel && (
 <button onClick={onCancel} className={`flex-1 ${buttonStyle.secondary}`}>
 取消
 </button>
 )}
 <button onClick={handleConfirmPay} className={`flex-1 ${buttonStyle.primary}`}>
 确认支付
 </button>
 </div>
 </>
 )}

 {/* 待支付 - 展示二维码 */}
 {status ==='pending' && (
 <div className="text-center py-4">
 <div className={`inline-flex flex-col items-center gap-3 p-6 ${cardStyle.flat} mb-4`}>
 {qrCode ? (
 <>
 <icons.QrCode className="w-32 h-32 text-muted-foreground/30" />
 <p className={heading.muted}>
 请使用{method ==='wechat_pay' ?'微信' :'支付宝'}扫描二维码
 </p>
 </>
 ) : (
 <>
 <icons.Loader2 className={`${iconSize.xl} text-primary animate-spin`} />
 <p className={heading.muted}>正在生成支付信息...</p>
 </>
 )}
 </div>

 <div className="flex items-center justify-center gap-2 mb-4">
 <icons.Clock className={`${iconSize.sm} text-warning`} />
 <span className={`${heading.micro} text-warning`}>
 订单将在 30 分钟后自动关闭
 </span>
 </div>

 {/* 模拟支付成功按钮（仅开发环境） */}
 <button
 onClick={() => {
 setStatus('success')
 setPolling(false)
 if (orderId) onPaymentComplete?.(orderId)
 }}
 className={`${buttonStyle.ghost} text-xs`}
 >
 <icons.RefreshCw className={`${iconSize.xs} mr-1 inline`} />
 模拟支付成功（开发模式）
 </button>
 </div>
 )}

 {/* 支付成功 */}
 {status ==='success' && (
 <div className="text-center py-6">
 <icons.CheckCircle2 className="w-12 h-12 text-success mx-auto mb-3" />
 <p className={heading.section}>支付成功</p>
 <p className={`${heading.muted} mt-1`}>
 订单号：{orderId?.slice(0, 8)}...
 </p>
 <div
 className={`inline-block mt-3 px-3 py-1 text-xs font-medium ${radius.badge} ${statusBadge.success}`}
 >
 已支付 &yen;{order.amount.toFixed(2)}
 </div>
 </div>
 )}

 {/* 支付失败 */}
 {status ==='failed' && (
 <div className="text-center py-6">
 <icons.XCircle className="w-12 h-12 text-destructive mx-auto mb-3" />
 <p className={heading.section}>支付失败</p>
 <p className={`${heading.muted} mt-1`}>请稍后重试或更换支付方式</p>
 <button
 onClick={() => {
 setStatus('idle')
 setQrCode(null)
 }}
 className={`mt-4 ${buttonStyle.primary}`}
 >
 重新支付
 </button>
 </div>
 )}
 </div>
 )
}
