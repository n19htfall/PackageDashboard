<script setup lang="ts">
import type { NumberAnimationInst } from 'naive-ui'
import { NNumberAnimation, NStatistic } from 'naive-ui'
import SvgIcon from '~/components/SvgIcon.vue'

export interface StatsCardProps {
  title: string
  value: Ref<number>
  colors: [string, string]
  icon: string
}

const props = defineProps<StatsCardProps>()
const numberAnimationInstRef = ref<NumberAnimationInst | null>(null)
</script>

<template>
  <GradientBg class="big-stats-card" :start-color="props.colors[0]" :end-color="props.colors[1]">
    <h3 class="text-stroke-custom text-32px">
      {{ title }}
    </h3>
    <div class="w-100% flex items-center justify-between text-48px">
      <SvgIcon :icon="icon" class="mt-2 text-50px" />
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

<style scoped>
.big-stats-card {
  height: 100%;
  width: 100%;
  padding: 20px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  min-height: 215px;
}
</style>
