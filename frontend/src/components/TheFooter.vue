<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

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

    <a icon-btn rel="noreferrer" href="https://github.com/osslab-pku/PackageDashboard" target="_blank" title="GitHub">
      <div i-carbon-logo-github />
    </a>
  </nav>
</template>
