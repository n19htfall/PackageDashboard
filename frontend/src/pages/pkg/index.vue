<script setup lang="ts">
import {
  NDivider,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { getPackageSources } from '~/api/package'
import PackageView from '~/components/PackageView.vue'
import RepositoryView from '~/components/RepositoryView.vue'

const route = useRoute()
const pUrl = computed(() => route.query.purl ? route.query.purl : 'pkg::rpm/openeuler/Bear@3.0.20-3.oe2203sp1?arch=src&epoch=0&distro=openeuler-2203sp1')
const { isLoading, startLoading, finishLoading, errorLoading } = useLoading()
const message = useMessage()

const packageSources: Ref<Array<PackageSource>> = ref([])
const showRepoTab = computed(() => packageSources.value.length > 0)
const selectedTab = ref('')

function setSelectTab(tab: string) {
  console.log('setSelectTab', tab)
  selectedTab.value = tab
}

async function fetchPackageSources() {
  packageSources.value = []
  startLoading()
  try {
    packageSources.value = await getPackageSources(pUrl.value as string)
    finishLoading()
  }
  catch (e) {
    errorLoading()
    showError(message, e as Error)
  }

  // set the first tab as selected
  if (packageSources.value.length > 0) {
    selectedTab.value = packageSources.value[0].repo_url
  }
}
fetchPackageSources()
watch(() => pUrl.value, () => {
  fetchPackageSources()
})

function getDisplayName(url: string) {
  // remove http:// or https://
  const _url = url.replace(/^(http|https):\/\//, '')
  const _splited = _url.split('/')
  return _splited.slice(1).join(' / ')
}
</script>

<template>
  <div class="page-container flex">
    <div class="left-container">
      <PackageView :purl="pUrl" />
    </div>
    <div v-if="showRepoTab" class="right-container">
      <NTabs
        type="line"
        animated
        :value="selectedTab"
        :on-update:value="setSelectTab"
      >
        <NTabPane
          v-for="item in packageSources"
          :key="item.repo_url"
          display="show:lazy"
          :name="item.repo_url"
        >
          <template #tab>
            {{ getDisplayName(item.repo_url) }}
            <NTag round size="small" :bordered="false" class="ml-1.5" type="success">
              <!-- round item.confidence to .2f -->
              {{ item.confidence ? item.confidence.toFixed(2) : "1.00" }}
            </NTag>
          </template>
          <RepositoryView :url="item.repo_url" class="mt-2" />
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
