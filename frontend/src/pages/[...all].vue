<script setup lang="ts">
const i18n = useI18n({ useScope: 'global' })
</script>

<template>
  <div>
    {{ i18n.t('not-found') }}
  </div>
</template>

<route lang="yaml">
meta:
  layout: 404
</route>
