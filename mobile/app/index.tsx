import { Redirect } from 'expo-router'
import { ActivityIndicator, View } from 'react-native'
import { Colors } from '@/constants/colors'
import { useAuthStore } from '@/lib/store'

export default function EntryScreen() {
  const { hydrated, isAuthenticated } = useAuthStore()

  if (!hydrated) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.background }}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    )
  }

  return <Redirect href={isAuthenticated ? '/(tabs)' : '/(auth)/login'} />
}
