import { useState } from 'react'
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
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { createAuthClient } from '@/lib/auth-client'
import { getAuthStorage } from '@/lib/auth-storage'
import { useAuthStore } from '@/lib/store'
import { authApi } from '@/services/api'

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const { setAuth } = useAuthStore()
  const authClient = createAuthClient({
    api: authApi,
    storage: getAuthStorage(),
  })

  const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  const isPasswordValid = password.length >= 8

  const handleLogin = async () => {
    if (!isEmailValid || !isPasswordValid) {
      Alert.alert('提示', '请输入有效邮箱和至少 8 位密码')
      return
    }
    if (!agreedToTerms) {
      Alert.alert('提示', '请先同意隐私协议和服务条款')
      return
    }

    setLoading(true)

    try {
      const result = await authClient.login({ email, password })
      setAuth(result.user, result.access_token)
      router.replace('/(tabs)/')
    } catch (error: any) {
      Alert.alert('登录失败', error?.message || '邮箱或密码错误，请稍后重试')
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
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>邮箱</Text>
              <View style={styles.phoneRow}>
                <TextInput
                  style={styles.phoneInput}
                  placeholder="请输入邮箱地址"
                  placeholderTextColor={Colors.textMuted}
                  value={email}
                  onChangeText={setEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>密码</Text>
              <View style={styles.codeRow}>
                <TextInput
                  style={styles.codeInput}
                  placeholder="请输入密码"
                  placeholderTextColor={Colors.textMuted}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                />
                <TouchableOpacity
                  style={styles.codeButton}
                  onPress={() => setShowPassword((value) => !value)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.codeButtonText}>{showPassword ? '隐藏' : '显示'}</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* 登录按钮 */}
            <TouchableOpacity
              style={[
                styles.loginButton,
                (!isEmailValid || !isPasswordValid || loading) && styles.loginButtonDisabled,
              ]}
              onPress={handleLogin}
              disabled={!isEmailValid || !isPasswordValid || loading}
              activeOpacity={0.8}
            >
              <Text style={styles.loginButtonText}>
                {loading ? '登录中...' : '登录'}
              </Text>
            </TouchableOpacity>

            {/* 第三方登录 */}
            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>更多登录方式即将开放</Text>
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
