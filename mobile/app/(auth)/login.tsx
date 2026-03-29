// -*- coding: utf-8 -*-
import { useState, useEffect, useRef } from 'react'
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
} from 'react-native'
import { router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { useAuthStore } from '@/lib/store'
import type { User } from '@/types/api'

export default function LoginScreen() {
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [countdown, setCountdown] = useState(0)
  const [loading, setLoading] = useState(false)
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const codeInputRef = useRef<TextInput>(null)
  const { setAuth } = useAuthStore()

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const isPhoneValid = /^1[3-9]\d{9}$/.test(phone)
  const isCodeValid = /^\d{4,6}$/.test(code)

  const handleSendCode = () => {
    if (!isPhoneValid) {
      Alert.alert('提示', '请输入正确的手机号码')
      return
    }
    if (!agreedToTerms) {
      Alert.alert('提示', '请先同意隐私协议和服务条款')
      return
    }

    // @mock-data FALLBACK - 模拟发送验证码
    setCountdown(60)
    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    codeInputRef.current?.focus()
    Alert.alert('验证码已发送', '测试验证码：1234')
  }

  const handleLogin = async () => {
    if (!isPhoneValid || !isCodeValid) return
    if (!agreedToTerms) {
      Alert.alert('提示', '请先同意隐私协议和服务条款')
      return
    }

    setLoading(true)

    try {
      // @mock-data FALLBACK - 模拟登录
      await new Promise((resolve) => setTimeout(resolve, 800))

      const mockUser: User = {
        id: 'user_001',
        name: '张三',
        email: 'zhangsan@example.com',
        role: 'client',
        avatar_url: undefined,
      }
      const mockToken = 'mock_token_' + Date.now()

      // 保存到 store 和 AsyncStorage
      setAuth(mockUser, mockToken)
      await AsyncStorage.setItem('token', mockToken)

      router.replace('/(tabs)/')
    } catch {
      Alert.alert('登录失败', '网络异常，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* 返回按钮 */}
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="close" size={28} color={Colors.text} />
          </TouchableOpacity>

          {/* Logo 区域 */}
          <View style={styles.logoSection}>
            <Text style={styles.logoText}>安心法务</Text>
            <Text style={styles.slogan}>专业 AI 法律服务，让法律触手可及</Text>
          </View>

          {/* 登录表单 */}
          <View style={styles.form}>
            {/* 手机号 */}
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>手机号</Text>
              <View style={styles.phoneRow}>
                <View style={styles.prefixBox}>
                  <Text style={styles.prefixText}>+86</Text>
                </View>
                <TextInput
                  style={styles.phoneInput}
                  placeholder="请输入手机号"
                  placeholderTextColor={Colors.textMuted}
                  value={phone}
                  onChangeText={setPhone}
                  keyboardType="phone-pad"
                  maxLength={11}
                />
              </View>
            </View>

            {/* 验证码 */}
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>验证码</Text>
              <View style={styles.codeRow}>
                <TextInput
                  ref={codeInputRef}
                  style={styles.codeInput}
                  placeholder="请输入验证码"
                  placeholderTextColor={Colors.textMuted}
                  value={code}
                  onChangeText={setCode}
                  keyboardType="number-pad"
                  maxLength={6}
                />
                <TouchableOpacity
                  style={[styles.codeButton, countdown > 0 && styles.codeButtonDisabled]}
                  onPress={handleSendCode}
                  disabled={countdown > 0}
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.codeButtonText,
                      countdown > 0 && styles.codeButtonTextDisabled,
                    ]}
                  >
                    {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* 登录按钮 */}
            <TouchableOpacity
              style={[
                styles.loginButton,
                (!isPhoneValid || !isCodeValid || loading) && styles.loginButtonDisabled,
              ]}
              onPress={handleLogin}
              disabled={!isPhoneValid || !isCodeValid || loading}
              activeOpacity={0.8}
            >
              <Text style={styles.loginButtonText}>
                {loading ? '登录中...' : '登录'}
              </Text>
            </TouchableOpacity>

            {/* 第三方登录 */}
            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>其他登录方式</Text>
              <View style={styles.dividerLine} />
            </View>

            <TouchableOpacity style={styles.wechatButton} activeOpacity={0.8}>
              <Ionicons name="logo-wechat" size={22} color={Colors.white} />
              <Text style={styles.wechatButtonText}>微信登录</Text>
            </TouchableOpacity>
          </View>

          {/* 隐私协议 */}
          <View style={styles.terms}>
            <TouchableOpacity
              style={styles.checkbox}
              onPress={() => setAgreedToTerms(!agreedToTerms)}
            >
              <Ionicons
                name={agreedToTerms ? 'checkbox' : 'square-outline'}
                size={20}
                color={agreedToTerms ? Colors.primary : Colors.textMuted}
              />
            </TouchableOpacity>
            <Text style={styles.termsText}>
              我已阅读并同意{' '}
              <Text style={styles.termsLink}>《用户服务协议》</Text>
              {' '}和{' '}
              <Text style={styles.termsLink}>《隐私政策》</Text>
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  flex: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: Layout.spacing.lg,
    paddingBottom: Layout.spacing.xl,
  },
  backButton: {
    marginTop: Layout.spacing.md,
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoSection: {
    alignItems: 'center',
    marginTop: Layout.spacing.xl,
    marginBottom: Layout.spacing.xl + Layout.spacing.md,
  },
  logoText: {
    fontSize: 36,
    fontWeight: '800',
    color: Colors.primary,
    letterSpacing: 2,
  },
  slogan: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginTop: Layout.spacing.sm,
  },
  form: {
    gap: Layout.spacing.lg,
  },
  inputGroup: {
    gap: Layout.spacing.sm,
  },
  inputLabel: {
    fontSize: Layout.fontSize.sm,
    fontWeight: '500',
    color: Colors.text,
  },
  phoneRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  prefixBox: {
    backgroundColor: Colors.surface,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    borderRadius: Layout.borderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  prefixText: {
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    fontWeight: '500',
  },
  phoneInput: {
    flex: 1,
    backgroundColor: Colors.surface,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    borderRadius: Layout.borderRadius.md,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  codeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  codeInput: {
    flex: 1,
    backgroundColor: Colors.surface,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    borderRadius: Layout.borderRadius.md,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  codeButton: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    borderRadius: Layout.borderRadius.md,
    backgroundColor: Colors.primary + '15',
  },
  codeButtonDisabled: {
    backgroundColor: Colors.surface,
  },
  codeButtonText: {
    fontSize: Layout.fontSize.sm,
    color: Colors.primary,
    fontWeight: '600',
  },
  codeButtonTextDisabled: {
    color: Colors.textMuted,
  },
  loginButton: {
    backgroundColor: Colors.primary,
    paddingVertical: Layout.spacing.md + 2,
    borderRadius: Layout.borderRadius.md,
    alignItems: 'center',
    marginTop: Layout.spacing.sm,
  },
  loginButtonDisabled: {
    opacity: 0.5,
  },
  loginButtonText: {
    fontSize: Layout.fontSize.lg,
    fontWeight: '600',
    color: Colors.white,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: Layout.spacing.sm,
  },
  dividerLine: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
    backgroundColor: Colors.border,
  },
  dividerText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.textMuted,
    marginHorizontal: Layout.spacing.md,
  },
  wechatButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#07C160',
    paddingVertical: Layout.spacing.md,
    borderRadius: Layout.borderRadius.md,
    gap: Layout.spacing.sm,
  },
  wechatButtonText: {
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
    color: Colors.white,
  },
  terms: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginTop: Layout.spacing.xl,
    paddingHorizontal: Layout.spacing.xs,
  },
  checkbox: {
    marginRight: Layout.spacing.sm,
    marginTop: 1,
  },
  termsText: {
    flex: 1,
    fontSize: Layout.fontSize.xs,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
  termsLink: {
    color: Colors.primary,
  },
})
