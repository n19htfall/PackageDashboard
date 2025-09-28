<script setup lang="ts">
import type { Ref } from 'vue'
import { ref } from 'vue'
import {
  NButton,
  NCard,
  NDivider,
  NEllipsis,
  NGrid,
  NGridItem,
  NInput,
  NInputGroup,
  NSpace,
  NTag,
  useMessage,
} from 'naive-ui'

import { PackageURL } from 'packageurl-js'

const props = defineProps<{
  purl: string
  constraint?: string
}>()
const pUrlObj = computed(() => {
  try {
    const res = PackageURL.fromString(props.purl)
    return res
  }
  catch (e) {
    return PackageURL.fromString(decodeURIComponent(props.purl))
  }
})
// const pkgUrl = computed(() => `/pkg?purl=${encodeURIComponent(props.purl)}`)
const pkgUrl = computed(() => `/pkg?purl=${props.purl}`)
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
  <RouterLink :to="pkgUrl" :title="pUrlObj.name" class="h-full w-full">
    <NCard :bordered="false" class="package-card rounded-10px shadow-sm">
      <template #header>
        <NEllipsis>
          {{ pUrlObj.name }}
        </NEllipsis>
      </template>
      <template #header-extra>
        <SvgIcon :icon="iconName" class="text-xl" />
      </template>
      <div>
        <NEllipsis>
          {{ pUrlObj.version }}
        </NEllipsis>
      </div>
      <template #footer>
        <NTag type="success" size="small" round class="mr-2">
          {{ pUrlObj.type }}
        </NTag>
        <NTag v-if="pUrlObj.qualifiers?.arch" type="warning" size="small" round class="mr-2">
          {{ pUrlObj.qualifiers.arch }}
        </NTag>
        <NTag v-if="pUrlObj.qualifiers?.distro" type="info" size="small" round class="mr-2">
          {{ pUrlObj.qualifiers.distro }}
        </NTag>
      </template>
      <template v-if="props.constraint" #action>
        <NEllipsis> {{ props.constraint }} </NEllipsis>
      </template>
    </NCard>
  </RouterLink>
</template>

<style scoped>
.package-card .n-card__content,
.n_card__footer,
.n_card__action {
  padding-bottom: 20px !important;
  padding-top: 20px !important;
}
</style>
