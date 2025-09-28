<script setup lang="ts">
import type { Data, Options } from 'vis-network'
import { Network } from 'vis-network'

interface ModuleInfo {
  id: string
  plugins: { name: string; transform?: number; resolveId?: number }[]
  deps: string[]
  virtual: boolean
  totalTime: number
}

interface PackageInfo {
  /** parseable PURL e.g. pkg:rpm/xxx/yyy? */
  purl: string
  /** normalized (0, 1] weight */
  weight: number
  /** dependencies */
  deps: string[]
  virtual: boolean
}

const props = defineProps<{
  modules?: ModuleInfo[]
}>()

const modules = [
  {
    id: 'A-FOT',
    plugins: { name: '1' },
    deps: [
      'Bear 3.0.20',
      'autofdo 0.19',
      'llvm-bolt 0',
      'gcc 10.3.1',
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'autofdo 0.19',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'llvm-bolt 0',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'gcc 10.3.1',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'Bear 3.0.20',
    plugins: { name: '1' },
    deps: [
      'glibc 2.3.4',
      'libgcc 10.3.1',
      'libstdc++ 10.3.1',
      'zlib 1.2.11',
      're2 20211101',
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'glibc 2.3.4',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'libgcc 10.3.1',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'libstdc++ 10.3.1',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 'zlib 1.2.11',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },
  {
    id: 're2 20211101',
    plugins: { name: '1' },
    deps: [
    ],
    virtual: false,
    totalTime: 0.000000,
  },

]

const isDark = useDark()

const graphWeightMode = 'deps'

function getModuleWeight(mod: ModuleInfo, mode: 'deps' | 'transform' | 'resolveId') {
  const value = 10 + (mode === 'deps' ? Math.min(mod.deps.length, 30) : Math.min(mod.plugins.reduce((total, plg) => total + (plg[mode as 'transform' | 'resolveId'] || 0), 0) / 20, 30))
  return value
}

const colors = Object.entries({
  vue: '#42b883',
  ts: '#41b1e0',
  js: '#d6cb2d',
  json: '#cf8f30',
  css: '#e6659a',
  html: '#e34c26',
  svelte: '#ff3e00',
  jsx: '#7d6fe8',
  tsx: '#7d6fe8',
}).map(([type, color]) => ({ type, color }))

const container = ref<HTMLDivElement | null>()
const weightItems = [
  { value: 'deps', label: 'dependency count' },
  { value: 'transform', label: 'transform time' },
  { value: 'resolveId', label: 'resolveId time' },
]

const shapes = [
  { type: 'source', icon: 'i-ic-outline-circle' },
  { type: 'virtual', icon: 'i-ic-outline-square rotate-45 scale-85' },
  { type: 'node_modules', icon: 'i-ic-outline-hexagon' },
]
const router = useRouter()

const data = computed<Data>(() => {
  const nodes: Data['nodes'] = modules.map((mod) => {
    const path = mod.id.replace(/\?.*$/, '').replace(/\#.*$/, '')
    return {
      id: mod.id,
      label: path.split('/').splice(-1)[0],
      group: 'vue',
      size: getModuleWeight(mod, graphWeightMode),
      font: { color: isDark.value ? 'white' : 'black' },
      shape: mod.id.includes('lib')
        ? 'hexagon'
        : mod.virtual
          ? 'diamond'
          : 'dot',
    }
  })
  const edges: Data['edges'] = modules.flatMap(mod => mod.deps.map(dep => ({
    from: mod.id,
    to: dep,
    arrows: {
      to: {
        enabled: true,
        scaleFactor: 0.8,
      },
    },
  })))

  return {
    nodes,
    edges,
  }
})

onMounted(() => {
  const options: Options = {
    nodes: {
      shape: 'dot',
      size: 16,
    },
    physics: {
      maxVelocity: 146,
      solver: 'forceAtlas2Based',
      timestep: 0.35,
      stabilization: {
        enabled: true,
        iterations: 200,
      },
    },
    groups: colors.reduce((groups, color) => ({ ...groups, [color.type]: { color: color.color } }), {}),
  }
  const network = new Network(container.value!, data.value, options)

  const clicking = ref(false)

  network.on('click', () => {
    clicking.value = true
  })

  network.on('hold', () => {
    clicking.value = false
  })

  network.on('dragStart', () => {
    clicking.value = false
  })

  network.on('release', (data) => {
    const node = data.nodes?.[0]
    if (clicking.value && node) {
      router.push(`/module?id=${encodeURIComponent(node)}`)
      clicking.value = false
    }
  })

  watch(data, () => {
    network.setData(data.value)
  })
})
</script>

<template>
  <div v-if="modules">
    <div ref="container" h-100vh w-full />
    <div
      border="~ main"
      flex="~ col"

      bg-main absolute bottom-3 right-3 w-38 select-none rounded bg-opacity-75 p3 text-sm shadow backdrop-blur-8
    >
      <div
        v-for="color of colors" :key="color.type"
        flex="~ gap-2 items-center"
      >
        <div h-3 w-3 rounded-full :style="{ backgroundColor: color.color }" />
        <div>
          {{ color.type }}
        </div>
      </div>
      <div border="t base" my3 h-1px />
      <div
        v-for="shape of shapes" :key="shape.type"
        flex="~ gap-2 items-center"
      >
        <div :class="shape.icon" flex-none />
        <div>
          {{ shape.type }}
        </div>
      </div>
    </div>
    <div
      border="~ main"
      bg-main absolute bottom-3 left-3 rounded bg-opacity-75 p3 text-sm shadow backdrop-blur-8
      flex="~ col gap-1"
    >
      <span text-sm op50>weight by</span>
      <RadioGroup
        v-model="graphWeightMode"
        flex-col text-sm
        name="weight"
        :options="weightItems"
      />
    </div>
  </div>
</template>
