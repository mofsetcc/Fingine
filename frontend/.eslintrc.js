module.exports = {
    root: true,
    env: {
        browser: true,
        es2020: true,
        node: true,
        jest: true
    },
    extends: [
        'eslint:recommended',
        '@typescript-eslint/recommended',
        'plugin:react/recommended',
        'plugin:react-hooks/recommended',
        'prettier'
    ],
    ignorePatterns: ['dist', '.eslintrc.js', 'node_modules', 'coverage'],
    parser: '@typescript-eslint/parser',
    parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
            jsx: true
        }
    },
    plugins: [
        '@typescript-eslint',
        'react',
        'react-hooks',
        'react-refresh'
    ],
    rules: {
        // React rules
        'react/react-in-jsx-scope': 'off',
        'react/prop-types': 'off',
        'react/jsx-uses-react': 'off',
        'react/jsx-uses-vars': 'error',

        // TypeScript rules
        '@typescript-eslint/no-unused-vars': ['error', {
            argsIgnorePattern: '^_',
            varsIgnorePattern: '^_'
        }],
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off',
        '@typescript-eslint/no-explicit-any': 'warn',
        '@typescript-eslint/no-non-null-assertion': 'warn',

        // React Hooks rules
        'react-hooks/rules-of-hooks': 'error',
        'react-hooks/exhaustive-deps': 'warn',

        // React Refresh rules (only warn to not break CI)
        'react-refresh/only-export-components': ['warn', {
            allowConstantExport: true
        }],

        // General rules
        'no-console': 'warn',
        'no-debugger': 'error',
        'prefer-const': 'error',
        'no-var': 'error'
    },
    settings: {
        react: {
            version: 'detect',
        },
    },
    // Override rules for test files
    overrides: [
        {
            files: ['**/__tests__/**/*', '**/*.test.*', '**/*.spec.*'],
            env: {
                jest: true
            },
            rules: {
                '@typescript-eslint/no-explicit-any': 'off',
                'no-console': 'off'
            }
        }
    ]
};