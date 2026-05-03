import { useEffect, useState, useCallback } from 'react'
import { View, Text, ScrollView, Switch, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  skillsApi, Skill, SkillCategory,
  DOMAIN_LABELS, DOMAIN_ORDER,
} from '../_mock'
import './index.scss'

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [collapsed, setCollapsed] = useState<Record<SkillCategory, boolean>>(() => {
    const init = {} as Record<SkillCategory, boolean>
    DOMAIN_ORDER.forEach((d, idx) => { init[d] = idx > 2 }) // 默认前 3 域展开
    return init
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await skillsApi.list()
      setSkills(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const onToggle = async (skill: Skill, on: boolean) => {
    try {
      const updated = await skillsApi.toggle(skill.name, on)
      setSkills((arr) => arr.map((s) => (s.name === skill.name ? updated : s)))
    } catch {
      Taro.showToast({ title: '操作失败', icon: 'none' })
    }
  }

  const onUpload = () => {
    Taro.showModal({
      title: '上传 SKILL.md',
      content: '小程序暂不支持上传文件，请前往 Web 端管理后台上传。',
      showCancel: false,
    })
  }

  const grouped: Record<SkillCategory, Skill[]> = {} as any
  DOMAIN_ORDER.forEach((d) => { grouped[d] = [] })
  skills.forEach((s) => {
    if (!grouped[s.category]) grouped[s.category] = []
    grouped[s.category].push(s)
  })

  const enabledCount = skills.filter((s) => s.enabled).length

  return (
    <View className='sk-page'>
      <View className='sk-header'>
        <Text className='sk-summary'>
          已启用 <Text className='sk-summary-num'>{enabledCount}</Text> / {skills.length} 技能
        </Text>
        <Button className='sk-upload-btn' onClick={onUpload}>
          + 上传
        </Button>
      </View>

      <ScrollView scrollY className='sk-scroll'>
        {loading ? (
          <View className='sk-empty'><Text>加载中…</Text></View>
        ) : (
          DOMAIN_ORDER.map((domain) => {
            const list = grouped[domain]
            if (!list || list.length === 0) return null
            const isCollapsed = collapsed[domain]
            const enabledInGroup = list.filter((s) => s.enabled).length
            return (
              <View key={domain} className='sk-group'>
                <View
                  className='sk-group-header'
                  onClick={() => setCollapsed((c) => ({ ...c, [domain]: !c[domain] }))}
                >
                  <Text className='sk-group-title'>
                    {DOMAIN_LABELS[domain]}
                  </Text>
                  <Text className='sk-group-count'>
                    {enabledInGroup} / {list.length}
                  </Text>
                  <Text className='sk-group-arrow'>{isCollapsed ? '▸' : '▾'}</Text>
                </View>
                {!isCollapsed && (
                  <View className='sk-group-body'>
                    {list.map((skill) => (
                      <View key={skill.name} className='sk-item'>
                        <View className='sk-item-body'>
                          <Text className='sk-item-title'>{skill.display_name}</Text>
                          <Text className='sk-item-desc'>{skill.description}</Text>
                          {skill.requires_apps.length > 0 && (
                            <Text className='sk-item-deps'>
                              依赖：{skill.requires_apps.join(' / ')}
                            </Text>
                          )}
                        </View>
                        <Switch
                          className='sk-switch'
                          checked={skill.enabled}
                          color='#D4A574'
                          onChange={(e) => onToggle(skill, e.detail.value)}
                        />
                      </View>
                    ))}
                  </View>
                )}
              </View>
            )
          })
        )}
      </ScrollView>
    </View>
  )
}
