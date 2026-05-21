import { createApp } from 'vue'
import { registerSW } from 'virtual:pwa-register'
import './styles.css'
import App from './App.vue'

registerSW({ immediate: true })

createApp(App).mount('#app')
