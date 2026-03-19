<script setup lang="ts">
import { NCollapseTransition, NSpace, NSwitch } from 'naive-ui'

const props = defineProps<{ name: string }>()
const router = useRouter()
const user = useUserStore()
const i18n = useI18n({ useScope: 'global' })

watchEffect(() => {
  user.setNewName(props.name)
})

const show = ref(false)
</script>

<template>
  <div>
    <div text-4xl>
      <div i-carbon-pedestrian inline-block />
    </div>
    <p>
      {{ i18n.t('intro.hi', { name: props.name }) }}
    </p>

    <p text-sm opacity-75>
      <em>{{ i18n.t('intro.dynamic-route') }}</em>
    </p>

    <template v-if="user.otherNames.length">
      <p mt-4 text-sm>
        <span opacity-75>{{ i18n.t('intro.aka') }}:</span>
        <ul>
          <li v-for="otherName in user.otherNames" :key="otherName">
            <RouterLink :to="`/hi/${otherName}`" replace>
              {{ otherName }}
            </RouterLink>
          </li>
        </ul>
      </p>
    </template>

    <div>
      <button
        m="3 t6" text-sm btn
        @click="router.back()"
      >
        {{ i18n.t('button.back') }}
      </button>
    </div>
  </div>

  <Graph />
</template>
