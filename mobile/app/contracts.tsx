import { useState } from 'react'
import { View, Text, FlatList, TouchableOpacity, TextInput, StyleSheet } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

// @mock-data FALLBACK
interface Contract {
  id: string
  title: string
  type: string
  partyA: string
  partyB: string
  status: '审核中' | '已签署' | '已归档'
  createdAt: string
}

const STATUS_COLORS: Record<Contract['status'], string> = {
  '审核中': '#E8A317',
  '已签署': '#4CAF50',
  '已归档': '#9E9E9E',
}

const FILTER_TABS = ['全部', '审核中', '已签署', '已归档'] as const

// @mock-data FALLBACK
const MOCK_CONTRACTS: Contract[] = [
  {
    id: '1',
    title: '房屋租赁合同',
    type: '租赁合同',
    partyA: '张三',
    partyB: '李四',
    status: '已签署',
    createdAt: '2026-03-15',
  },
  {
    id: '2',
    title: '技术开发服务合同',
    type: '服务合同',
    partyA: '安心科技有限公司',
    partyB: '创新软件公司',
    status: '审核中',
    createdAt: '2026-03-20',
  },
  {
    id: '3',
    title: '劳动合同',
    type: '劳动合同',
    partyA: '安心科技有限公司',
    partyB: '王五',
    status: '已签署',
    createdAt: '2026-02-10',
  },
  {
    id: '4',
    title: '股权转让协议',
    type: '股权协议',
    partyA: '赵六',
    partyB: '钱七',
    status: '已归档',
    createdAt: '2026-01-05',
  },
  {
    id: '5',
    title: '保密协议（NDA）',
    type: '保密协议',
    partyA: '安心科技有限公司',
    partyB: '合作方A',
    status: '审核中',
    createdAt: '2026-03-25',
  },
]

export default function ContractsScreen() {
  const [searchText, setSearchText] = useState('')
  const [activeTab, setActiveTab] = useState<string>('全部')

  const filteredContracts = MOCK_CONTRACTS.filter((contract) => {
    const matchesSearch =
      contract.title.includes(searchText) ||
      contract.partyA.includes(searchText) ||
      contract.partyB.includes(searchText)
    const matchesStatus = activeTab === '全部' || contract.status === activeTab
    return matchesSearch && matchesStatus
  })

  const renderContract = ({ item }: { item: Contract }) => (
    <TouchableOpacity style={styles.card} activeOpacity={0.7}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <View style={styles.typeTag}>
          <Text style={styles.typeTagText}>{item.type}</Text>
        </View>
      </View>
      <View style={styles.cardRow}>
        <Ionicons name="people-outline" size={14} color="#999" />
        <Text style={styles.cardLabel}>
          {item.partyA} — {item.partyB}
        </Text>
      </View>
      <View style={styles.cardFooter}>
        <View style={[styles.statusBadge, { backgroundColor: STATUS_COLORS[item.status] + '20' }]}>
          <View style={[styles.statusDot, { backgroundColor: STATUS_COLORS[item.status] }]} />
          <Text style={[styles.statusText, { color: STATUS_COLORS[item.status] }]}>
            {item.status}
          </Text>
        </View>
        <Text style={styles.dateText}>{item.createdAt}</Text>
      </View>
    </TouchableOpacity>
  )

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="document-text-outline" size={64} color="#CCC" />
      <Text style={styles.emptyText}>暂无合同</Text>
      <Text style={styles.emptySubText}>您的合同将显示在这里</Text>
    </View>
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen
        options={{
          title: '我的合同',
          headerStyle: { backgroundColor: '#FFF' },
          headerTintColor: '#333',
        }}
      />

      {/* 搜索框 */}
      <View style={styles.searchContainer}>
        <Ionicons name="search-outline" size={18} color="#999" />
        <TextInput
          style={styles.searchInput}
          placeholder="搜索合同名称、签约方..."
          placeholderTextColor="#BBB"
          value={searchText}
          onChangeText={setSearchText}
        />
        {searchText.length > 0 && (
          <TouchableOpacity onPress={() => setSearchText('')}>
            <Ionicons name="close-circle" size={18} color="#999" />
          </TouchableOpacity>
        )}
      </View>

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

      {/* 合同列表 */}
      <FlatList
        data={filteredContracts}
        keyExtractor={(item) => item.id}
        renderItem={renderContract}
        ListEmptyComponent={renderEmpty}
        contentContainerStyle={filteredContracts.length === 0 ? styles.emptyList : styles.listContent}
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    height: 42,
  },
  searchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 15,
    color: '#333',
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
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
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  typeTag: {
    backgroundColor: '#D4A57420',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: 8,
  },
  typeTagText: {
    fontSize: 11,
    color: '#D4A574',
    fontWeight: '500',
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardLabel: {
    fontSize: 13,
    color: '#666',
    marginLeft: 6,
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
    fontSize: 12,
    color: '#999',
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
