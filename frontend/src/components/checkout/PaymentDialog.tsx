/**
 * PaymentDialog - 支付确认对话框
 *
 * Demo 版：显示订单详情 + mock 支付二维码
 * 真实版：接入微信/支付宝 SDK
 */

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

interface PaymentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  order: {
    orderId: string
    planName: string
    amount: number
    paymentMethod: 'wechat' | 'alipay'
  } | null
}

export function PaymentDialog({ open, onOpenChange, order }: PaymentDialogProps) {
  const [countdown, setCountdown] = useState(300) // 5分钟倒计时
  const [mockPaid, setMockPaid] = useState(false)

  useEffect(() => {
    if (!open) {
      setCountdown(300)
      setMockPaid(false)
      return
    }

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          toast.error('支付超时，请重新下单')
          onOpenChange(false)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [open, onOpenChange])

  if (!order) return null

  const minutes = Math.floor(countdown / 60)
  const seconds = countdown % 60

  const handleMockPay = () => {
    setMockPaid(true)
    toast.success('支付成功！订阅已激活')
    setTimeout(() => {
      onOpenChange(false)
      window.location.href = '/my-subscription'
    }, 1500)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {order.paymentMethod === 'wechat' ? (
              <icons.Smartphone className="h-5 w-5 text-green-600" />
            ) : (
              <icons.CreditCard className="h-5 w-5 text-blue-600" />
            )}
            {order.paymentMethod === 'wechat' ? '微信支付' : '支付宝'}
          </DialogTitle>
          <DialogDescription>
            请使用{order.paymentMethod === 'wechat' ? '微信' : '支付宝'}扫码支付
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 订单信息 */}
          <div className="bg-muted/50 rounded-lg p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">套餐</span>
              <span className="font-medium">{order.planName}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">订单号</span>
              <span className="font-mono text-xs">{order.orderId}</span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t">
              <span className="text-muted-foreground">应付金额</span>
              <span className="text-2xl font-bold text-primary">
                ¥{order.amount.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Demo 版：Mock 二维码 */}
          <div className="flex flex-col items-center gap-3 py-4">
            <Badge variant="outline" className="text-orange-600 border-orange-600">
              演示版 - Mock 支付
            </Badge>
            <div className="w-48 h-48 bg-muted rounded-lg flex items-center justify-center">
              <div className="text-center space-y-2">
                <icons.QrCode className="h-16 w-16 mx-auto text-muted-foreground" />
                <p className="text-xs text-muted-foreground">
                  真实版将显示支付二维码
                </p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              剩余时间：{minutes}:{seconds.toString().padStart(2, '0')}
            </p>
          </div>

          {/* Demo 版：模拟支付按钮 */}
          {!mockPaid && (
            <Button
              onClick={handleMockPay}
              className="w-full"
              variant="outline"
            >
              <icons.Check className="h-4 w-4 mr-2" />
              模拟支付成功（仅演示）
            </Button>
          )}

          {mockPaid && (
            <div className="flex items-center justify-center gap-2 text-green-600 py-2">
              <icons.CheckCircle className="h-5 w-5" />
              <span className="font-medium">支付成功，正在跳转...</span>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
