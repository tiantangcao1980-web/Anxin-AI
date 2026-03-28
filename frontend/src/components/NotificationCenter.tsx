
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, heading, buttonStyle, statusBadge, iconSize } from '@/lib/design-tokens';
import { notificationsApi, Notification } from '../lib/api';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface NotificationCenterProps {
  onClose: () => void;
  onClearAll: () => void; // Keeping this prop for now, but implementation will be internal
}

export function NotificationCenter({ onClose }: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    try {
      const response = await notificationsApi.list({ limit: 50 });
      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
      toast.error('获取通知失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationsApi.markAsRead(id);
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: true } : n)
      );
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsApi.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      toast.success('已全部标记为已读');
    } catch (error) {
      console.error('Failed to mark all as read:', error);
      toast.error('操作失败');
    }
  };

  const typeConfig = {
    urgent: { badge: statusBadge.error, text: 'text-destructive', icon: icons.AlertCircle },
    warning: { badge: statusBadge.warning, text: 'text-amber-600 dark:text-amber-400', icon: icons.AlertCircle },
    info: { badge: statusBadge.info, text: 'text-primary', icon: icons.Bell },
    success: { badge: statusBadge.success, text: 'text-emerald-600 dark:text-emerald-400', icon: icons.Check },
  };

  const getIcon = (type: string) => {
    const config = typeConfig[type as keyof typeof typeConfig];
    return config ? config.icon : icons.Bell;
  };

  const getConfig = (type: string) => {
    const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.info;
    return config;
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
      >
        <motion.div
          initial={{ opacity: 0, x: 320 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 320 }}
          onClick={(e) => e.stopPropagation()}
          className="absolute right-0 top-0 bottom-0 w-96 bg-background shadow-2xl flex flex-col"
        >
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <icons.Bell className={`${iconSize.md} text-muted-foreground`} />
                <h2 className={heading.section}>通知中心</h2>
              </div>
              <button
                onClick={onClose}
                className={buttonStyle.icon}
              >
                <icons.X className={`${iconSize.md} text-muted-foreground`} />
              </button>
            </div>
            <button
              onClick={handleMarkAllAsRead}
              className={buttonStyle.ghost}
            >
              全部标记为已读
            </button>
          </div>

          {/* Notifications List */}
          <div className="flex-1 overflow-y-auto p-4">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <icons.Loader2 className={`${iconSize.lg} animate-spin text-muted-foreground`} />
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <icons.Bell className={`${iconSize['2xl']} mb-2 opacity-20`} />
                <p>暂无通知</p>
              </div>
            ) : (
              <div className="space-y-3">
                {notifications.map((notification, index) => {
                  const config = getConfig(notification.type);
                  const Icon = getIcon(notification.type);

                  return (
                    <motion.div
                      key={notification.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => !notification.is_read && handleMarkAsRead(notification.id)}
                      className={`${cardStyle.interactive} ${config.badge} active:scale-98 ${
                        !notification.is_read ? 'border-l-4' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-9 h-9 rounded-xl ${config.badge} flex items-center justify-center flex-shrink-0`}>
                          <Icon className={`${iconSize.sm} ${config.text}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className={heading.card}>{notification.title}</h4>
                            {!notification.is_read && (
                              <div className="w-2 h-2 bg-primary rounded-full flex-shrink-0"></div>
                            )}
                          </div>
                          <p className={`${heading.muted} text-foreground/80 leading-relaxed mb-2`}>
                            {notification.message}
                          </p>
                          <p className={heading.micro}>
                            {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true, locale: zhCN })}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-border">
            <button className={`w-full ${buttonStyle.ghost} text-primary`}>
              查看全部通知
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
