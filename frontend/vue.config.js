const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    // Forward /api calls to Flask so no CORS setup is needed in development
    proxy: { '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true } }
  }
})
