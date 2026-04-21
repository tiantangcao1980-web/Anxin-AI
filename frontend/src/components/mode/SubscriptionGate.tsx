/**
 * SubscriptionGate — 全局订阅引导弹窗（V2 架构）
 *
 * 订阅不足时（ModeGate.requestModeSwitch 返回 false），
 * 全局显示订阅升级引导，引导用户跳转到 /pricing。
 *
 * 使用方式：在 App.tsx 顶层挂载一次即可。
 */

import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { usePrivacy } from '@/context/PrivacyContext'
import { Button } from '@/components/ui/button'

export function SubscriptionGate() {
  const navigate = useNavigate()
  const { subscriptionRequired, setSubscriptionRequired } = usePrivacy()

  const handleSubscribe = () => {
    setSubscriptionRequired(false)
    navigate('/pricing')
  }

  const handleStartTrial = async () => {
    try {
      const { billingApi } = await import('@/lib/api')
      const { toast } = await import('sonner')
      await billingApi.createTrial('needer')
      toast.success('已开通 3 天免费试用，请重新切换模式')
      setSubscriptionRequired(false)
    } catch (e: any) {
      const { toast } = await import('sonner')
      toast.error(e?.message || '试用开通失败')
    }
  }

  return (
    <AnimatePresence>
      {subscriptionRequired && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          onClick={() => setSubscriptionRequired(false)}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card border border-border rounded-2xl shadow-xl max-w-md w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <icons.Sparkles className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground">订阅以解锁云端能力</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  混合/云端模式需要订阅。升级后可使用：
                </p>
              </div>
            </div>

            <div className="space-y-2 mb-5 ml-1">
              {[
                { icon: icons.Sparkles, text: '云端高级 AI 模型（响应更快、更精准）' },
                { icon: icons.Search, text: '舆情监测、尽职调查、找律师' },
                { icon: icons.Database, text: '法律智库全量检索、知识图谱' },
                { icon: icons.MessageCircle, text: '团队即时通讯与实时协作' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <item.icon className="w-4 h-4 text-primary shrink-0" />
                  <span className="text-xs text-foreground">{item.text}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-2">
              <Button onClick={handleSubscribe} className="w-full">
                <icons.DollarSign className="w-4 h-4 mr-1.5" />
                查看订阅方案
              </Button>
              <Button onClick={handleStartTrial} variant="outline" className="w-full">
                <icons.Clock className="w-4 h-4 mr-1.5" />
                免费试用 3 天（无需支付）
              </Button>
              <button
                onClick={() => setSubscriptionRequired(false)}
                className="w-full text-xs text-muted-foreground hover:text-foreground mt-1"
              >
                暂不订阅，继续使用本地模式
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
