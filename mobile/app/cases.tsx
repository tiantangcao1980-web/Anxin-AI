import { useState } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

// @mock-data FALLBACK
interface Case {
  id: string
  name: string
  caseNumber: string
  lawyer: string
  status: '进行中' | '待处理' | '已结案'
  updatedAt: string
}

const STATUS_COLORS: Record<Case['status'], string> = {
  '进行中': '#2196F3',
  '待处理': '#FF9800',
  '已结案': '#9E9E9E',
}

const FILTER_TABS = ['全部', '进行中', '待处理', '已结案'] as const

// @mock-data FALLBACK
const MOCK_CASES: Case[] = [
  {
    id: '1',
    name: '张三 vs 李四 合同纠纷案',
    caseNumber: '（2026）沪民初字第1234号',
    lawyer: '王律师',
    status: '进行中',
    updatedAt: '2026-03-27 14:30',
  },
  {
    id: '2',
    name: '安心科技劳动争议案',
    caseNumber: '（2026）京劳仲字第5678号',
    lawyer: '陈律师',
    status: '待处理',
    updatedAt: '2026-03-25 09:15',
  },
  {
    id: '3',
    name: '知识产权侵权纠纷',
    caseNumber: '（2026）粤知民初字第0912号',
    lawyer: '林律师',
    status: '进行中',
    updatedAt: '2026-03-22 16:45',
  },
  {
    id: '4',
    name: '房屋买卖合同纠纷',
    caseNumber: '（2025）浙民终字第3456号',
    lawyer: '赵律师',
    status: '已结案',
    updatedAt: '2026-02-15 11:00',
  },
]

export default function CasesScreen() {
  const [activeTab, setActiveTab] = useState<string>('全部')

  const filteredCases = MOCK_CASES.filter((item) => {
    return activeTab === '全部' || item.status === activeTab
  })

  const renderCase = ({ item }: { item: Case }) => (
    <TouchableOpacity style={styles.card} activeOpacity={0.7}>
      <View style={styles.cardBody}>
        <View style={styles.cardMain}>
          <Text style={styles.caseName} numberOfLines={2}>
            {item.name}
          </Text>
          <View style={styles.caseNumberRow}>
            <Ionicons name="document-outline" size={13} color="#999" />
            <Text style={styles.caseNumber}>{item.caseNumber}</Text>
          </View>
          <View style={styles.lawyerRow}>
            <Ionicons name="person-outline" size={13} color="#999" />
            <Text style={styles.lawyerText}>负责律师：{item.lawyer}</Text>
          </View>
          <View style={styles.cardFooter}>
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: STATUS_COLORS[item.status] + '20' },
              ]}
            >
              <View
                style={[styles.statusDot, { backgroundColor: STATUS_COLORS[item.status] }]}
              />
              <Text style={[styles.statusText, { color: STATUS_COLORS[item.status] }]}>
                {item.status}
              </Text>
            </View>
            <Text style={styles.dateText}>更新于 {item.updatedAt}</Text>
          </View>
        </View>
        <View style={styles.arrowContainer}>
          <Ionicons name="chevron-forward" size={20} color="#CCC" />
        </View>
      </View>
    </TouchableOpacity>
  )

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="briefcase-outline" size={64} color="#CCC" />
      <Text style={styles.emptyText}>暂无案件</Text>
      <Text style={styles.emptySubText}>您的案件将显示在这里</Text>
    </View>
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen
        options={{
          title: '我的案件',
          headerStyle: { backgroundColor: '#FFF' },
          headerTintColor: '#333',
        }}
      />

      {/* 状态筛选 Tab */}
      <View style={styles.tabContainer}>
        {FILTER_TABS.map((tab) => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
              {tab}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* 案件列表 */}
      <FlatList
        data={filteredCases}
        keyExtractor={(item) => item.id}
        renderItem={renderCase}
        ListEmptyComponent={renderEmpty}
        contentContainerStyle={filteredCases.length === 0 ? styles.emptyList : styles.listContent}
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginTop: 12,
    marginBottom: 8,
  },
  tab: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#FFF',
    marginRight: 8,
  },
  tabActive: {
    backgroundColor: '#D4A574',
  },
  tabText: {
    fontSize: 13,
    color: '#666',
  },
  tabTextActive: {
    color: '#FFF',
    fontWeight: '600',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
  },
  cardBody: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardMain: {
    flex: 1,
  },
  caseName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6,
  },
  caseNumberRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  caseNumber: {
    fontSize: 12,
    color: '#999',
    marginLeft: 4,
  },
  lawyerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  lawyerText: {
    fontSize: 13,
    color: '#666',
    marginLeft: 4,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '500',
  },
  dateText: {
    fontSize: 11,
    color: '#BBB',
  },
  arrowContainer: {
    marginLeft: 8,
  },
  emptyList: {
    flex: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 80,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 16,
  },
  emptySubText: {
    fontSize: 13,
    color: '#CCC',
    marginTop: 4,
  },
})
