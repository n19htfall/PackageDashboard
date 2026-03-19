import type { Locale } from 'vue-i18n'
import { createI18n } from 'vue-i18n'
import { type UserModule } from '~/types'

const DEFAULT_LOCALE = 'en'

const localeModules = import.meta.glob('../../locales/*.yml', { eager: true }) as Record<
  string,
  { default: Record<string, string> }
>

const messages = Object.fromEntries(
  Object.entries(localeModules)
    .map(([path, module]) => [path.match(/([\w-]*)\.yml$/)?.[1], module.default])
    .filter(([locale]) => Boolean(locale)),
) as Record<Locale, Record<string, string>>

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: DEFAULT_LOCALE,
  fallbackLocale: DEFAULT_LOCALE,
  messages,
})

export const availableLocales = Object.keys(messages)

function setI18nLanguage(lang: Locale) {
  i18n.global.locale.value = lang as any
  if (typeof document !== 'undefined')
    document.querySelector('html')?.setAttribute('lang', lang)
  return lang
}

export async function loadLanguageAsync(lang: string): Promise<Locale> {
  if (!messages[lang as Locale])
    return setI18nLanguage(DEFAULT_LOCALE)

  return setI18nLanguage(lang as Locale)
}

export const install: UserModule = ({ app }) => {
  app.use(i18n)
  setI18nLanguage(DEFAULT_LOCALE)
}
