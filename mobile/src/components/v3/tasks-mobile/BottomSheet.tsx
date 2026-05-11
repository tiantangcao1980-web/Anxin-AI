/**
 * BottomSheet — 轻量底部弹层
 *
 * 不引入 @gorhom/bottom-sheet 等外部 native 依赖，使用 Modal + Animated
 * 实现，避免在 Expo Go 里需要原生 link。如果未来要做更复杂的手势拖拽，
 * 可以再升级为 @gorhom/bottom-sheet。
 */
import { useEffect, useRef } from 'react'
import {
  Animated,
  Easing,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useTheme } from '@/lib/theme'

interface Props {
  visible: boolean
  onClose: () => void
  /** 占屏幕高度比例。默认 0.55 */
  heightRatio?: number
  children: React.ReactNode
}

export function BottomSheet({ visible, onClose, heightRatio = 0.55, children }: Props) {
  const t = useTheme()
  const insets = useSafeAreaInsets()
  const translateY = useRef(new Animated.Value(800)).current
  const overlay = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(translateY, {
          toValue: 0,
          duration: 260,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(overlay, {
          toValue: 1,
          duration: 260,
          useNativeDriver: true,
        }),
      ]).start()
    } else {
      Animated.parallel([
        Animated.timing(translateY, {
          toValue: 800,
          duration: 200,
          easing: Easing.in(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(overlay, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start()
    }
  }, [visible, translateY, overlay])

  return (
    <Modal
      transparent
      visible={visible}
      onRequestClose={onClose}
      animationType="none"
      statusBarTranslucent
    >
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <Animated.View style={[styles.overlay, { opacity: overlay }]}>
          <Pressable style={styles.flex} onPress={onClose} />
        </Animated.View>
        <Animated.View
          style={[
            styles.sheet,
            {
              backgroundColor: t.background,
              transform: [{ translateY }],
              paddingBottom: insets.bottom + 16,
              maxHeight: `${Math.round(heightRatio * 100)}%`,
            },
          ]}
        >
          <View style={[styles.handle, { backgroundColor: t.border }]} />
          {children}
        </Animated.View>
      </KeyboardAvoidingView>
    </Modal>
  )
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.45)',
  },
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingHorizontal: 16,
    paddingTop: 8,
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: -4 },
    elevation: 12,
  },
  handle: {
    width: 44,
    height: 4,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 12,
  },
})
