<script setup lang="ts">
import { useRouter } from 'vue-router'
import { availableLocales, loadLanguageAsync } from '~/modules/i18n'

const i18n = useI18n({ useScope: 'global' })
const router = useRouter()

async function toggleLocales() {
  // change to some real logic
  const locales = availableLocales
  const newLocale = locales[(locales.indexOf(i18n.locale.value) + 1) % locales.length]
  await loadLanguageAsync(newLocale)
}
</script>

<template>
  <nav flex="~ gap-4" mt-6 justify-center text-xl>
    <a icon-btn title="Go back" @click="() => router.back()">
      <div i-carbon-arrow-left />
    </a>

    <RouterLink icon-btn to="/" :title="i18n.t('button.home')">
      <div i-carbon-campsite />
    </RouterLink>

    <button icon-btn :title="i18n.t('button.toggle_dark')" @click="toggleDark()">
      <div i="carbon-sun dark:carbon-moon" />
    </button>

    <a icon-btn rel="noreferrer" href="https://github.com/osslab-pku/PackageDashboard" target="_blank" title="GitHub">
      <div i-carbon-logo-github />
    </a>
  </nav>
</template>
