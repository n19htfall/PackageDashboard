<script setup lang="ts">
import type { Ref } from 'vue'
import { ref } from 'vue'
import {
  NButton,
  NCard,
  NCollapseTransition,
  NDivider,
  NEllipsis,
  NGradientText,
  NGrid,
  NGridItem,
  NH1,
  NH2,
  NInput,
  NInputGroup,
  NSpace,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  PackageURL,
} from 'packageurl-js'

import BigStatsCard from '~/components/BigStatsCard.vue'
import ExpandMoreCard from '~/components/ExpandMoreCard.vue'
import AlertItem from '~/components/AlertItem.vue'
import PackageCard from '~/components/PackageCard.vue'
import type { StatsCardProps } from '~/components/StatsCard.vue'
import BarChartCard from '~/components/BarChartCard.vue'

import { useLoading } from '~/composables/loading'
import { showError } from '~/composables/error'
import { getPackageDependencies, getPackageDependents, getPackageInfo, getPackageSources, getPackageStats } from '~/api/package'

const loadingProvider = useLoading()
const { isLoading, startLoading, finishLoading, errorLoading } = loadingProvider
const message = useMessage()

const defaultEmptyMsg = '...'
const route = useRoute()
const pUrl = computed(() => route.query.purl as string || 'pkg::rpm/openeuler/Bear@3.0.20-3.oe2203sp1?arch=src&epoch=0&distro=openeuler-2203sp1')
const pUrlObj = computed(() => {
  return PackageURL.fromString(pUrl.value)
})
console.log(pUrlObj.value)

watch(pUrl, () => init())

enum StatsItems {
  PageRank = 'pagerank',
}

const chartNames: Record<StatsItems, string> = {
  pagerank: 'Package Centrality',
}

// constData should be <key from dataorder: StatsCardProps>
const cardData: Record<string, StatsCardProps> = {
  dependencies: {
    title: 'Dependencies',
    value: ref(0),
    unit: '',
    colors: ['#ec4786', '#b955a4'],
    icon: 'mdi:graph-outline',
  },
  dependents: {
    title: 'Dependents',
    value: ref(0),
    unit: '',
    colors: ['#865ec0', '#5144b4'],
    icon: 'mdi:graph-outline',
  },
  repositories: {
    title: 'Repositories',
    value: ref(0),
    unit: '',
    colors: ['#56cdf3', '#719de3'],
    icon: 'ant-design:bar-chart-outlined',
  },
  pagerank: {
    title: 'Centrality',
    value: ref(0),
    unit: '',
    colors: ['#fcbc25', '#f68057'],
    icon: 'ant-design:bar-chart-outlined',
  },
}

const packageInfo = ref<Package | null>(null)
/**
 * Fetches and Updates the Package information
 * Don't chain promises, it will cause the waterfall effect
 * */
async function fetchPackageInfo() {
  startLoading()
  try {
    packageInfo.value = await getPackageInfo(pUrl.value)
    finishLoading()
  }
  catch (e) {
    errorLoading()
    showError(message, e as Error)
  }
}

const packageDependencies: Ref<Array<PackageDependency>> = ref([])
async function fetchPackageDependencies() {
  startLoading()
  try {
    packageDependencies.value = await getPackageDependencies(pUrl.value)
    finishLoading()
  }
  catch (e) {
    packageDependencies.value = []
    errorLoading()
    showError(message, e as Error)
  }
  if (!packageDependencies.value)
    return
  cardData.dependencies.value.value = packageDependencies.value.length
}

const packageDependents: Ref<Array<PackageDependency>> = ref([])
async function fetchPackageDependents() {
  startLoading()
  try {
    packageDependents.value = await getPackageDependents(pUrl.value)
    finishLoading()
  }
  catch (e) {
    packageDependents.value = []
    errorLoading()
    showError(message, e as Error)
  }
  if (!packageDependents.value)
    return
  cardData.dependents.value.value = packageDependents.value.length
}

const packageSources: Ref<Array<PackageSource>> = ref([])
async function fetchPackageSources() {
  packageSources.value = []
  startLoading()
  try {
    packageSources.value = await getPackageSources(pUrl.value)
    finishLoading()
  }
  catch (e) {
    errorLoading()
    showError(message, e as Error)
  }
  if (!packageSources.value)
    return
  cardData.repositories.value.value = packageSources.value.length
}

const MOCK_AXIS = [
  '2021-02-01T00:00:00',
  '2021-03-01T00:00:00',
  '2021-04-01T00:00:00',
  '2021-05-01T00:00:00',
  '2021-06-01T00:00:00',
  '2021-07-01T00:00:00',
  '2021-08-01T00:00:00',
  '2021-09-01T00:00:00',
  '2021-10-01T00:00:00',
  '2021-11-01T00:00:00',
  '2021-12-01T00:00:00',
  '2022-01-01T00:00:00',
  '2022-02-01T00:00:00',
  '2022-03-01T00:00:00',
  '2022-04-01T00:00:00',
  '2022-05-01T00:00:00',
  '2022-06-01T00:00:00',
  '2022-07-01T00:00:00',
  '2022-08-01T00:00:00',
  '2022-09-01T00:00:00',
  '2022-10-01T00:00:00',
  '2022-11-01T00:00:00',
  '2022-12-01T00:00:00',
  '2023-01-01T00:00:00',
  '2023-02-01T00:00:00',
  '2023-03-01T00:00:00',
  '2023-04-01T00:00:00',
  '2023-05-01T00:00:00',
]
const MOCK_PAGERANK = [
  0.001735,
  0.002001,
  0.001735,
  0.001823,
  0.002192,
  0.002323,
  0.003894,
  0.003988,
  0.004192,
  0.004323,
  0.004894,
  0.004988,
  0.005192,
  0.005323,
  0.005894,
  0.005988,
  0.006792,
  0.005323,
  0.006894,
  0.004988,
  0.006192,
  0.005223,
  0.007894,
  0.006958,
  0.006192,
  0.005323,
  0.005874,
  0.005903,
]

const barAxis = ref<Array<string>>([])
const barData: Record<StatsItems, Ref<Array<number>>> = {
  pagerank: ref([]),
}

const packageStats = ref<PackageStats[]>([])
async function fetchPackageStats() {
  let packageStats: PackageStats[] = []
  startLoading()
  try {
    packageStats = await getPackageStats(pUrl.value)
    finishLoading()
  }
  catch (e) {
    packageStats = []
    errorLoading()
    showError(message, e as Error)
  }

  // if (!packageStats) {
  //   return
  // }

  const dates = MOCK_AXIS
  const stats: Record<StatsItems, Array<number>> = {
    pagerank: MOCK_PAGERANK,
  }

  packageStats.sort((a, b) => {
    return new Date(a.stats_from).getTime() - new Date(b.stats_from).getTime()
  })

  for (const statsRecord of packageStats) {
    dates.push(new Date(statsRecord.stats_from).toLocaleDateString())
    stats.pagerank.push(statsRecord.pagerank)
  }

  // sum up the data
  cardData.pagerank.value.value = stats.pagerank.reduce((a, b) => a + b, 0)

  // update the figures
  for (const key in barData) {
    const _key = key as StatsItems
    barData[_key].value = stats[_key]
  }
  barAxis.value = dates
}

const PKG_GRID_SPAN = '0:24 640:12 960:8 1280:6 1920:4'
const N_PKGS_DEFAULT = 4
const showDependencies = ref(false)
function toggleShowDependencies() {
  showDependencies.value = !showDependencies.value
}
const showDependents = ref(false)
function toggleShowDependents() {
  showDependents.value = !showDependents.value
}

function init() {
  fetchPackageDependencies()
  fetchPackageDependents()
  fetchPackageSources()
  fetchPackageInfo()
  fetchPackageStats()
  showDependencies.value = false
  showDependents.value = false
}
init()

const iconNameMap = {
  deb: 'vscode-icons:folder-type-debian',
  rpm: 'vscode-icons:folder-type-package',
  maven: 'vscode-icons:folder-type-maven',
  gradle: 'vscode-icons:folder-type-gradle',
  npm: 'vscode-icons:folder-type-js',
  yarn: 'vscode-icons:folder-type-yarn',
  pip: 'vscode-icons:folder-type-python',
  gomod: 'vscode-icons:folder-type-component',
  cargo: 'vscode-icons:file-type-cargo',
  default: 'vscode-icons:file-type-package',
}

const iconName = computed(() => {
  if (pUrlObj.value.type in iconNameMap) {
    const _name = pUrlObj.value.type as keyof typeof iconNameMap
    return iconNameMap[_name]
  }
  else {
    return iconNameMap.default
  }
})
</script>

<template>
  <div class="package-container">
    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem span="0:24 640:24 1280:12">
        <NCard :bordered="false" class="h-full w-full rounded-10px shadow-sm">
          <template #header>
            <NGradientText class="text-30px">
              {{ packageInfo ? `${packageInfo.name} ${packageInfo.version}` : defaultEmptyMsg }}
            </NGradientText>
          </template>

          <template #header-extra>
            <SvgIcon :icon="iconName" class="text-30px" />
          </template>

          <NEllipsis class="text-#777" :line-clamp="3">
            {{ packageInfo ? packageInfo?.description : defaultEmptyMsg }}
          </NEllipsis>

          <template #footer>
            <div v-if="packageInfo && packageInfo.license" class="flex gap-12px overflow-auto">
              <NTag v-if="packageInfo && packageInfo.arch" type="warning" round>
                {{ packageInfo.arch }}
              </NTag>

              <NTag v-if="packageInfo && packageInfo.distro" type="info" round>
                {{ packageInfo.distro }}
              </NTag>
              <NTag v-for="item in packageInfo.license.split(/and/)" :key="item" type="error" round>
                <div class="flex gap-0.3em">
                  <SvgIcon icon="tabler:license" />
                  {{ item }}
                </div>
              </NTag>
            </div>
          </template>

          <template #action>
            <a :href="packageInfo ? packageInfo.homepage_url : ''" class="w-full flex justify-center gap-0.5em" target="_blank">
              <SvgIcon icon="tabler:external-link" class="position-relative top-3px" />
              {{ packageInfo ? packageInfo.homepage_url : '' }}
            </a>
          </template>
        </NCard>
      </NGridItem>

      <NGridItem span="0:24 640:24 1280:12">
        <NCard :bordered="false" class="h-full w-full rounded-10px shadow-sm">
          <template #header>
            <NGradientText class="text-30px" type="error">
              Alerts
            </NGradientText>
          </template>

          <template #header-extra>
            <SvgIcon icon="fluent-emoji:warning" class="text-30px" />
          </template>

          <div class="gap flex flex-col items-baseline gap-0.5em">
            <AlertItem type="success" icon="ant-design:check-circle-filled" title="License Compatible">
              <a href="https://licenserec.com" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span> LicenseRec</a>
              did not find any license compatibility issues.
            </AlertItem>
            <AlertItem type="warning" icon="ant-design:book-filled" title="Repository Archived">
              Repository <a href="https://github.com/atom/atom" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span> atom</a> is archived.
            </AlertItem>
            <AlertItem type="error" icon="ant-design:bug-filled" title="Vulnerabilities">
              <a href="https://www.cvedetails.com/cve/CVE-2017-1000424/" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span> CVE-2017-1000424 </a> (Medium).
            </AlertItem>
            <AlertItem type="primary" icon="fluent:people-team-48-filled" title="Many Contributors">
              Repository <a href="https://github.com/atom/atom" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span> atom</a> has 495 contributors.
            </AlertItem>
          </div>
        </NCard>
      </NGridItem>
    </NGrid>

    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem :span="PKG_GRID_SPAN">
        <BigStatsCard
          :id="cardData.dependencies.id"
          :title="cardData.dependencies.title"
          :icon="cardData.dependencies.icon"
          :value="cardData.dependencies.value"
          :unit="cardData.dependencies.unit"
          :colors="cardData.dependencies.colors"
        />
      </NGridItem>
      <NGridItem
        v-for="v in (showDependencies || packageDependencies.length <= N_PKGS_DEFAULT + 1 ? packageDependencies : packageDependencies.slice(0, N_PKGS_DEFAULT))"
        :key="v.dep_purl"
        :span="PKG_GRID_SPAN"
      >
        <PackageCard :purl="v.dep_purl" :constraint="v.constraint" />
      </NGridItem>
      <NGridItem v-if="packageDependencies.length > N_PKGS_DEFAULT + 1" :span="PKG_GRID_SPAN">
        <ExpandMoreCard :show="showDependencies" :count="packageDependencies.length - N_PKGS_DEFAULT" @click="toggleShowDependencies" />
      </NGridItem>
    </NGrid>

    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem :span="PKG_GRID_SPAN">
        <BigStatsCard
          :id="cardData.dependents.id"
          :title="cardData.dependents.title"
          :icon="cardData.dependents.icon"
          :value="cardData.dependents.value"
          :unit="cardData.dependents.unit"
          :colors="cardData.dependents.colors"
        />
      </NGridItem>
      <NGridItem v-for="v in (showDependents ? packageDependents : packageDependents.slice(0, N_PKGS_DEFAULT))" :key="v.dep_purl" :span="PKG_GRID_SPAN">
        <PackageCard :purl="v.purl" :constraint="v.constraint" />
      </NGridItem>
      <NGridItem v-if="packageDependents.length > N_PKGS_DEFAULT + 1" :span="PKG_GRID_SPAN">
        <ExpandMoreCard :show="showDependents" :count="packageDependents.length - N_PKGS_DEFAULT" @click="toggleShowDependents" />
      </NGridItem>
    </NGrid>

    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem :span="PKG_GRID_SPAN">
        <BigStatsCard
          :id="cardData.pagerank.id"
          :title="cardData.pagerank.title"
          :icon="cardData.pagerank.icon"
          :value="cardData.pagerank.value"
          :unit="cardData.pagerank.unit"
          :colors="cardData.pagerank.colors"
        />
      </NGridItem>
      <NGridItem
        span="0:24 640:12 960:16 1280:18 1920:20"
      >
        <BarChartCard
          title="Centrality Score"
          :data="barData.pagerank"
          :axis="barAxis"
        />
      </ngriditem>
    </NGrid>
  </div>
</template>

<style scoped>
.package-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin: 16px;
}

.text-stroke-custom {
  text-shadow: 0px 0px 5px black;
}

#container {
  overflow: hidden;
  width: 200px;
}

#inner {
  overflow: hidden;
  width: 2000px;
}

.child {
  float: left;
  width: 50px;
  height: 50px;
}
</style>

<route lang="yaml">
meta:
  layout: default
</route>
