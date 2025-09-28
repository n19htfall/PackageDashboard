<script setup lang="ts">
import type { NumberAnimationInst } from 'naive-ui'
import { NNumberAnimation, NStatistic } from 'naive-ui'
import SvgIcon from '~/components/SvgIcon.vue'

export interface StatsCardProps {
  id?: string
  title: string
  value: Ref<number>
  unit: string
  colors: [string, string]
  icon: string
}

const props = defineProps<StatsCardProps>()
const numberAnimationInstRef = ref<NumberAnimationInst | null>(null)
</script>

<template>
  <GradientBg class="h-max" :start-color="props.colors[0]" :end-color="props.colors[1]">
    <h3 class="text-stroke-custom text-20px font-500">
      {{ title }}
    </h3>
    <div class="flex items-center justify-between text-30px">
      <SvgIcon :icon="icon" class="mt-2 text-32px" />
      <NNumberAnimation
        ref="numberAnimationInstRef"
        show-separator
        :from="0"
        :to="props.value.value"
        :precision="props.value.value % 1 !== 0 ? 3 : 0"
      />
    </div>
  </GradientBg>
</template>
