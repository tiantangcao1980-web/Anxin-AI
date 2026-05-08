const fs = require('fs')
const path = require('path')

const projectRoot = path.resolve(__dirname, '..')
const pageFiles = [
  'src/pages/index/index.tsx',
  'src/pages/profile/index.tsx',
]

const forbiddenPatterns = [
  {
    pattern: /path:\s*['"]\s*['"]/,
    message: 'primary navigation item has an empty path',
  },
  {
    pattern: /功能开发中/,
    message: 'primary navigation still ends in a generic development placeholder',
  },
]

const failures = []

for (const relativePath of pageFiles) {
  const absolutePath = path.join(projectRoot, relativePath)
  const source = fs.readFileSync(absolutePath, 'utf8')
  for (const { pattern, message } of forbiddenPatterns) {
    if (pattern.test(source)) {
      failures.push(`${relativePath}: ${message}`)
    }
  }
}

if (failures.length > 0) {
  console.error('Mini-program navigation boundary: FAIL')
  for (const failure of failures) {
    console.error(`  - ${failure}`)
  }
  process.exit(1)
}

console.log('Mini-program navigation boundary: PASS')
