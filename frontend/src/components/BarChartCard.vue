<script setup lang="ts">
import { NCard } from 'naive-ui'
import VChart from 'vue-echarts'
import { type ECOption, useEcharts } from '~/composables/echarts'

const props = defineProps<{
  title: string
  axis: Array<string>
  data: Ref<Array<number>>
}>()

const optionsRef: Ref<ECOption> = ref({})
const chartRef = useEcharts(optionsRef).domRef
updateBarChartOptions(optionsRef, {
  chartAxis: props.axis,
  chartData: props.data.value,
  chartName: props.title,
})
watch([
  () => props.axis,
  () => props.data,
], () => {
  updateBarChartOptions(
    optionsRef,
    {
      chartAxis: props.axis,
      chartData: props.data.value,
      chartName: props.title,
    },
  )
})
</script>

<template>
  <NCard :bordered="false" class="rounded-10px shadow-sm">
    <h3 class="mb--35px text-16px font-bold">
      {{ props.title }}
    </h3>
    <VChart :ref="chartRef" :option="optionsRef" autoresize class="h-250px w-full" />
  </NCard>
</template>
