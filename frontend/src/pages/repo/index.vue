<script setup lang="ts">
import {
  NDivider,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  useThemeVars,
} from 'naive-ui'
import { PackageURL } from 'packageurl-js'
import { getRepositoryPackages } from '~/api/repository'

import PackageView from '~/components/PackageView.vue'
import RepositoryView from '~/components/RepositoryView.vue'

const themeVars = useThemeVars()
const route = useRoute()
const rUrl = computed(() => route.query.url ? route.query.url : 'https://github.com/go-delve/delve')

const { isLoading, startLoading, finishLoading, errorLoading } = useLoading()
const message = useMessage()

const repositoryPackages: Ref<Array<PackageSource>> = ref([])
const selectedTab = ref('')
function setSelectTab(tab: string) {
  console.log('setSelectTab', tab)
  selectedTab.value = tab
}

async function fetchRepositoryPackages() {
  repositoryPackages.value = []
  startLoading()
  try {
    repositoryPackages.value = await getRepositoryPackages(rUrl.value as string)
    finishLoading()
  }
  catch (e) {
    errorLoading()
    showError(message, e as Error)
  }

  // set the first tab as selected
  if (repositoryPackages.value.length > 0) {
    selectedTab.value = repositoryPackages.value[0].purl
  }
}
fetchRepositoryPackages()
watch(() => rUrl.value, () => {
  fetchRepositoryPackages()
})

function getDisplayName(url: string) {
  // remove http:// or https://
  const purl = PackageURL.fromString(url)
  return `${purl.name}@${purl.version}`
}

function getDependencyType(url: string) {
// remove http:// or https://
  const purl = PackageURL.fromString(url)
  return purl.qualifiers?.arch ? purl.qualifiers.arch : purl.type
}
</script>

<template>
  <div class="page-container flex">
    <div class="left-container">
      <RepositoryView :url="rUrl" />
    </div>
    <div class="right-container">
      <NTabs
        type="line"
        animated
        :value="selectedTab"
        :on-update:value="setSelectTab"
      >
        <!-- <template #prefix>
          {{ repositoryPackages.length }}
        </template> -->
        <NTabPane
          v-for="item in repositoryPackages"
          :key="item.purl"
          display="show:lazy"
          :name="item.purl"
        >
          <template #tab>
            {{ getDisplayName(item.purl) }}
            <NTag round size="small" :bordered="false" class="ml-1.5" type="success">
              {{ getDependencyType(item.purl) }}
            </NTag>
          </template>
          <PackageView :purl="item.purl" class="mt-2" />
        </NTabPane>
      </NTabs>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
}

.left-container {
  min-width: 50%;
  padding: 12px;
}

.right-container {
  min-width: 50%;
  padding: 12px;
}

.repo-prec-tag {
  background-color: rgba(99, 226, 183, 0.3);
  border-radius: 0.25em;
  margin-left: 0.5em;
  padding-left: 0.25em;
  padding-right: 0.25em;
}

@media screen and (max-width: 1000px) {
  .page-container {
    flex-direction: column;
  }

  .left-container {
    min-width: 100%;
  }

  .right-container {
    min-width: 100%;
  }

}
</style>

<route lang="yaml">
meta:
  layout: default
    </route>
