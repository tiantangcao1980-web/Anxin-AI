import React from 'react'
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native'
import { Colors } from '../constants/colors'
import { Layout } from '../constants/layout'

interface LoadingScreenProps {
  message?: string
}

export function LoadingScreen({ message = '加载中...' }: LoadingScreenProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={Colors.primary} />
      <Text style={styles.text}>{message}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.background,
    gap: Layout.spacing.md,
  },
  text: {
    fontSize: Layout.fontSize.md,
    color: Colors.textSecondary,
  },
})
