import React from 'react'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useColorScheme } from 'react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { Colors, DarkColors } from '../src/constants/colors'
import { PrivacyProvider } from '../src/lib/privacy-context'

export default function RootLayout() {
  const colorScheme = useColorScheme()
  const theme = colorScheme === 'dark' ? DarkColors : Colors

  return (
    <SafeAreaProvider>
      <PrivacyProvider>
        <StatusBar style={colorScheme === 'dark' ? 'light' : 'dark'} />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: theme.background },
            headerTintColor: theme.text,
            headerTitleStyle: { fontWeight: '600' },
            contentStyle: { backgroundColor: theme.background },
            headerShadowVisible: false,
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="(auth)" options={{ headerShown: false }} />
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        </Stack>
      </PrivacyProvider>
    </SafeAreaProvider>
  )
}
