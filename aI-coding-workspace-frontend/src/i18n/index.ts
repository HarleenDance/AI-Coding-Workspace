import { createI18n } from 'vue-i18n'
import zh from './zh'
import en from './en'

// 从 localStorage 读取语言偏好，默认中文
const savedLang = localStorage.getItem('app-language') || 'zh'

const i18n = createI18n({
  legacy: false,
  locale: savedLang,
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export default i18n

/** 切换语言并持久化 */
export function setLanguage(lang: 'zh' | 'en') {
  i18n.global.locale.value = lang
  localStorage.setItem('app-language', lang)
}

/** 获取当前语言 */
export function getLanguage(): 'zh' | 'en' {
  return i18n.global.locale.value as 'zh' | 'en'
}
