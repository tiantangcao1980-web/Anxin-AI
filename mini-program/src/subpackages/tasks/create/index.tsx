// -*- coding: utf-8 -*-
/**
 * 新建任务（V3 P21-B）
 *
 * 表单：
 *   - persona picker（10 个智能体）
 *   - 标题（可选）
 *   - 任务指令（必填）
 *   - 优先级 selector（0-9）
 *   - 派远端 switch（远端沙箱执行 / 本地）
 *
 * 提交 → tasksApi.createTask → redirectTo 详情页
 */

import { useMemo, useState } from 'react'
import { View, Text, Input, Textarea, Picker, Switch } from '@tarojs/components'
import Taro from '@tarojs/taro'

import { Screen } from '../../../components/Layout'
import { tasksApi } from '../_lib/tasksApi'
import { PERSONA_OPTIONS } from '../_lib/personas'
import './index.scss'

const PRIORITY_OPTIONS = ['0 (后台)', '1', '2', '3', '4', '5 (默认)', '6', '7', '8', '9 (紧急)']

export default function CreateTask() {
  const [personaIdx, setPersonaIdx] = useState(0)
  const [title, setTitle] = useState('')
  const [userInput, setUserInput] = useState('')
  const [priorityIdx, setPriorityIdx] = useState(5)
  const [remote, setRemote] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const personaLabels = useMemo(
    () => PERSONA_OPTIONS.map((p) => `${p.emoji} ${p.name}`),
    [],
  )

  const handleSubmit = async () => {
    if (submitting) return
    if (!userInput.trim()) {
      Taro.showToast({ title: '请填写任务指令', icon: 'none' })
      return
    }
    setSubmitting(true)
    try {
      const persona = PERSONA_OPTIONS[personaIdx]
      const task = await tasksApi.createTask({
        agent_persona: persona.id,
        priority: priorityIdx,
        payload: {
          title: title.trim() || undefined,
          user_input: userInput.trim(),
          execution: remote ? 'remote_sandbox' : 'local',
        },
      })
      Taro.showToast({ title: '已创建任务', icon: 'success' })
      // 等 toast 看一下再跳
      setTimeout(() => {
        Taro.redirectTo({
          url: `/subpackages/tasks/detail/index?id=${encodeURIComponent(task.id)}`,
        })
      }, 600)
    } catch (e) {
      Taro.showToast({
        title: e instanceof Error ? e.message : '创建失败',
        icon: 'none',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Screen padded={false}>
      <View className='ct'>
        <View className='ct-section'>
          <Text className='ct-section__label'>选择智能体</Text>
          <Picker
            mode='selector'
            range={personaLabels}
            value={personaIdx}
            onChange={(e) => setPersonaIdx(Number(e.detail.value))}
          >
            <View className='ct-row'>
              <Text className='ct-row__value'>{personaLabels[personaIdx]}</Text>
              <Text className='ct-row__arrow'>›</Text>
            </View>
          </Picker>
          <Text className='ct-section__hint'>
            {PERSONA_OPTIONS[personaIdx].domain
              ? `所属业务域：${PERSONA_OPTIONS[personaIdx].domain}`
              : '系统会按指令路由到合适的智能体'}
          </Text>
        </View>

        <View className='ct-section'>
          <Text className='ct-section__label'>任务标题（可选）</Text>
          <Input
            className='ct-input'
            value={title}
            placeholder='例如：审查 NDA - 美方供应商'
            maxlength={60}
            onInput={(e) => setTitle(e.detail.value)}
          />
        </View>

        <View className='ct-section'>
          <Text className='ct-section__label'>任务指令 *</Text>
          <Textarea
            className='ct-textarea'
            value={userInput}
            placeholder='详细描述要让智能体完成的事项，越具体结果越好'
            maxlength={1000}
            autoHeight
            onInput={(e) => setUserInput(e.detail.value)}
          />
          <Text className='ct-section__hint'>{userInput.length}/1000</Text>
        </View>

        <View className='ct-section'>
          <Text className='ct-section__label'>优先级</Text>
          <Picker
            mode='selector'
            range={PRIORITY_OPTIONS}
            value={priorityIdx}
            onChange={(e) => setPriorityIdx(Number(e.detail.value))}
          >
            <View className='ct-row'>
              <Text className='ct-row__value'>{PRIORITY_OPTIONS[priorityIdx]}</Text>
              <Text className='ct-row__arrow'>›</Text>
            </View>
          </Picker>
        </View>

        <View className='ct-section ct-section--inline'>
          <View className='ct-section__inline-text'>
            <Text className='ct-section__label'>派远端沙箱执行</Text>
            <Text className='ct-section__hint'>
              开启后任务在隔离沙箱内运行（更安全、可联网工具）；关闭则本地直接处理
            </Text>
          </View>
          <Switch
            checked={remote}
            onChange={(e) => setRemote(e.detail.value)}
            color='#F97316'
          />
        </View>

        <View
          className={`ct-submit${submitting ? ' ct-submit--loading' : ''}`}
          onClick={handleSubmit}
          hoverClass='ct-submit--hover'
        >
          <Text className='ct-submit__text'>{submitting ? '创建中…' : '创建任务'}</Text>
        </View>

        <Text className='ct-foot'>创建后任务将异步执行，可以在「任务」Tab 查看进度</Text>
      </View>
    </Screen>
  )
}
