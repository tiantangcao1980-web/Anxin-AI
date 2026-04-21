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
import { api } from '@/services/api'

/**
 * 注册页 —— 对接后端 `POST /auth/register`，成功后回到登录页。
 *
 * 后端会发送邮箱验证码，本页注册成功后提示用户查收邮件。
 * 真正登录仍走 /login（验证码校验在独立页面 verify-email）。
 */

type UserType = 'individual' | 'enterprise' | 'platform_lawyer'

const USER_TYPES: { key: UserType; label: string; desc: string }[] = [
  { key: 'individual', label: '个人用户', desc: '个人法律咨询与服务' },
  { key: 'enterprise', label: '企业用户', desc: '企业法务管理与合规' },
  { key: 'platform_lawyer', label: '入驻律师', desc: '执业律师入驻接单' },
]

export default function RegisterScreen() {
  const [userType, setUserType] = useState<UserType>('individual')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)

  const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  const isPasswordValid = password.length >= 8
  const isPasswordMatched = password === confirmPassword
  const isNameValid = name.trim().length >= 2

  const canSubmit =
    isEmailValid && isPasswordValid && isPasswordMatched && isNameValid && agreed

  const onSubmit = async () => {
    if (!canSubmit) return
    setLoading(true)
    try {
      await api.post('/auth/register', {
        email,
        password,
        name: name.trim(),
        user_type: userType,
      })
      Alert.alert(
        '注册成功',
        '我们已向您的邮箱发送验证邮件，验证后即可登录。',
        [{ text: '返回登录', onPress: () => router.replace('/(auth)/login') }],
      )
    } catch (err: any) {
      Alert.alert('注册失败', err?.message || '请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <TouchableOpacity style={styles.back} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color={Colors.text} />
          </TouchableOpacity>

          <Text style={styles.title}>创建账号</Text>
          <Text style={styles.subtitle}>选择适合你的账号类型</Text>

          {/* 账号类型 */}
          <View style={styles.userTypeRow}>
            {USER_TYPES.map((t) => (
              <TouchableOpacity
                key={t.key}
                style={[styles.userType, userType === t.key && styles.userTypeActive]}
                onPress={() => setUserType(t.key)}
              >
                <Text
                  style={[
                    styles.userTypeLabel,
                    userType === t.key && styles.userTypeLabelActive,
                  ]}
                >
                  {t.label}
                </Text>
                <Text
                  style={[
                    styles.userTypeDesc,
                    userType === t.key && styles.userTypeDescActive,
                  ]}
                >
                  {t.desc}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* 姓名 */}
          <Field label="姓名 / 称呼">
            <TextInput
              style={styles.input}
              placeholder="请输入您的姓名"
              placeholderTextColor={Colors.textMuted}
              value={name}
              onChangeText={setName}
              autoCorrect={false}
            />
          </Field>

          {/* 邮箱 */}
          <Field label="邮箱">
            <TextInput
              style={styles.input}
              placeholder="用于登录与找回密码"
              placeholderTextColor={Colors.textMuted}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </Field>

          {/* 密码 */}
          <Field label="密码">
            <View style={styles.inputRow}>
              <TextInput
                style={[styles.input, { flex: 1 }]}
                placeholder="至少 8 位，建议字母 + 数字"
                placeholderTextColor={Colors.textMuted}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
              />
              <TouchableOpacity
                style={styles.eyeBtn}
                onPress={() => setShowPassword((s) => !s)}
              >
                <Ionicons
                  name={showPassword ? 'eye-off' : 'eye'}
                  size={20}
                  color={Colors.textMuted}
                />
              </TouchableOpacity>
            </View>
          </Field>

          {/* 确认密码 */}
          <Field label="确认密码">
            <TextInput
              style={styles.input}
              placeholder="再次输入密码"
              placeholderTextColor={Colors.textMuted}
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
            />
            {confirmPassword.length > 0 && !isPasswordMatched && (
              <Text style={styles.hintError}>两次密码不一致</Text>
            )}
          </Field>

          <TouchableOpacity
            style={[styles.submitBtn, !canSubmit && styles.submitBtnDisabled]}
            disabled={!canSubmit || loading}
            onPress={onSubmit}
          >
            <Text style={styles.submitBtnText}>
              {loading ? '注册中...' : '注册'}
            </Text>
          </TouchableOpacity>

          <View style={styles.terms}>
            <TouchableOpacity onPress={() => setAgreed(!agreed)}>
              <Ionicons
                name={agreed ? 'checkbox' : 'square-outline'}
                size={20}
                color={agreed ? Colors.primary : Colors.textMuted}
              />
            </TouchableOpacity>
            <Text style={styles.termsText}>
              我已阅读并同意{' '}
              <Text style={styles.link}>《用户服务协议》</Text>
              {' '}和{' '}
              <Text style={styles.link}>《隐私政策》</Text>
            </Text>
          </View>

          <View style={styles.loginBack}>
            <Text style={styles.loginBackText}>已有账号？</Text>
            <TouchableOpacity onPress={() => router.replace('/(auth)/login')}>
              <Text style={styles.link}>立即登录</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
  content: { padding: Layout.spacing.lg, paddingBottom: Layout.spacing.xl },
  back: { width: 40, height: 40, justifyContent: 'center' },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: Colors.text,
    marginTop: Layout.spacing.md,
  },
  subtitle: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginTop: 4,
    marginBottom: Layout.spacing.lg,
  },
  userTypeRow: { gap: Layout.spacing.sm, marginBottom: Layout.spacing.lg },
  userType: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
  },
  userTypeActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primary + '10',
  },
  userTypeLabel: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  userTypeLabelActive: { color: Colors.primary },
  userTypeDesc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  userTypeDescActive: { color: Colors.primary },
  field: { marginBottom: Layout.spacing.md },
  label: {
    fontSize: Layout.fontSize.sm,
    fontWeight: '500',
    color: Colors.text,
    marginBottom: 6,
  },
  input: {
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Layout.borderRadius.md,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
  },
  inputRow: { flexDirection: 'row', alignItems: 'center' },
  eyeBtn: { position: 'absolute', right: 12, padding: 8 },
  hintError: {
    fontSize: Layout.fontSize.xs,
    color: '#DC2626',
    marginTop: 4,
  },
  submitBtn: {
    backgroundColor: Colors.primary,
    paddingVertical: Layout.spacing.md + 2,
    borderRadius: Layout.borderRadius.md,
    alignItems: 'center',
    marginTop: Layout.spacing.md,
  },
  submitBtnDisabled: { opacity: 0.5 },
  submitBtnText: { fontSize: Layout.fontSize.lg, fontWeight: '600', color: Colors.white },
  terms: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginTop: Layout.spacing.lg,
    gap: Layout.spacing.sm,
  },
  termsText: {
    flex: 1,
    fontSize: Layout.fontSize.xs,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
  link: { color: Colors.primary, fontWeight: '500' },
  loginBack: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 4,
    marginTop: Layout.spacing.xl,
  },
  loginBackText: { fontSize: Layout.fontSize.sm, color: Colors.textSecondary },
})
