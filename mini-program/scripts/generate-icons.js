// -*- coding: utf-8 -*-
/**
 * 生成 V3 TabBar 占位图标（4 tab × 2 状态 = 8 个 PNG）
 *
 * 设计：使用一个简单的标记形状（圆 + 内嵌 emoji-like 抽象）来区分 4 个 tab。
 * 实际上线时由设计师替换为 Lottie / 真 PNG。本脚本生成的是「能让 weapp build 不报错」的占位。
 *
 * 运行：node scripts/generate-icons.js
 *
 * 输出：src/assets/tab/{agents,tasks,capabilities,me}{,-active}.png
 */

const fs = require('fs')
const path = require('path')
const zlib = require('zlib')

const assetsDir = path.join(__dirname, '..', 'src', 'assets', 'tab')
if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true })
}

// 同步移除旧的根级 tab-*.png（已被 V3 子目录替代）
const oldAssetsDir = path.join(__dirname, '..', 'src', 'assets')
if (fs.existsSync(oldAssetsDir)) {
  for (const f of fs.readdirSync(oldAssetsDir)) {
    if (/^tab-(home|chat|profile)(-active)?\.png$/.test(f)) {
      try {
        fs.unlinkSync(path.join(oldAssetsDir, f))
      } catch {}
    }
  }
}

function crc32(buf) {
  let c = 0xffffffff
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i]
    for (let j = 0; j < 8; j++) {
      c = (c >>> 1) ^ (c & 1 ? 0xedb88320 : 0)
    }
  }
  return (c ^ 0xffffffff) >>> 0
}

function chunk(type, data) {
  const typeData = Buffer.concat([Buffer.from(type), data])
  const len = Buffer.alloc(4)
  len.writeUInt32BE(data.length)
  const crc = Buffer.alloc(4)
  crc.writeUInt32BE(crc32(typeData))
  return Buffer.concat([len, typeData, crc])
}

/**
 * 渲染 PNG —— 根据 shape 生成不同形状（圆 / 方框 / 三角 / 网格）
 */
function createPNG({ r, g, b, shape, size = 81 }) {
  const rawRows = []
  const center = Math.floor(size / 2)
  const radius = center - 6

  for (let y = 0; y < size; y++) {
    const row = Buffer.alloc(1 + size * 4)
    row[0] = 0
    for (let x = 0; x < size; x++) {
      const dx = x - center
      const dy = y - center
      const offset = 1 + x * 4
      let alpha = 0

      switch (shape) {
        case 'circle': {
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist <= radius) {
            alpha = 255
            if (dist > radius - 1.5) {
              alpha = Math.max(0, Math.round(((radius - dist + 1.5) / 1.5) * 255))
            }
          }
          break
        }
        case 'rounded-square': {
          const adx = Math.abs(dx)
          const ady = Math.abs(dy)
          const r2 = radius - 2
          if (adx <= r2 && ady <= r2) {
            // 角点圆角
            const cornerDist = Math.max(adx - (r2 - 6), 0)
            const cornerDistY = Math.max(ady - (r2 - 6), 0)
            const cd = Math.sqrt(cornerDist * cornerDist + cornerDistY * cornerDistY)
            if (cd <= 6) alpha = 255
          }
          break
        }
        case 'triangle': {
          // 向上三角
          const ny = (y - 8) / (size - 16)
          if (ny >= 0 && ny <= 1) {
            const halfWidth = ny * (radius - 4)
            if (Math.abs(dx) <= halfWidth) alpha = 255
          }
          break
        }
        case 'person': {
          // 头部：上方圆
          const headCY = center - radius * 0.4
          const headR = radius * 0.32
          const dh = Math.sqrt(dx * dx + (y - headCY) * (y - headCY))
          if (dh <= headR) alpha = 255
          // 身体：下方半圆
          const bodyCY = center + radius * 0.25
          const bodyR = radius * 0.65
          const db = Math.sqrt(dx * dx + (y - bodyCY) * (y - bodyCY))
          if (db <= bodyR && y >= bodyCY - bodyR * 0.2) alpha = 255
          break
        }
      }

      if (alpha > 0) {
        row[offset] = r
        row[offset + 1] = g
        row[offset + 2] = b
        row[offset + 3] = alpha
      }
    }
    rawRows.push(row)
  }

  const rawData = Buffer.concat(rawRows)
  const compressed = zlib.deflateSync(rawData)
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8
  ihdr[9] = 6
  ihdr[10] = 0
  ihdr[11] = 0
  ihdr[12] = 0
  return Buffer.concat([
    signature,
    chunk('IHDR', ihdr),
    chunk('IDAT', compressed),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

const INACTIVE = { r: 134, g: 144, b: 156 } // #86909C
const ACTIVE = { r: 212, g: 165, b: 116 } // #D4A574

const tabs = [
  { name: 'agents', shape: 'circle' },
  { name: 'tasks', shape: 'rounded-square' },
  { name: 'capabilities', shape: 'triangle' },
  { name: 'me', shape: 'person' },
]

let count = 0
for (const tab of tabs) {
  for (const state of ['', '-active']) {
    const color = state ? ACTIVE : INACTIVE
    const png = createPNG({ ...color, shape: tab.shape })
    const filename = `${tab.name}${state}.png`
    const filePath = path.join(assetsDir, filename)
    fs.writeFileSync(filePath, png)
    console.log(`[icons] Created: assets/tab/${filename}`)
    count++
  }
}

console.log(`\n[icons] Done. Generated ${count} PNG files in src/assets/tab/`)
