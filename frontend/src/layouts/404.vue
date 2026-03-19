<script setup lang="ts">
const router = useRouter()
const i18n = useI18n({ useScope: 'global' })
</script>

<template>
  <main p="x4 y10" text="center teal-700 dark:gray-200">
    <div text-4xl>
      <div i-carbon-warning inline-block />
    </div>
    <RouterView />
    <div>
      <button text-sm btn m="3 t8" @click="router.back()">
        {{ i18n.t('button.back') }}
      </button>
    </div>
  </main>
</template>
