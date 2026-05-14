module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', 'node_modules'],
  rules: {
    'no-unused-vars': 'off',
    'no-case-declarations': 'off',
    'no-constant-condition': 'off',
    'react-hooks/exhaustive-deps': 'off',
    'react-refresh/only-export-components': 'off',
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unused-vars': 'off',
    'no-restricted-imports': [
      'error',
      {
        paths: [
          {
            name: 'lucide-react',
            message:
              'Use `import { icons } from "@/lib/icons"` (or `import type { LucideIcon } from "@/lib/icons"`). Only `src/components/ui/**` shadcn primitives may import lucide-react directly.',
          },
        ],
      },
    ],
  },
  overrides: [
    {
      files: ['src/components/ui/**', 'src/lib/icons.ts'],
      rules: {
        'no-restricted-imports': 'off',
      },
    },
  ],
}
