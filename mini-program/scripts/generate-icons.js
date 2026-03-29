/**
 * 生成 TabBar 占位图标
 * 运行: node scripts/generate-icons.js
 */
const fs = require('fs')
const path = require('path')
const zlib = require('zlib')

const assetsDir = path.join(__dirname, '..', 'src', 'assets')
if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true })
}

function createPNG(r, g, b, size = 81) {
  // Create raw image data (RGBA) - simple filled circle
  const rawRows = []
  const center = Math.floor(size / 2)
  const radius = center - 4

  for (let y = 0; y < size; y++) {
    const row = Buffer.alloc(1 + size * 4) // filter byte + RGBA
    row[0] = 0 // no filter
    for (let x = 0; x < size; x++) {
      const dx = x - center
      const dy = y - center
      const dist = Math.sqrt(dx * dx + dy * dy)
      const offset = 1 + x * 4
      if (dist <= radius) {
        let alpha = 255
        if (dist > radius - 1.5) {
          alpha = Math.max(0, Math.round(((radius - dist + 1.5) / 1.5) * 255))
        }
        row[offset] = r
        row[offset + 1] = g
        row[offset + 2] = b
        row[offset + 3] = alpha
      }
      // else stays 0,0,0,0 (transparent)
    }
    rawRows.push(row)
  }

  const rawData = Buffer.concat(rawRows)
  const compressed = zlib.deflateSync(rawData)

  // Build PNG
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])

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

  // IHDR: width, height, bit depth, color type (6=RGBA), compression, filter, interlace
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8   // bit depth
  ihdr[9] = 6   // color type RGBA
  ihdr[10] = 0  // compression
  ihdr[11] = 0  // filter
  ihdr[12] = 0  // interlace

  return Buffer.concat([
    signature,
    chunk('IHDR', ihdr),
    chunk('IDAT', compressed),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

const icons = [
  { name: 'tab-home.png', r: 153, g: 153, b: 153 },
  { name: 'tab-home-active.png', r: 212, g: 165, b: 116 },
  { name: 'tab-chat.png', r: 153, g: 153, b: 153 },
  { name: 'tab-chat-active.png', r: 212, g: 165, b: 116 },
  { name: 'tab-profile.png', r: 153, g: 153, b: 153 },
  { name: 'tab-profile-active.png', r: 212, g: 165, b: 116 },
]

for (const icon of icons) {
  const png = createPNG(icon.r, icon.g, icon.b)
  const filePath = path.join(assetsDir, icon.name)
  fs.writeFileSync(filePath, png)
  console.log(`Created: ${filePath}`)
}

console.log('\nAll icons generated successfully!')
