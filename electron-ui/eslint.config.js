import js from '@eslint/js'
import globals from 'globals'
import {globalIgnores} from 'eslint/config'

export default [
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: '@typescript-eslint/parser',
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
      },
      globals: globals.browser,
    },
    plugins: [
      '@typescript-eslint',
      'react-hooks',
      'react-refresh',
    ],
    extends: [
      js.configs.recommended,
      'plugin:@typescript-eslint/recommended',
      'plugin:react-hooks/recommended',
      'plugin:react-refresh/vite',
    ],
  },
]
