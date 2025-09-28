<script setup lang="ts">
// auto-detect dark theme support
import { useDark } from '@vueuse/core'
import { NConfigProvider, NLayout, NLoadingBarProvider, NMessageProvider, NNotificationProvider, darkTheme } from 'naive-ui'

const isDark = useDark()
</script>

<template>
  <NConfigProvider :theme="isDark ? darkTheme : null">
    <NLayout class="default-layout">
      <NLoadingBarProvider>
        <NNotificationProvider>
          <NMessageProvider>
            <TheFooter />
            <div class="layout-content">
              <router-view />
            </div>
          </NMessageProvider>
        </NNotificationProvider>
      </NLoadingBarProvider>

      <div class="shadow-meta">
        <!-- Layout: Default -->
      </div>
    </NLayout>
  </NConfigProvider>
</template>

<style>
.default-layout {
  height: 100%;
  min-height: 100vh;
}

/* really wide screens */
@media screen and (min-width: 1000px) {
  .layout-content {
    width: max(1000px, 80%);
    margin: auto;
  }
}
</style>
