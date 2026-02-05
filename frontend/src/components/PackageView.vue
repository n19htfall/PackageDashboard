<script setup lang="ts">
import type { Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import {
  NButton,
  NCard,
  NDivider,
  NEllipsis,
  NGradientText,
  NGrid,
  NGridItem,
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
import DependencyView from '~/components/DependencyView.vue'

import { useLoading } from '~/composables/loading'
import { showError } from '~/composables/error'
import { getPackageAlerts, getPackageDependencies, getPackageDependents, getPackageInfo, getPackageRec, getPackageTransitiveDependencies } from '~/api/package'

const loadingProvider = useLoading()
const { isLoading, startLoading, finishLoading, errorLoading } = loadingProvider
const message = useMessage()

const defaultEmptyMsg = '...'

const { purl, constraint } = definePropsRefs<{
  purl: string
  constraint?: string
}>()

const pUrl = computed(() => {
  return purl.value ? purl.value : 'pkg::rpm/openeuler/Bear@3.0.20-3.oe2203sp1?arch=src&epoch=0&distro=openeuler-2203sp1'
})
const pUrlObj = computed(() => {
  return PackageURL.fromString(decodeURIComponent(pUrl.value).replace('@', '%40'))
})

watch(purl, () => init())

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
  recommendations: {
    title: 'Recommended',
    value: ref(0),
    unit: '',
    colors: ['#fcbc25', '#f68057'],
    icon: 'mdi:thumb-up-outline',
  },
}

const packageInfo = ref<Package | null>(null)

async function fetchPackageInfo() {
  startLoading()
  try {
    packageInfo.value = await getPackageInfo(pUrl.value)
    finishLoading()
    // 当获取到 info 后，如果存在 repo_url，则获取推荐
    if (packageInfo.value?.repo_url) {
      fetchPackageRec(packageInfo.value.repo_url)
    }
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

const packageTransitiveDependencies: Ref<Array<PackageDependency>> = ref([])
async function fetchPackageTransitiveDependencies() {
  startLoading()
  try {
    packageTransitiveDependencies.value = await getPackageTransitiveDependencies(pUrl.value)
    finishLoading()
  }
  catch (e) {
    packageTransitiveDependencies.value = []
    errorLoading()
    showError(message, e as Error)
  }
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

const packageAlert: Ref<PackageAlert | null> = ref(null)
async function fetchPackageAlers() {
  startLoading()
  try {
    packageAlert.value = await getPackageAlerts(pUrl.value)
    if(packageAlert.value){
      showAlerts.value = true;
    }
    finishLoading()
    // toggleShowAlerts()
  }
  catch (e) {
    packageAlert.value = null
    errorLoading()
    showError(message, e as Error)
  }
}

const packageRec: Ref<Array<Package> | null> = ref(null)
async function fetchPackageRec(url: string) {
  startLoading()
  try {
    packageRec.value = await getPackageRec(url)
    finishLoading()
  }
  catch (e) {
    packageRec.value = [] // Fixed: Assign to packageRec, not packageAlert
    errorLoading()
    showError(message, e as Error)
  }
  if (packageRec.value) {
    cardData.recommendations.value.value = packageRec.value.length
  }
}

function getCVEUrl(cveid: string) {
  return `https://www.cvedetails.com/cve/${cveid}/`
}

const PKG_GRID_SPAN = '0:24 640:12 960:8 1280:6 1920:4'
const N_PKGS_DEFAULT = 4

const showDependencies = ref(false)
function toggleShowDependencies() {
  if (!showDependencies.value && packageDependencies.value.length > 100) {
    showError(message, 'Displaying too many packages freezes the browser. Working on a fix.')
    return
  }
  showDependencies.value = !showDependencies.value
}

const showDependents = ref(false)
function toggleShowDependents() {
  if (!showDependents.value && packageDependents.value.length > 100) {
    showError(message, 'Displaying too many packages freezes the browser. Working on a fix.')
    return
  }
  showDependents.value = !showDependents.value
}

const showRecommendations = ref(false)
function toggleShowRecommendations() {
  if (!showRecommendations.value && packageRec.value && packageRec.value.length > 100) {
    showError(message, 'Displaying too many packages freezes the browser. Working on a fix.')
    return
  }
  showRecommendations.value = !showRecommendations.value
}

const showAlerts = ref(false)
// function toggleShowAlerts() {
  // if (!showAlerts.value && !packageAlert) {
  //   showError(message, 'Displaying too many packages freezes the browser. Working on a fix.')
  //   return
  // }
  // showAlerts.value = !showAlerts.value
// }

function init() {
  fetchPackageDependencies()
  fetchPackageDependents()
  fetchPackageInfo() // fetchPackageRec is called inside fetchPackageInfo after getting repo_url
  fetchPackageAlers()
  fetchPackageTransitiveDependencies()
  
  showDependencies.value = false
  showDependents.value = false
  showRecommendations.value = false
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
            <a
              :href="packageInfo ? packageInfo.homepage_url : ''" class="w-full flex justify-center gap-0.5em"
              target="_blank"
            >
              <SvgIcon icon="tabler:external-link" class="position-relative top-3px" />
              {{ packageInfo ? packageInfo.homepage_url : '' }}
            </a>
          </template>
        </NCard>
      </NGridItem>

      <NGridItem span="0:24 640:24 1280:12" v-if="showAlerts">
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
            <!-- <AlertItem
              v-if="!packageAlert?.license_compatibility" type="warning" icon="ant-design:info-circle-filled"
              title="License Compatible"
            >
              <a href="https://licenserec.com" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span>
                LicenseRec</a>
              still not have detected this library.
            </AlertItem> -->
            <AlertItem
              v-if="packageAlert?.license_compatibility === 0" type="success"
              icon="ant-design:check-circle-filled" title="License Compatible"
            >
              <a href="https://licenserec.com" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span>
                LicenseRec</a>
              did not find any license compatibility issues.
            </AlertItem>
            <AlertItem
              v-else-if="packageAlert?.license_compatibility === 1" type="error"
              icon="ant-design:close-circle-filled" title="License Compatible"
            >
              <a href="https://licenserec.com" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span>
                LicenseRec</a>
              discovered license compatibility issues.
            </AlertItem>
            <!-- <AlertItem
              v-else-if="packageAlert?.license_compatibility === 2" type="warning"
              icon="ant-design:book-filled" title="License Compatible"
            >
              <a href="https://licenserec.com" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span>
                LicenseRec</a>
              don't support checking the compatibility of this license.
            </AlertItem> -->
            <AlertItem
              v-if="packageAlert?.is_archived" type="warning" icon="ant-design:book-filled"
              title="Repository Status"
            >
              Repository <a :href="packageAlert?.repo_url ? packageAlert?.repo_url : ''" target="_blank"> <span
                                                                                                            class="i-carbon-launch mr-1"
                                                                                                          > 1
                                                                                                          </span>
                {{ packageAlert?.name }}</a> is archived.
            </AlertItem>
            <AlertItem v-else type="success" icon="ant-design:book-filled" title="Repository Status">
              Repository <a :href="packageAlert?.repo_url ? packageAlert?.repo_url : ''" target="_blank"> <span
                                                                                                            class="i-carbon-launch mr-1"
                                                                                                          > 1
                                                                                                          </span>
                {{ packageAlert?.name }}</a> has not been archived.
            </AlertItem>
            <AlertItem
              v-if="packageAlert?.vulns.length" type="error" icon="ant-design:bug-filled"
              title="Vulnerabilities"
            >
              Package <a :href="packageAlert?.repo_url ? packageAlert?.repo_url : ''" target="_blank"> <span
                                                                                                         class="i-carbon-launch mr-1"
                                                                                                       > 1
                                                                                                       </span>
                {{ packageAlert?.name }} {{ packageAlert?.version }}</a> has {{ packageAlert?.vulns.length }}
              Vulnerabilities:
              <a v-for="(vuln, index) in packageAlert?.vulns" :key="vuln" :href="getCVEUrl(vuln)" target="_blank"> <span
                                                                                                                     class="i-carbon-launch mr-1"
                                                                                                                   >
                                                                                                                     1 </span> {{ vuln }}
                <span v-if="packageAlert?.vulns && index < packageAlert.vulns.length - 1">, </span>
              </a>
            </AlertItem>
            <AlertItem v-else type="success" icon="ant-design:bug-filled" title="Vulnerabilities">
              No Vulnerabilities.
            </AlertItem>
            <AlertItem type="primary" icon="fluent:people-team-48-filled" title="Many Contributors">
              Repository <a :href="packageAlert?.repo_url ? packageAlert?.repo_url : ''" target="_blank"> <span
                                                                                                            class="i-carbon-launch mr-1"
                                                                                                          > 1
                                                                                                          </span>
                {{ packageAlert?.name }}</a> has {{ packageAlert?.n_contributors }} contributors.
            </AlertItem>
          </div>
        </NCard>
      </NGridItem>
    </NGrid>

    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem :span="PKG_GRID_SPAN">
        <BigStatsCard
          :id="cardData.dependencies.id" :title="cardData.dependencies.title"
          :icon="cardData.dependencies.icon" :value="cardData.dependencies.value" :unit="cardData.dependencies.unit"
          :colors="cardData.dependencies.colors"
        />
      </NGridItem>
      <NGridItem
        v-for="v in (showDependencies || packageDependencies.length <= N_PKGS_DEFAULT + 1 ? packageDependencies : packageDependencies.slice(0, N_PKGS_DEFAULT))"
        :key="v.dep_purl" :span="PKG_GRID_SPAN"
      >
        <PackageCard :purl="v.dep_purl" :constraint="v.constraint" />
      </NGridItem>
      <NGridItem v-if="packageDependencies.length > N_PKGS_DEFAULT + 1" :span="PKG_GRID_SPAN">
        <ExpandMoreCard
          :show="showDependencies" :count="packageDependencies.length - N_PKGS_DEFAULT"
          @click="toggleShowDependencies"
        />
      </NGridItem>
    </NGrid>

    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem :span="PKG_GRID_SPAN">
        <BigStatsCard
          :id="cardData.dependents.id" :title="cardData.dependents.title" :icon="cardData.dependents.icon"
          :value="cardData.dependents.value" :unit="cardData.dependents.unit" :colors="cardData.dependents.colors"
        />
      </NGridItem>
      <NGridItem
        v-for="v in (showDependents ? packageDependents : packageDependents.slice(0, N_PKGS_DEFAULT))"
        :key="v.dep_purl" :span="PKG_GRID_SPAN"
      >
        <PackageCard :purl="v.purl" :constraint="v.constraint" />
      </NGridItem>
      <NGridItem v-if="packageDependents.length > N_PKGS_DEFAULT + 1" :span="PKG_GRID_SPAN">
        <ExpandMoreCard
          :show="showDependents" :count="packageDependents.length - N_PKGS_DEFAULT"
          @click="toggleShowDependents"
        />
      </NGridItem>
    </NGrid>

    <NGrid v-if="packageRec && packageRec.length > 0" :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem :span="PKG_GRID_SPAN">
        <BigStatsCard
          :id="cardData.recommendations.id" 
          :title="cardData.recommendations.title" 
          :icon="cardData.recommendations.icon"
          :value="cardData.recommendations.value" 
          :unit="cardData.recommendations.unit" 
          :colors="cardData.recommendations.colors"
        />
      </NGridItem>
      <NGridItem
        v-for="pkg in (showRecommendations ? packageRec : packageRec.slice(0, N_PKGS_DEFAULT))"
        :key="pkg.purl" 
        :span="PKG_GRID_SPAN"
      >
        <PackageCard :purl="pkg.purl" :constraint="pkg.description"/>
      </NGridItem>
      <NGridItem v-if="packageRec.length > N_PKGS_DEFAULT + 1" :span="PKG_GRID_SPAN">
        <ExpandMoreCard
          :show="showRecommendations" 
          :count="packageRec.length - N_PKGS_DEFAULT"
          @click="toggleShowRecommendations"
        />
      </NGridItem>
    </NGrid>

    <DependencyView :deps="packageTransitiveDependencies.concat(packageDependents)" />

  </div>
</template>

<style scoped>
.package-container {
  display: flex;
  flex-direction: column;
  /* align-items: center;  Removed this to allow Grid to take full width properly if needed, usually better for grids */
  justify-content: center;
  gap: 16px;
}
/* ... other styles */
</style>