<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** start of the gradient color */
  startColor?: string
  /** end of the gradient color */
  endColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  startColor: '#56cdf3',
  endColor: '#719de3',
})

const gradientStyle = computed(() => `linear-gradient(to bottom right, ${props.startColor}, ${props.endColor})`)
</script>

<template>
  <div class="rounded-8px p-16px text-white" :style="{ backgroundImage: gradientStyle }">
    <slot />
  </div>
</template>

<style scoped></style>
