<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SelectOption } from 'naive-ui'
import { NButton, NDivider, NGrid, NGridItem, NH1, NInput, NInputGroup, NInputNumber, NPagination, NSelect, NSpace, NTable, useMessage, useThemeVars } from 'naive-ui'
import { getPackageDistros, searchPackageList } from '~/api/package'
import WavesBackground from '~/components/Waves.vue'

const themeVars = useThemeVars()
const { width, height } = useWindowSize()

const currentPage = ref(1)
const pageCount = ref(1)
const pageSize = ref(12)
const regex = ref('')
const packages = ref<Package[]>([])
const { isLoading, startLoading, finishLoading, errorLoading } = useLoading()
const message = useMessage()

const packageDistros = ref<string[]>([])
const selectedDistros = ref<string[]>([])
const distroOptions = computed(() => {
  return packageDistros.value.map((distro) => {
    return {
      label: distro.split('-').join(' '),
      value: distro,
    }
  })
})

async function fetchPackages() {
  startLoading()
  try {
    const res = await searchPackageList(regex.value, currentPage.value, pageSize.value, selectedDistros.value)
    finishLoading()
    packages.value = res.items
    currentPage.value = res.page ? res.page : 1
    pageCount.value = res.pages ? res.pages : 1
  }
  catch (e) {
    errorLoading()
    showError(message, e as Error)
  }
}
fetchPackages()

async function fetchPackageDistros() {
  startLoading()
  try {
    finishLoading()
    packageDistros.value = await getPackageDistros()
    console.log('packageDistros', packageDistros.value)
  }
  catch (e) {
    showError(message, e as Error)
    errorLoading()
  }
}
fetchPackageDistros()

const pageSizes = [
  {
    label: '6 Per Page',
    value: 6,
  },
  {
    label: '12 Per Page',
    value: 12,
  },
  {
    label: '24 Per Page',
    value: 24,
  },
  {
    label: '48 Per Page',
    value: 48,
  },
]
</script>

<template>
  <div class="page-container flex flex-col gap-1em">
    <div class="text-center">
      <NH1>Package Dashboard</NH1>
    </div>
    <NInputGroup>
      <NInput
        v-model:value="regex"
        class="width-40%"
        placeholder="Enter what you know about the package (regex is supported)"
        clearable
        :loading="isLoading"
        :on-keyup="(e) => { if (e.key === 'Enter') fetchPackages() }"
      />
      <NButton type="primary" ghost :disabled="isLoading" @click="fetchPackages">
        <SvgIcon icon="ic:baseline-search" />
      </NButton>
    </NInputGroup>

    <div class="select-container">
      <NPagination
        v-model:page-size="pageSize"
        v-model:page="currentPage"
        :page-count="pageCount"
        show-size-picker
        :page-sizes="pageSizes"
        show-total
        :on-update-page="fetchPackages"
        :on-update-page-size="fetchPackages"
        :page-slot="width >= 520 ? 8 : 5"
      />

      <NSelect
        v-model:value="selectedDistros"
        multiple
        :options="distroOptions"
        class="distro-select"
        placeholder="Please select the distributions"
      />
    </div>

    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem
        v-for="v in packages"
        :key="v.purl"
        span="0:24 640:12 960:8 1280:6 1920:4"
      >
        <PackageCard :purl="v.purl" :constraint="v.summary" />
      </NGridItem>
    </NGrid>
  </div>

  <WavesBackground :color="themeVars.primaryColor" class="wave-background" />
</template>

<style scoped>
.page-container {
  padding: 16px;
  padding-top: 8vw;
  padding-bottom: 4vw;
}

.page-container * {
  z-index: 2;
}

.wave-background {
  position: fixed;
  bottom: 0px;
  left: 0px;
  right: 0px;
  top: 0px;
  pointer-events: none;
}

.distro-select {
  max-width: calc(100px + 20vw);
  min-width: 200px;
}

.select-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

@media screen and (max-width: 640px) {
  .select-container {
    flex-direction: column;
    align-items: center;
  }

  .distro-select {
    max-width: 100%;
  }
}
</style>

<route lang="yaml">
meta:
  layout: default
  </route>
