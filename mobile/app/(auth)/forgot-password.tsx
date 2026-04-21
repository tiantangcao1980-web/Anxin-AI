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
 * 忘记密码 —— 对接 `POST /auth/forgot-password`，发送重置链接到邮箱。
 *
 * 链接带一次性 token，点击后进入 `/(auth)/reset-password?token=xxx` 完成重置。
 * 后端带频率限制，过于频繁会返回 429。
 */

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  const onSubmit = async () => {
    if (!isValid) return
    setLoading(true)
    try {
      await api.post('/auth/forgot-password', { email })
      setSent(true)
    } catch (err: any) {
      Alert.alert('发送失败', err?.message || '请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.successBox}>
          <View style={styles.successIconBox}>
            <Ionicons name="mail-unread" size={48} color={Colors.primary} />
          </View>
          <Text style={styles.successTitle}>邮件已发送</Text>
          <Text style={styles.successDesc}>
            我们已向 {email} 发送密码重置链接，请查收邮件并点击链接完成重置。
          </Text>
          <TouchableOpacity
            style={styles.primaryBtn}
            onPress={() => router.replace('/(auth)/login')}
          >
            <Text style={styles.primaryBtnText}>返回登录</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setSent(false)}>
            <Text style={styles.link}>换个邮箱地址重新发送</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <TouchableOpacity style={styles.back} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color={Colors.text} />
          </TouchableOpacity>

          <Text style={styles.title}>找回密码</Text>
          <Text style={styles.subtitle}>输入您的注册邮箱，我们将发送重置链接</Text>

          <View style={styles.field}>
            <Text style={styles.label}>邮箱</Text>
            <TextInput
              style={styles.input}
              placeholder="请输入您的注册邮箱"
              placeholderTextColor={Colors.textMuted}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <TouchableOpacity
            style={[styles.primaryBtn, !isValid && styles.primaryBtnDisabled]}
            disabled={!isValid || loading}
            onPress={onSubmit}
          >
            <Text style={styles.primaryBtnText}>
              {loading ? '发送中...' : '发送重置链接'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={() => router.replace('/(auth)/login')}
          >
            <Text style={styles.secondaryBtnText}>返回登录</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
  content: { padding: Layout.spacing.lg },
  back: { width: 40, height: 40, justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: '700', color: Colors.text, marginTop: Layout.spacing.md },
  subtitle: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginTop: 4,
    marginBottom: Layout.spacing.xl,
  },
  field: { marginBottom: Layout.spacing.lg },
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
  primaryBtn: {
    backgroundColor: Colors.primary,
    paddingVertical: Layout.spacing.md + 2,
    borderRadius: Layout.borderRadius.md,
    alignItems: 'center',
    marginTop: Layout.spacing.md,
  },
  primaryBtnDisabled: { opacity: 0.5 },
  primaryBtnText: { fontSize: Layout.fontSize.lg, fontWeight: '600', color: Colors.white },
  secondaryBtn: {
    alignItems: 'center',
    paddingVertical: Layout.spacing.md,
    marginTop: Layout.spacing.sm,
  },
  secondaryBtnText: { fontSize: Layout.fontSize.md, color: Colors.primary, fontWeight: '500' },
  successBox: {
    flex: 1,
    alignItems: 'center',
    padding: Layout.spacing.xl,
    justifyContent: 'center',
    gap: Layout.spacing.md,
  },
  successIconBox: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Layout.spacing.md,
  },
  successTitle: { fontSize: 22, fontWeight: '700', color: Colors.text },
  successDesc: {
    fontSize: Layout.fontSize.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
  },
  link: {
    fontSize: Layout.fontSize.sm,
    color: Colors.primary,
    fontWeight: '500',
    marginTop: Layout.spacing.md,
  },
})
