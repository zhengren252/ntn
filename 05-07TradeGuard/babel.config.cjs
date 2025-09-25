module.exports = {
  presets: [
    [
      '@babel/preset-env',
      {
        targets: {
          node: 'current'
        },
        modules: 'commonjs'
      }
    ]
  ],
  plugins: [
    // 支持动态导入
    '@babel/plugin-syntax-dynamic-import'
  ],
  env: {
    test: {
      presets: [
        [
          '@babel/preset-env',
          {
            targets: {
              node: 'current'
            },
            modules: 'commonjs'
          }
        ]
      ]
    }
  }
};