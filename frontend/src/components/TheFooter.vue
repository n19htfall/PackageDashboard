<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NButton, NInput, NModal } from 'naive-ui'
import { availableLocales, loadLanguageAsync } from '~/modules/i18n'

const { t, locale } = useI18n()
const router = useRouter()
const showSubscribeModal = ref(false)
const subscribeEmail = ref('')
const showAlert = ref(false)

async function toggleLocales() {
  // change to some real logic
  const locales = availableLocales
  const newLocale = locales[(locales.indexOf(locale.value) + 1) % locales.length]
  await loadLanguageAsync(newLocale)
  locale.value = newLocale
}

function handleSubscribe() {
  const email = subscribeEmail.value
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailPattern.test(email)) {
    showAlert.value = true
    return
  }
  showSubscribeModal.value = false
  subscribeEmail.value = ''
  showAlert.value = false
}
</script>

<template>
  <nav flex="~ gap-4" mt-6 justify-center text-xl>
    <a icon-btn title="Go back" @click="() => router.back()">
      <div i-carbon-arrow-left />
    </a>

    <RouterLink icon-btn to="/" :title="t('button.home')">
      <div i-carbon-campsite />
    </RouterLink>

    <button icon-btn :title="t('button.toggle_dark')" @click="toggleDark()">
      <div i="carbon-sun dark:carbon-moon" />
    </button>

    <!-- <RouterLink icon-btn to="/about" :title="t('button.about')">
      <div i-carbon-dicom-overlay />
    </RouterLink> -->

    <!-- <a icon-btn rel="noreferrer" href="https://github.com/12f23eddde/package-dashboard" target="_blank" title="GitHub">
      <div i-carbon-logo-github />
    </a> -->

    <button
      v-if="router.currentRoute.value.name !== 'index'" icon-btn title="Subscribe Package"
      @click="showSubscribeModal = true"
    >
      <div i-carbon-notification />
    </button>
  </nav>
  <NModal v-model:show="showSubscribeModal" preset="dialog" title="Subscribe" style="max-width:350px;">
    <div flex="~ col gap-4" py-2>
      <!-- <NInput v-model:value="subscribeEmail" placeholder="Enter your email" clearable autofocus /> -->
      <input
        v-model="subscribeEmail" type="email" placeholder="Enter your email"
        style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;" required
      >
      <div v-if="showAlert" style="color: red; font-size: 0.875em;">
        Please enter a valid email address.
      </div>
      <NButton ghost secondary type="primary" block @click="handleSubscribe">
        {{ "Confirm" }}
      </NButton>
    </div>
  </NModal>
</template>
