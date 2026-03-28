/**
 * A2UI 扩展组件集合
 *
 * 预留接口的前端实现 — 提供基础 UI 框架，
 * 未来可逐步替换为完整功能组件。
 *
 * 包含：
 * - MapView: 地图视图（律所/法院位置）
 * - PaymentCard: 支付卡片
 * - LawyerPicker: 律师选择器
 * - MediaCard: 媒体预览
 * - SchedulePicker: 日程预约
 * - FeedbackCard: 评价反馈
 * - PluginContainer: 通用插件容器（Skills/MCP）
 */

import { memo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import type {
  MapViewComponent, PaymentCardComponent, LawyerPickerComponent,
  MediaCardComponent, SchedulePickerComponent, FeedbackCardComponent,
  PluginContainerComponent, A2UIEventHandler,
} from '../types';

// ========== 地图视图 ==========

export const MapView = memo(function MapView({
  component, onEvent,
}: { component: MapViewComponent; onEvent: A2UIEventHandler }) {
  const { title, markers = [], mapProvider = 'amap', action } = component.data;

  return (
    <div className="bg-background rounded-xl border border-border overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-border/50 flex items-center gap-2">
        <icons.MapPin className="w-4 h-4 text-primary" />
        <span className="text-sm font-medium text-foreground">{title}</span>
        <span className="ml-auto text-[10px] text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
          {mapProvider === 'amap' ? '高德地图' : mapProvider === 'bmap' ? '百度地图' : 'Google Maps'}
        </span>
      </div>
      {/* 地图占位区 — 未来对接真实地图 SDK */}
      <div className="h-48 bg-primary/5 flex items-center justify-center relative">
        <div className="text-center">
          <icons.Globe className="w-8 h-8 text-primary/40 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">地图加载中...</p>
          <p className="text-[10px] text-muted-foreground mt-1">地图功能即将开放</p>
        </div>
        {/* 标记点提示 */}
        {markers.length > 0 && (
          <div className="absolute bottom-2 left-2 right-2 flex gap-2 overflow-x-auto pb-1">
            {markers.map((m) => (
              <div key={m.id} className="flex-shrink-0 bg-background/90 backdrop-blur-sm rounded-lg px-2.5 py-1.5 shadow-sm border border-border text-[11px]">
                <div className="font-medium text-foreground/80">{m.label}</div>
                {m.info && <div className="text-muted-foreground mt-0.5">{m.info}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
      {action && (
        <button
          onClick={() => onEvent({ type: 'action', actionId: action.actionId, componentId: component.id })}
          className="w-full px-4 py-2.5 text-sm text-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-1.5 border-t border-border/50"
        >
          <icons.ExternalLink className="w-3.5 h-3.5" />
          {action.label}
        </button>
      )}
    </div>
  );
});

// ========== 支付卡片 ==========

export const PaymentCard = memo(function PaymentCard({
  component, onEvent,
}: { component: PaymentCardComponent; onEvent: A2UIEventHandler }) {
  const { title, amount, currency = 'CNY', description, paymentMethods = [], payAction, cancelAction } = component.data;
  const [selectedMethod, setSelectedMethod] = useState(paymentMethods[0]?.id || '');

  const currencySymbol = currency === 'CNY' ? '¥' : currency === 'USD' ? '$' : currency;

  return (
    <div className="bg-background rounded-xl border border-border overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-border/50 flex items-center gap-2">
        <icons.DollarSign className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium text-foreground">{title}</span>
      </div>
      <div className="px-4 py-4">
        {/* 金额展示 */}
        <div className="text-center mb-4">
          <div className="text-3xl font-bold text-foreground">
            {currencySymbol}<span className="tabular-nums">{amount.toFixed(2)}</span>
          </div>
          {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
        </div>
        {/* 支付方式选择 */}
        {paymentMethods.length > 0 && (
          <div className="space-y-2 mb-4">
            <p className="text-xs text-muted-foreground font-medium">选择支付方式</p>
            {paymentMethods.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMethod(m.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors ${
                  selectedMethod === m.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-border/80'
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
                  <icons.DollarSign className="w-4 h-4" />
                </div>
                <span className="text-sm font-medium text-foreground/80">{m.name}</span>
                {selectedMethod === m.id && <icons.Check className="w-4 h-4 text-primary ml-auto" />}
              </button>
            ))}
          </div>
        )}
        {/* 提示 */}
        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-800 rounded-lg px-3 py-2 mb-4">
          <p className="text-[11px] text-amber-700 dark:text-amber-400">支付功能即将开放，敬请期待</p>
        </div>
      </div>
      {/* 操作区 */}
      <div className="px-4 pb-4 flex gap-2">
        {cancelAction && (
          <button
            onClick={() => onEvent({ type: 'action', actionId: cancelAction.actionId, componentId: component.id })}
            className="flex-1 px-4 py-2.5 text-sm text-muted-foreground bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            {cancelAction.label}
          </button>
        )}
        {payAction && (
          <button
            onClick={() => onEvent({
              type: 'action', actionId: payAction.actionId, componentId: component.id,
              payload: { method: selectedMethod, amount },
            })}
            className="flex-1 px-4 py-2.5 text-sm text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors font-medium"
          >
            {payAction.label}
          </button>
        )}
      </div>
    </div>
  );
});

// ========== 律师选择器 ==========

export const LawyerPicker = memo(function LawyerPicker({
  component, onEvent,
}: { component: LawyerPickerComponent; onEvent: A2UIEventHandler }) {
  const { title, lawyers = [], filters = [], sortOptions = [] } = component.data;

  return (
    <div className="bg-background rounded-xl border border-border overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-border/50 flex items-center gap-2">
        <icons.Users className="w-4 h-4 text-primary" />
        <span className="text-sm font-medium text-foreground">{title}</span>
        <span className="ml-auto text-[10px] text-muted-foreground">{lawyers.length} 位律师</span>
      </div>
      {/* 筛选排序栏 */}
      {(filters.length > 0 || sortOptions.length > 0) && (
        <div className="px-4 py-2 border-b border-border/50 flex gap-2 overflow-x-auto">
          {filters.map((f) => (
            <button key={f.id} className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 text-[11px] text-muted-foreground bg-muted hover:bg-muted/80 rounded-full transition-colors">
              <icons.Filter className="w-3 h-3" />
              {f.label}
            </button>
          ))}
          {sortOptions.map((s) => (
            <button key={s.id} className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 text-[11px] text-muted-foreground bg-muted hover:bg-muted/80 rounded-full transition-colors">
              <icons.List className="w-3 h-3" />
              {s.label}
            </button>
          ))}
        </div>
      )}
      {/* 律师列表占位 — 实际渲染由 A2UIRenderer 递归处理 */}
      <div className="p-3 space-y-2">
        {lawyers.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            <icons.Users className="w-8 h-8 mx-auto mb-2 text-muted-foreground/50" />
            暂无符合条件的律师
          </div>
        ) : (
          <div className="text-center py-4 text-muted-foreground text-[11px]">
            律师选择器功能即将开放
          </div>
        )}
      </div>
    </div>
  );
});

// ========== 媒体卡片 ==========

export const MediaCard = memo(function MediaCard({
  component, onEvent,
}: { component: MediaCardComponent; onEvent: A2UIEventHandler }) {
  const { title, mediaType, url, thumbnail, description, size, action } = component.data;

  const iconMap = {
    image: icons.Image,
    video: icons.SkipForward,
    pdf: icons.FileText,
    document: icons.FileText,
  };
  const Icon = iconMap[mediaType] || icons.FileText;

  return (
    <div className="bg-background rounded-xl border border-border overflow-hidden shadow-sm">
      {/* 预览区 */}
      {thumbnail || mediaType === 'image' ? (
        <div className="h-40 bg-muted flex items-center justify-center">
          {thumbnail ? (
            <img src={thumbnail} alt={title} className="w-full h-full object-cover" />
          ) : (
            <Icon className="w-10 h-10 text-muted-foreground/50" />
          )}
        </div>
      ) : (
        <div className="h-24 bg-muted/50 flex items-center justify-center">
          <Icon className="w-10 h-10 text-muted-foreground/50" />
        </div>
      )}
      {/* 信息 */}
      <div className="px-4 py-3">
        <h4 className="text-sm font-medium text-foreground truncate">{title}</h4>
        {description && <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{description}</p>}
        <div className="flex items-center gap-2 mt-2">
          <span className="text-[10px] text-muted-foreground bg-muted px-2 py-0.5 rounded-full uppercase">{mediaType}</span>
          {size && <span className="text-[10px] text-muted-foreground">{size}</span>}
        </div>
      </div>
      {action && (
        <button
          onClick={() => onEvent({ type: 'action', actionId: action.actionId, componentId: component.id })}
          className="w-full px-4 py-2.5 text-sm text-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-1.5 border-t border-border/50"
        >
          <icons.Download className="w-3.5 h-3.5" />
          {action.label}
        </button>
      )}
    </div>
  );
});

// ========== 日程预约 ==========

export const SchedulePicker = memo(function SchedulePicker({
  component, onEvent,
}: { component: SchedulePickerComponent; onEvent: A2UIEventHandler }) {
  const { title, subtitle, availableSlots = [], onSelectAction } = component.data;
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);

  // 按日期分组
  const slotsByDate = availableSlots.reduce<Record<string, typeof availableSlots>>((acc, slot) => {
    (acc[slot.date] = acc[slot.date] || []).push(slot);
    return acc;
  }, {});

  return (
    <div className="bg-background rounded-xl border border-border overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <icons.Calendar className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-foreground">{title}</span>
        </div>
        {subtitle && <p className="text-[11px] text-muted-foreground mt-0.5 ml-6">{subtitle}</p>}
      </div>
      <div className="p-4 space-y-3 max-h-64 overflow-y-auto">
        {Object.entries(slotsByDate).map(([date, slots]) => (
          <div key={date}>
            <p className="text-[11px] text-muted-foreground font-medium mb-1.5">{date}</p>
            <div className="flex flex-wrap gap-1.5">
              {slots.map((slot) => (
                <button
                  key={slot.id}
                  disabled={!slot.available}
                  onClick={() => setSelectedSlot(slot.id)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] transition-colors ${
                    !slot.available
                      ? 'bg-muted text-muted-foreground/50 cursor-not-allowed'
                      : selectedSlot === slot.id
                        ? 'bg-primary text-white'
                        : 'bg-muted text-muted-foreground hover:bg-primary/5 hover:text-primary'
                  }`}
                >
                  <icons.Clock className="w-3 h-3 inline mr-1" />
                  {slot.time}
                </button>
              ))}
            </div>
          </div>
        ))}
        {availableSlots.length === 0 && (
          <p className="text-center text-muted-foreground text-sm py-4">暂无可用时段</p>
        )}
      </div>
      {onSelectAction && selectedSlot && (
        <div className="px-4 pb-3">
          <button
            onClick={() => onEvent({
              type: 'action', actionId: onSelectAction.actionId, componentId: component.id,
              payload: { slotId: selectedSlot },
            })}
            className="w-full py-2.5 text-sm text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors font-medium"
          >
            {onSelectAction.label}
          </button>
        </div>
      )}
    </div>
  );
});

// ========== 评价反馈 ==========

export const FeedbackCard = memo(function FeedbackCard({
  component, onEvent,
}: { component: FeedbackCardComponent; onEvent: A2UIEventHandler }) {
  const { title, ratingEnabled = true, commentEnabled = true, tags = [], submitAction } = component.data;
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  return (
    <div className="bg-background rounded-xl border border-border overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-border/50 flex items-center gap-2">
        <icons.Star className="w-4 h-4 text-amber-500" />
        <span className="text-sm font-medium text-foreground">{title}</span>
      </div>
      <div className="px-4 py-4 space-y-4">
        {/* 星级评分 */}
        {ratingEnabled && (
          <div className="flex items-center justify-center gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <button key={i} onClick={() => setRating(i)} className="transition-transform hover:scale-110">
                <icons.Star className={`w-7 h-7 ${i <= rating ? 'text-amber-400 fill-amber-400' : 'text-muted-foreground/30'}`} />
              </button>
            ))}
          </div>
        )}
        {/* 标签 */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 justify-center">
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-3 py-1 rounded-full text-[11px] transition-colors ${
                  selectedTags.includes(tag)
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'bg-muted text-muted-foreground border border-border hover:border-border/80'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
        {/* 评论输入 */}
        {commentEnabled && (
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="请留下您的评价..."
            className="w-full px-3 py-2 text-sm border border-border rounded-lg resize-none focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
            rows={3}
          />
        )}
      </div>
      {submitAction && (
        <div className="px-4 pb-4">
          <button
            onClick={() => onEvent({
              type: 'form-submit', actionId: submitAction.actionId, componentId: component.id,
              formData: { rating, comment, tags: selectedTags },
            })}
            className="w-full py-2.5 text-sm text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors font-medium flex items-center justify-center gap-1.5"
          >
            <icons.ThumbsUp className="w-3.5 h-3.5" />
            {submitAction.label}
          </button>
        </div>
      )}
    </div>
  );
});

// ========== 通用插件容器 ==========

export const PluginContainer = memo(function PluginContainer({
  component, onEvent,
}: { component: PluginContainerComponent; onEvent: A2UIEventHandler }) {
  const { pluginType, title, config, fallbackText = '该功能即将开放' } = component.data;

  return (
    <div className="bg-background rounded-xl border border-dashed border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border/50 flex items-center gap-2">
        <icons.Wrench className="w-4 h-4 text-primary" />
        <span className="text-sm font-medium text-foreground">{title || `插件: ${pluginType}`}</span>
        <span className="ml-auto text-[10px] text-primary bg-primary/5 px-2 py-0.5 rounded-full">{pluginType}</span>
      </div>
      <div className="px-4 py-6 text-center">
        <icons.Wrench className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">{fallbackText}</p>
        <p className="text-[10px] text-muted-foreground mt-1">
          此功能将通过 Skills/MCP 扩展提供
        </p>
      </div>
    </div>
  );
});
