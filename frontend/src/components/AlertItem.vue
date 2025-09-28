<script setup lang="ts">
import { NEllipsis, NTag } from 'naive-ui'
import SvgIcon from '~/components/SvgIcon.vue'

const props = defineProps<{
  title: string
  type: 'default' | 'error' | 'primary' | 'info' | 'success' | 'warning'
  icon: string
}>()
</script>

<template>
  <div class="w-full flex items-center gap-0.5em">
    <NTag round :bordered="false" :type="props.type">
      {{ props.title }}
      <template #icon>
        <SvgIcon :icon="props.icon" class="pl-2px" />
      </template>
    </NTag>
    <NEllipsis class="text-#777">
      <slot>
        No messages inside slot!
      </slot>
    </NEllipsis>
  </div>
</template>
