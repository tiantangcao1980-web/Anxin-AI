import { useState } from 'react'
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  ScrollView,
  StyleSheet,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

// @mock-data FALLBACK
interface Lawyer {
  id: string
  name: string
  initials: string
  yearsOfPractice: number
  specialties: string[]
  rating: number
  rateRange: string
}

// @mock-data FALLBACK
const MOCK_LAWYERS: Lawyer[] = [
  {
    id: '1',
    name: '王建国',
    initials: '王',
    yearsOfPractice: 15,
    specialties: ['合同纠纷', '公司法', '知识产权'],
    rating: 4.9,
    rateRange: '¥500 - ¥800/小时',
  },
  {
    id: '2',
    name: '陈美玲',
    initials: '陈',
    yearsOfPractice: 10,
    specialties: ['劳动法', '婚姻家庭', '民事诉讼'],
    rating: 4.8,
    rateRange: '¥400 - ¥600/小时',
  },
  {
    id: '3',
    name: '林志远',
    initials: '林',
    yearsOfPractice: 20,
    specialties: ['刑事辩护', '行政诉讼', '合规顾问'],
    rating: 4.7,
    rateRange: '¥600 - ¥1000/小时',
  },
  {
    id: '4',
    name: '赵晓婷',
    initials: '赵',
    yearsOfPractice: 8,
    specialties: ['房产纠纷', '建设工程', '合同法'],
    rating: 4.6,
    rateRange: '¥350 - ¥500/小时',
  },
  {
    id: '5',
    name: '刘鹏飞',
    initials: '刘',
    yearsOfPractice: 12,
    specialties: ['国际贸易', '海商法', '仲裁'],
    rating: 4.8,
    rateRange: '¥500 - ¥900/小时',
  },
]

function StarRating({ rating }: { rating: number }) {
  const fullStars = Math.floor(rating)
  const hasHalf = rating - fullStars >= 0.5

  return (
    <View style={styles.starRow}>
      {Array.from({ length: 5 }, (_, i) => {
        if (i < fullStars) {
          return <Ionicons key={i} name="star" size={14} color="#F5A623" />
        }
        if (i === fullStars && hasHalf) {
          return <Ionicons key={i} name="star-half" size={14} color="#F5A623" />
        }
        return <Ionicons key={i} name="star-outline" size={14} color="#F5A623" />
      })}
      <Text style={styles.ratingValue}>{rating.toFixed(1)}</Text>
    </View>
  )
}

export default function FindLawyerScreen() {
  const [description, setDescription] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  const handleMatch = () => {
    setHasSearched(true)
  }

  const renderLawyer = ({ item }: { item: Lawyer }) => (
    <View style={styles.lawyerCard}>
      <View style={styles.lawyerTop}>
        {/* 头像 */}
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{item.initials}</Text>
        </View>
        <View style={styles.lawyerInfo}>
          <View style={styles.nameRow}>
            <Text style={styles.lawyerName}>{item.name}</Text>
            <Text style={styles.yearsText}>执业 {item.yearsOfPractice} 年</Text>
          </View>
          <StarRating rating={item.rating} />
        </View>
      </View>

      {/* 专业领域标签 */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.specialtiesRow}
        contentContainerStyle={styles.specialtiesContent}
      >
        {item.specialties.map((s) => (
          <View key={s} style={styles.specialtyTag}>
            <Text style={styles.specialtyText}>{s}</Text>
          </View>
        ))}
      </ScrollView>

      {/* 底部：费率 + 咨询按钮 */}
      <View style={styles.lawyerFooter}>
        <Text style={styles.rateText}>{item.rateRange}</Text>
        <TouchableOpacity style={styles.consultButton} activeOpacity={0.7}>
          <Ionicons name="chatbubble-ellipses-outline" size={14} color="#FFF" />
          <Text style={styles.consultButtonText}>咨询</Text>
        </TouchableOpacity>
      </View>
    </View>
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen
        options={{
          title: '找律师',
          headerStyle: { backgroundColor: '#FFF' },
          headerTintColor: '#333',
        }}
      />

      {/* 需求描述输入 */}
      <View style={styles.inputSection}>
        <Text style={styles.inputLabel}>描述您的法律需求</Text>
        <TextInput
          style={styles.descriptionInput}
          placeholder="请简要描述您遇到的法律问题，例如：公司合同纠纷、劳动仲裁等..."
          placeholderTextColor="#BBB"
          multiline
          numberOfLines={4}
          textAlignVertical="top"
          value={description}
          onChangeText={setDescription}
        />
        <TouchableOpacity
          style={[styles.matchButton, !description && styles.matchButtonDisabled]}
          activeOpacity={0.7}
          onPress={handleMatch}
          disabled={!description}
        >
          <Ionicons name="sparkles-outline" size={18} color="#FFF" />
          <Text style={styles.matchButtonText}>智能匹配</Text>
        </TouchableOpacity>
      </View>

      {/* 推荐律师列表 */}
      {hasSearched && (
        <FlatList
          data={MOCK_LAWYERS}
          keyExtractor={(item) => item.id}
          renderItem={renderLawyer}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListHeaderComponent={
            <Text style={styles.resultTitle}>
              为您推荐 {MOCK_LAWYERS.length} 位律师
            </Text>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  inputSection: {
    backgroundColor: '#FFF',
    margin: 16,
    borderRadius: 12,
    padding: 16,
  },
  inputLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  descriptionInput: {
    backgroundColor: '#F9F9F9',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: '#333',
    height: 100,
    borderWidth: 1,
    borderColor: '#EEE',
  },
  matchButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#D4A574',
    borderRadius: 10,
    height: 44,
    marginTop: 12,
  },
  matchButtonDisabled: {
    opacity: 0.5,
  },
  matchButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 6,
  },
  resultTitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 10,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  lawyerCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
  },
  lawyerTop: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#D4A574',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '700',
  },
  lawyerInfo: {
    flex: 1,
    marginLeft: 12,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  lawyerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  yearsText: {
    fontSize: 12,
    color: '#999',
    marginLeft: 8,
  },
  starRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  ratingValue: {
    fontSize: 12,
    color: '#F5A623',
    fontWeight: '600',
    marginLeft: 4,
  },
  specialtiesRow: {
    marginTop: 12,
  },
  specialtiesContent: {
    gap: 6,
  },
  specialtyTag: {
    backgroundColor: '#D4A57415',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  specialtyText: {
    fontSize: 12,
    color: '#D4A574',
    fontWeight: '500',
  },
  lawyerFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#EEE',
  },
  rateText: {
    fontSize: 13,
    color: '#666',
  },
  consultButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#D4A574',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 18,
  },
  consultButtonText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 4,
  },
})
