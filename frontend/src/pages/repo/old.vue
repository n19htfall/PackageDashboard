<script setup lang="ts">
import type { Ref } from 'vue'
import { ref } from 'vue'
import {
  NButton,
  NCard,
  NDivider,
  NEllipsis,
  NGradientText,
  NGrid,
  NGridItem,
  NInput,
  NInputGroup,
  NSpace,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  Icon,
} from '@iconify/vue'

import type { StatsCardProps } from '~/components/StatsCard.vue'
import StatsCard from '~/components/StatsCard.vue'
import BarChartCard from '~/components/BarChartCard.vue'

import { getRepositoryInfo, getRepositoryStats } from '~/api/repository'
import { useLoading } from '~/composables/loading'
import { showError } from '~/composables/error'

const { isLoading, startLoading, finishLoading, errorLoading } = useLoading()
const message = useMessage()

const defaultEmptyMsg = '...'

const route = useRoute()
const repoUrl = computed(() => route.query.url as string || 'https://github.com/rizsotto/Bear')
watch(repoUrl, () => init())

enum StatsItems {
  Commit = 'commits',
  Comment = 'comments',
  Issue = 'issues',
  PR = 'prs',
  Star = 'stars',
  Tag = 'tags',
  Hits = 'hits',
  HitsRankPCT = 'hitsRankPCT',
  HitsZScore = 'hitsZScore',
}

const chartNames: { [key in StatsItems]: string } = {
  commits: 'Number of Commits',
  comments: 'Number of Comments',
  issues: 'Number of Issues',
  prs: 'Number of Pull Requests',
  stars: 'Number of Stars',
  tags: 'Number of Tags',
  hits: 'Hits Score',
  hitsRankPCT: 'Hits Percentile',
  hitsZScore: 'Hits ZScore',
}

// constData should be <key from dataorder: StatsCardProps>
const cardData: { [key in StatsItems]: StatsCardProps } = {
  commits: {
    title: 'Commits',
    value: ref(0),
    unit: '',
    colors: ['#ec4786', '#b955a4'],
    icon: 'ph:git-commit',
  },
  comments: {
    title: 'Comments',
    value: ref(0),
    unit: '',
    colors: ['#865ec0', '#5144b4'],
    icon: 'prime:comments',
  },
  issues: {
    id: 'issues',
    title: 'Issues',
    value: ref(0),
    unit: '',
    colors: ['#56cdf3', '#719de3'],
    icon: 'codicon:issues',
  },
  prs: {
    id: 'prs',
    title: 'Pull Requests',
    value: ref(0),
    unit: '',
    colors: ['#fcbc25', '#f68057'],
    icon: 'ph:git-pull-request',
  },
  stars: {
    id: 'stars',
    title: 'Stars',
    value: ref(0),
    unit: '',
    colors: ['#78ff78', '#78ffd6'],
    icon: 'solar:stars-outline',
  },
  tags: {
    id: 'tags',
    title: 'Tags',
    value: ref(0),
    unit: '',
    colors: ['#654ea3', '#eaafc8'],
    icon: 'material-symbols:bookmark-added-outline',
  },
  hits: {
    id: 'hits',
    title: 'Hits',
    value: ref(0),
    unit: '',
    colors: ['#7F7FD5', '#86A8E7'],
    icon: 'ant-design:bar-chart-outlined',
  },
  hitsRankPCT: {
    id: 'hitsRankPCT',
    title: 'Hits Percentile',
    value: ref(0),
    unit: '',
    colors: ['#A8F9FF', '#7BB2D9'],
    icon: 'ant-design:bar-chart-outlined',
  },
  hitsZScore: {
    id: 'hitsZScore',
    title: 'Hits ZScore',
    value: ref(0),
    unit: '',
    colors: ['#568259', '#96E6B3'],
    icon: 'ant-design:bar-chart-outlined',
  },
}

const barData: { [key in StatsItems]: Ref<Array<number>> } = {
  commits: ref([]),
  comments: ref([]),
  issues: ref([]),
  prs: ref([]),
  stars: ref([]),
  tags: ref([]),
  hits: ref([]),
  hitsRankPCT: ref([]),
  hitsZScore: ref([]),
}

const barAxis: Ref<Array<string>> = ref([])

const repositoryInfo = ref<Repository | null>(null)

/**
 * Fetches and Updates the repository information
 * Don't chain promises, it will cause the waterfall effect
 * */
async function fetchRepositoryInfo() {
  startLoading()
  try {
    repositoryInfo.value = await getRepositoryInfo(repoUrl.value)
    finishLoading()
  }
  catch (e) {
    repositoryInfo.value = null
    errorLoading()
    showError(message, e as Error)
  }
}

async function fetchRepositoryStats() {
  let repositoryStats: RepositoryStats[] = []
  startLoading()
  try {
    repositoryStats = await getRepositoryStats(repoUrl.value)
    finishLoading()
  }
  catch (e) {
    repositoryStats = []
    errorLoading()
    showError(message, e as Error)
  }

  if (!repositoryStats) {
    return
  }

  const dates = []
  const stats: Record<StatsItems, Array<number>> = {
    commits: [],
    comments: [],
    issues: [],
    prs: [],
    stars: [],
    tags: [],
    hits: [],
    hitsRankPCT: [],
    hitsZScore: [],
  }

  repositoryStats.sort((a, b) => {
    return new Date(a.stats_from).getTime() - new Date(b.stats_from).getTime()
  })

  for (const statsRecord of repositoryStats) {
    dates.push(new Date(statsRecord.stats_from).toLocaleDateString())
    stats.commits.push(statsRecord.n_commits)
    stats.comments.push(statsRecord.n_comments)
    stats.issues.push(statsRecord.n_issues)
    stats.prs.push(statsRecord.n_prs)
    stats.stars.push(statsRecord.n_stars)
    stats.tags.push(statsRecord.n_tags)
    stats.hits.push(statsRecord.hits ?? 0)
    stats.hitsRankPCT.push(statsRecord.hits_rank_pct ?? 0)
    stats.hitsZScore.push(statsRecord.hits_zscore ?? 0)
  }

  // sum up the data
  cardData.commits.value.value = stats.commits.reduce((a, b) => a + b, 0)
  cardData.comments.value.value = stats.comments.reduce((a, b) => a + b, 0)
  cardData.issues.value.value = stats.issues.reduce((a, b) => a + b, 0)
  cardData.prs.value.value = stats.prs.reduce((a, b) => a + b, 0)
  cardData.stars.value.value = stats.stars.reduce((a, b) => a + b, 0)
  cardData.tags.value.value = stats.tags.reduce((a, b) => a + b, 0)
  // last val that is not 0
  cardData.hits.value.value = stats.hits.reduce((a, b) => b > 0 ? b : a, 0)
  cardData.hitsRankPCT.value.value = stats.hitsRankPCT.reduce((a, b) => b > 0 ? b : a, 0)
  cardData.hitsZScore.value.value = stats.hitsZScore.reduce((a, b) => b > 0 ? b : a, 0)

  // update the figures
  for (const key in barData) {
    const _key = key as StatsItems
    barData[_key].value = stats[_key]
  }
  barAxis.value = dates
}

function init() {
  fetchRepositoryStats()
  fetchRepositoryInfo()
}
init()
</script>

<template>
  <div class="page-container">
    <NGrid :x-gap="16" :y-gap="16" :item-responsive="true">
      <NGridItem span="0:24 640:24 1280:10">
        <NCard :bordered="false" class="h-full rounded-10px shadow-sm">
          <template #header>
            <NGradientText class="text-30px" type="info">
              {{ repositoryInfo ? repositoryInfo.name.split(/\//).join(' / ') : defaultEmptyMsg }}
            </NGradientText>
          </template>

          <template #header-extra>
            <SvgIcon icon="ion:logo-github" class="text-30px" />
          </template>

          <div class="flex flex-col items-baseline justify-center">
            <h3 class="mb--5 text-16px font-bold">
              Repository Information
            </h3>
            <NDivider />
            <NEllipsis class="mt--2 text-#aaa" :line-clamp="3">
              {{ repositoryInfo ? repositoryInfo.description : defaultEmptyMsg }}
            </NEllipsis>
            <NEllipsis class="text-#aaa">
              Created at:
              {{ repositoryInfo ? new Date(repositoryInfo.created_at).toLocaleString() : defaultEmptyMsg }}
            </NEllipsis>
            <NEllipsis class="text-#aaa">
              Last Updated at:
              {{ repositoryInfo ? new Date(repositoryInfo.updated_at).toLocaleString() : defaultEmptyMsg }}
            </NEllipsis>
            <NEllipsis v-if="repositoryInfo && repositoryInfo.archived_at" class="text-#aaa">
              Archived at:
              {{
                repositoryInfo?.archived_at ? new Date(repositoryInfo.archived_at).toLocaleString() : defaultEmptyMsg
              }}
            </NEllipsis>

            <div v-if="repositoryInfo" class="mt-4 flex gap-12px">
              <NTag type="success" round>
                <div class="flex gap-0.5em">
                  <SvgIcon icon="streamline:programming-script-code-code-angle-programming-file-bracket" />
                  {{ repositoryInfo.primary_language ? repositoryInfo.primary_language : defaultEmptyMsg }}
                </div>
              </NTag>
              <NTag type="error" round>
                <div class="flex gap-0.3em">
                  <SvgIcon icon="tabler:license" />
                  {{ repositoryInfo.license }}
                </div>
              </NTag>
            </div>
          </div>

          <template #footer>
            <h3 class="mb--5 text-16px font-bold">
              Repository Alerts
            </h3>
            <NDivider />
            <div class="gap flex flex-col items-baseline gap-0.5em">
              <AlertItem type="success" icon="ant-design:check-circle-filled" title="License Compatible">
                LicenseRec
                did not find any license compatibility issues.
              </AlertItem>
              <AlertItem type="warning" icon="ant-design:book-filled" title="Repository Archived">
                Repository atom is archived.
              </AlertItem>
              <AlertItem type="error" icon="ant-design:bug-filled" title="Vulnerabilities">
                <a href="https://www.cvedetails.com/cve/CVE-2017-1000424/" target="_blank"> <span class="i-carbon-launch mr-1"> 1 </span> CVE-2017-1000424 </a> (Medium).
              </AlertItem>
              <AlertItem type="primary" icon="fluent:people-team-48-filled" title="Many Contributors">
                Repository  atom has 495 contributors.
              </AlertItem>
            </div>
          </template>

          <template #action>
            <a :href="repositoryInfo ? repositoryInfo.url : ''" class="w-full flex justify-center gap-0.5em" target="_blank">
              <SvgIcon icon="tabler:external-link" class="position-relative top-3px" />
              {{ repositoryInfo ? repositoryInfo.url : '' }}
            </a>
          </template>
        </NCard>
      </NGridItem>

      <NGridItem span="0:24 640:24 1280:14">
        <NCard :bordered="false" class="h-full rounded-8px shadow-sm">
          <div class="h-max w-full py-12px pt-5">
            <h3 class="mb--5 mt--5 text-16px font-bold">
              Cumulative Statistics
            </h3>
            <NDivider />
            <NGrid x-gap="16" y-gap="16" item-responsive>
              <NGridItem v-for="item in cardData" :key="item.id" span="0:24 480:12 640:8 960:6 1280:4 1920:3">
                <StatsCard
                  :id="item.id"
                  :title="item.title"
                  :icon="item.icon"
                  :value="item.value"
                  :unit="item.unit"
                  :colors="item.colors"
                />
              </NGridItem>
            </NGrid>
          </div>
        </NCard>
      </NGridItem>
      <NGridItem v-for="(v, k) in barData" :key="k" span="0:24 640:12 960:8 1280:6">
        <!-- @vue-ignore should be ts's fault: ref<number[]> should be compatible with number[] -->
        <BarChartCard :data="v" :axis="barAxis" :title="chartNames[k]" />
      </NGridItem>
    </NGrid>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 20px;
  gap: 8px;
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
