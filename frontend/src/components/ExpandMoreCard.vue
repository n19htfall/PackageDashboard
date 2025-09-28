<script setup lang="ts">
import {
  NCard,
  NEllipsis,
  NTag,
} from 'naive-ui'

const props = defineProps<{
  show: boolean
  count?: number
}>()
const emit = defineEmits<{
  (e: 'click'): void
}>()
function toggleExpand() {
  emit('click')
}
</script>

<template>
  <NCard
    :bordered="false" title="" class="expand-more-card border-rounded-10px" @click="toggleExpand()"
  >
    <div class="h-full w-full flex items-center justify-center text-2xl">
      {{ show ? 'Less' : $props.count ? `${count}  More` : 'More' }}
    </div>

    <template #action>
      <div class="w-full flex items-center justify-center text-xl">
        <SvgIcon :icon="show ? 'material-symbols:expand-circle-up' : 'material-symbols:expand-circle-down'" />
      </div>
    </template>
  </NCard>
</template>

<style scoped>
.expand-more-card {
  height: 100%;
  width: 100%;
  border-radius: 10px;
  cursor: pointer;
}

.expand-more-card * {
  user-select: none;
  transition: all 0.3s ease-in-out;
}
</style>
