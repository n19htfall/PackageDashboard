<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-invalid-this */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

// Import watch and computed, nextTick
import * as d3 from 'd3'
import type { D3DragEvent, Simulation, SimulationLinkDatum, SimulationNodeDatum } from 'd3'

// Assuming PackageURL is imported/available globally or imported correctly
// import { PackageURL } from 'packageurl-js'; // Make sure this is imported if used

// Import debounce (install lodash-es if you haven't: npm install lodash-es @types/lodash-es)
import { debounce } from 'lodash-es'

// --- Interfaces (keep as they are) ---
interface NodeData extends SimulationNodeDatum {
  id: string // PURL
  name: string // Display name (e.g., core@7.1.1)
  type: 'package'
  width?: number
  height?: number
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

interface LinkData extends SimulationLinkDatum<NodeData> {
  source: string | NodeData
  target: string | NodeData
  constraint: string
  type: 'depends'
}

// --- FAKE PackageDependency for standalone testing ---
// Remove this if PackageDependency is globally defined or imported
interface PackageDependency {
  purl: string
  dep_purl: string
  constraint?: string
}
// --- Props ---
const props = defineProps<{
  deps: PackageDependency[] | null | undefined
}>()
// --- FAKE PackageURL for standalone testing ---
// Remove this if PackageURL is globally defined or imported
declare class PackageURL {
  name: string
  version?: string
  static fromString(purl: string): PackageURL
}
// Example fallback implementation for testing if needed
if (typeof PackageURL === 'undefined') {
  (globalThis as any).PackageURL = class {
    name = 'unknown'
    version?: string
    constructor(purl: string) {
      const parts = purl?.replace(/^pkg:/, '').split(/[@?#]/)[0]?.split('/')
      this.name = parts?.[parts.length - 1] || 'unknown'
      const versionMatch = purl?.match(/@([^?#]+)/)
      this.version = versionMatch?.[1]
    }

    static fromString(purl: string): PackageURL {
      return new PackageURL(purl)
    }
  }
}

// --- Refs and Variables ---
const svgRef = ref<SVGSVGElement | null>(null)
const graphContainerRef = ref<HTMLDivElement | null>(null) // Ref for the main container
let simulation: Simulation<NodeData, LinkData> | null = null
let resizeObserver: ResizeObserver | null = null // Variable for the observer instance

const nodePadding = { x: 10, y: 5 }
const isFullscreen = ref(false) // State to track fullscreen status

// --- Utility Functions ---
function parsePurlGetNameVersion(purl: string): string {
  // Keep your existing parsePurlGetNameVersion function
  if (!purl) {
    return 'unknown'
  }
  try {
    const purlObject = PackageURL.fromString(purl)
    const name = purlObject.name
    const version = purlObject.version
    if (!name) {
      console.warn(`Could not extract name from PURL: ${purl}`)
      const parts = purl.split('/')
      return parts[parts.length - 1] || purl
    }
    return version ? `${name}@${version}` : name
  }
  catch (e) {
    console.error(`Failed to parse PURL "${purl}" with packageurl-js:`, e)
    const parts = purl.split('/')
    const lastPart = parts[parts.length - 1]
    return (lastPart && !lastPart.includes(':')) ? lastPart : purl
  }
}

// --- Main Graph Drawing Function ---
function drawGraph() {
  // Check container ref existence as well
  if (!svgRef.value || !graphContainerRef.value) {
    console.log('SVG or Container ref not ready.')
    // Optionally clear SVG if it exists but container doesn't (edge case)
    if (svgRef.value)
      d3.select(svgRef.value).selectAll('*').remove()
    if (simulation)
      simulation.stop()
    simulation = null
    return
  }

  // --- Get Dimensions from Container ---
  const container = graphContainerRef.value
  // Use clientWidth/clientHeight for actual rendered size
  const width = container.clientWidth
  // Ensure height is reasonable, subtract space if info text is inside
  const availableHeight = container.clientHeight // Or adjust if needed
  const minHeight = 250
  const height = Math.max(minHeight, availableHeight > 50 ? availableHeight - 40 : availableHeight) // Subtract ~40px for potential button/info space

  const svgElement = svgRef.value

  // Stop previous simulation BEFORE clearing SVG might be slightly safer
  if (simulation) {
    simulation.stop()
    simulation = null // Clear ref
  }

  // --- Clear Previous Drawing ---
  d3.select(svgElement).selectAll('*').remove()

  // --- Check for Data ---
  if (!props.deps || props.deps.length === 0) {
    console.log('No dependencies data to draw.')
    // Optionally display a message in the SVG area
    svgElement.appendChild(
      Object.assign(document.createElementNS('http://www.w3.org/2000/svg', 'text'), {
        textContent: '没有可显示的依赖关系数据。',
        x: width / 2,
        y: 30, // Position near the top
        textAnchor: 'middle',
        fill: '#666',
        fontSize: '14px',
      }),
    )
    return
  }

  // --- Data Transformation (Keep as is) ---
  const nodesMap = new Map<string, NodeData>()
  const links: LinkData[] = []

  props.deps.forEach((dep) => {
    if (dep.purl && !nodesMap.has(dep.purl)) {
      nodesMap.set(dep.purl, {
        id: dep.purl,
        name: parsePurlGetNameVersion(dep.purl),
        type: 'package',
      })
    }
    if (dep.dep_purl && !nodesMap.has(dep.dep_purl)) {
      nodesMap.set(dep.dep_purl, {
        id: dep.dep_purl,
        name: parsePurlGetNameVersion(dep.dep_purl),
        type: 'package',
      })
    }
    if (dep.purl && dep.dep_purl) {
      links.push({
        source: dep.purl,
        target: dep.dep_purl,
        constraint: dep.constraint || '',
        type: 'depends',
      })
    }
    else {
      console.warn('Skipping link due to missing purl or dep_purl:', dep)
    }
  })

  const nodes = Array.from(nodesMap.values())

  if (nodes.length === 0) {
    console.log('No nodes generated after processing deps.')
    svgElement.appendChild(
      Object.assign(document.createElementNS('http://www.w3.org/2000/svg', 'text'), {
        textContent: '无法生成节点。',
        x: width / 2,
        y: 30,
        textAnchor: 'middle',
        fill: '#666',
        fontSize: '14px',
      }),
    )
    return
  }

  // --- Create SVG ---
  const svg = d3
    .select(svgElement)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height]) // Use dynamic width/height
    .attr('style', 'max-width: 100%; height: auto;') // Keep responsiveness

  // --- Create NEW Simulation ---
  // Important: Create a new simulation instance on each draw
  simulation = d3
    .forceSimulation(nodes)
    .force(
      'link',
      d3
        .forceLink<NodeData, LinkData>(links)
        .id(d => d.id)
        .distance(180)
        .strength(0.6),
    )
    .force('charge', d3.forceManyBody().strength(-800))
    .force('center', d3.forceCenter(width / 2, height / 2)) // Use NEW width/height
    .force(
      'collision',
      d3.forceCollide().radius((d: NodeData) => (d.width || 100) / 1.8), // Use type assertion
    )
    .alphaDecay(0.02) // Slightly faster cooling
    .alphaTarget(0) // Start stable unless interacted with

  // --- Arrowhead Definition ---
  const defs = svg.append('defs')
  defs
    .append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 15) // Placeholder, adjusted via line end point calculation now
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#666')

  // --- Draw Links (Mostly the same) ---
  const linkGroup = svg
    .append('g')
    .attr('class', 'links')
    .selectAll<SVGGElement, LinkData>('g.link')
    .data(links)
    .join('g')
    .attr('class', 'link')

  const linkLine = linkGroup
    .append('line')
    .attr('stroke', '#666')
    .attr('stroke-width', 2)
    .attr('marker-end', 'url(#arrowhead)')

  const linkConstraintBg = linkGroup
    .append('rect')
    .attr('class', 'link-constraint-bg')
    .attr('fill', 'white') // Or use container background color?
    .attr('rx', 3)
    .attr('ry', 3)
    .attr('opacity', 0.85)
    .style('display', 'none')

  const linkText = linkGroup
    .append('text')
    .attr('class', 'link-constraint')
    .attr('text-anchor', 'middle')
    .attr('dy', '-5')
    .attr('font-size', 10)
    .attr('fill', '#d9534f')
    .text(d => d.constraint || '')

  // --- Draw Nodes (Mostly the same) ---
  const nodeGroup = svg
    .append('g')
    .attr('class', 'nodes')
    .selectAll<SVGGElement, NodeData>('g.node')
    .data(nodes, d => d.id)
    .join('g')
    .attr('class', 'node')

  // Calculate node dimensions
  nodeGroup.each(function (d) {
    const group = d3.select(this)
    const tempText = group.append('text').attr('class', 'temp-node-text').style('opacity', 0).style('pointer-events', 'none').attr('font-size', 12).text(d.name)
    try {
      const textNode = tempText.node() as SVGTextElement | null
      const bbox = textNode?.getBBox() ?? { width: 80, height: 16, x: 0, y: 0 }
      d.width = bbox.width + 2 * nodePadding.x
      d.height = bbox.height + 2 * nodePadding.y
    }
    catch (e) {
      console.error('Error getting bbox for node:', d.name, e)
      d.width = 100
      d.height = 30
    }
    finally {
      tempText.remove()
    }
  })

  nodeGroup
    .append('rect')
    .attr('width', d => d.width || 100)
    .attr('height', d => d.height || 30)
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('fill', '#bbdeff')
    .attr('stroke', '#333')
    .attr('x', d => -(d.width || 100) / 2)
    .attr('y', d => -(d.height || 30) / 2)

  nodeGroup
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', 12)
    .text(d => d.name)

  // --- Simulation Tick (Mostly the same, but uses dynamic width/height for bounds) ---
  simulation.on('tick', () => {
    const isNodeData = (node: string | NodeData): node is NodeData =>
      typeof node !== 'string'

    linkLine.each(function (d) {
      const line = d3.select(this)
      // Ensure source/target are NodeData and have coordinates
      if (
        isNodeData(d.source) && isNodeData(d.target)
        && d.source.x != null && d.source.y != null
        && d.target.x != null && d.target.y != null
      ) {
        const dx = d.target.x - d.source.x
        const dy = d.target.y - d.source.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        // Use actual target node width if available, fallback, add buffer
        const targetRadius = (d.target.width ? d.target.width / 2 : 50) + 2

        // Prevent division by zero or NaN if nodes are exactly at the same spot
        if (dist < 1)
          return // Or draw a tiny line?

        const ratio = (dist - targetRadius) / dist
        // Clamp ratio to prevent negative values if radius > dist
        const clampedRatio = Math.max(0, ratio)

        const targetXAdjusted = d.source.x + dx * clampedRatio
        const targetYAdjusted = d.source.y + dy * clampedRatio

        line
          .attr('x1', d.source.x)
          .attr('y1', d.source.y)
          .attr('x2', targetXAdjusted)
          .attr('y2', targetYAdjusted)
      }
    })

    linkGroup.each(function (d) {
      const group = d3.select(this)
      const bgRect = group.select<SVGRectElement>('rect.link-constraint-bg')
      const text = group.select<SVGTextElement>('text.link-constraint')

      if (isNodeData(d.source) && isNodeData(d.target)
           && d.source.x != null && d.source.y != null
           && d.target.x != null && d.target.y != null) {
        const midX = (d.source.x + d.target.x) / 2
        const midY = (d.source.y + d.target.y) / 2
        text.attr('x', midX).attr('y', midY)

        if (d.constraint) {
          try {
            const textNode = text.node()
            if (textNode) {
              // Use requestAnimationFrame or setTimeout to get bbox reliably? Sometimes fails immediately.
              // Let's try without first.
              const bbox = textNode.getBBox()
              if (bbox && bbox.width > 0 && bbox.height > 0) {
                bgRect
                  .attr('x', bbox.x - nodePadding.x / 2)
                  .attr('y', bbox.y - nodePadding.y / 2)
                  .attr('width', bbox.width + nodePadding.x)
                  .attr('height', bbox.height + nodePadding.y)
                  .style('display', 'block')
              }
              else {
                bgRect.style('display', 'none')
              }
            }
            else {
              bgRect.style('display', 'none')
            }
          }
          catch (e) {
            console.error('Error getting bbox for link text', e)
            bgRect.style('display', 'none')
          }
        }
        else {
          bgRect.style('display', 'none')
        }
      }
      else {
        text.attr('x', null).attr('y', null)
        bgRect.style('display', 'none')
      }
    })

    nodeGroup.attr('transform', (d) => {
      // Apply boundaries using the dynamic width/height
      const radiusX = (d.width || 100) / 2
      const radiusY = (d.height || 30) / 2
      // Ensure d.x and d.y are numbers before using Math.max/min
      const currentX = typeof d.x === 'number' ? d.x : width / 2 // Fallback to center
      const currentY = typeof d.y === 'number' ? d.y : height / 2
      d.x = Math.max(radiusX, Math.min(width - radiusX, currentX))
      d.y = Math.max(radiusY, Math.min(height - radiusY, currentY))
      return `translate(${d.x},${d.y})`
    })
  })

  // --- Drag Behavior (Keep as is, ensure simulation ref is used) ---
  function dragstarted(event: D3DragEvent<SVGGElement, NodeData, NodeData>, d: NodeData) {
    if (!event.active && simulation)
      simulation.alphaTarget(0.3).restart()
    // Use potentially bounded positions from tick as starting point for fx/fy
    d.fx = d.x ?? event.x
    d.fy = d.y ?? event.y
  }

  function dragged(event: D3DragEvent<SVGGElement, NodeData, NodeData>, d: NodeData) {
    d.fx = event.x
    d.fy = event.y
  }

  function dragended(event: D3DragEvent<SVGGElement, NodeData, NodeData>, d: NodeData) {
    if (!event.active && simulation)
      simulation.alphaTarget(0)
    // Keep fixed position after drag by default
    // d.fx = null;
    // d.fy = null; // Uncomment to release node after drag
  }

  nodeGroup.call(
    d3.drag<SVGGElement, NodeData>()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended),
  )

  // Restart simulation to apply forces with new nodes/layout/size
  simulation.alpha(0.8).restart() // Give it a bit more initial energy
} // End of drawGraph

// --- Debounced version of drawGraph ---
// Adjust debounce delay as needed (200-500ms is common)
const debouncedDrawGraph = debounce(drawGraph, 300)

// --- Fullscreen Logic (Keep as is) ---
function checkFullscreenStatus() {
  isFullscreen.value = !!(document.fullscreenElement
    || (document as any).webkitFullscreenElement
    || (document as any).mozFullScreenElement
    || (document as any).msFullscreenElement)
}

async function toggleFullscreen() {
  const elem = graphContainerRef.value
  if (!elem)
    return
  try {
    if (!isFullscreen.value) {
      if (elem.requestFullscreen)
        await elem.requestFullscreen()
      else if ((elem as any).webkitRequestFullscreen)
        await (elem as any).webkitRequestFullscreen()
      else if ((elem as any).mozRequestFullScreen)
        await (elem as any).mozRequestFullScreen()
      else if ((elem as any).msRequestFullscreen)
        await (elem as any).msRequestFullscreen()
    }
    else {
      if (document.exitFullscreen)
        await document.exitFullscreen()
      else if ((document as any).webkitExitFullscreen)
        await (document as any).webkitExitFullscreen()
      else if ((document as any).mozCancelFullScreen)
        await (document as any).mozCancelFullScreen()
      else if ((document as any).msExitFullscreen)
        await (document as any).msExitFullscreen()
    }
  }
  catch (err) {
    console.error('Fullscreen API error:', err)
    checkFullscreenStatus() // Re-check state on error
  }
}

const fullscreenButtonText = computed(() => isFullscreen.value ? '退出全屏' : '全屏')

// --- Watcher and Lifecycle Hooks ---

// Watch for changes in dependencies prop
watch(() => props.deps, (newDeps, oldDeps) => {
  // Avoid redraw if data reference is the same or both are null/empty
  if (newDeps === oldDeps || (!newDeps?.length && !oldDeps?.length)) {
    // If graph is empty and new data arrives, still draw
    if (newDeps?.length && !simulation?.nodes().length) {
      console.log('Dependencies prop updated (initial data?), redrawing graph...')
      drawGraph() // Use non-debounced draw for direct data changes
    }
    else if (!newDeps?.length) {
      // If data removed, clear the graph
      drawGraph()
    }
    return
  }
  console.log('Dependencies prop updated, redrawing graph...')
  // Use non-debounced drawGraph for direct data changes for faster visual feedback
  // Or use debouncedDrawGraph if updates can be very rapid
  drawGraph()
}, { deep: true }) // Use deep watch if nested structure of deps might change

onMounted(() => {
  // Initial check and add listener for fullscreen changes
  checkFullscreenStatus()
  document.addEventListener('fullscreenchange', checkFullscreenStatus)
  document.addEventListener('webkitfullscreenchange', checkFullscreenStatus)
  document.addEventListener('mozfullscreenchange', checkFullscreenStatus)
  document.addEventListener('MSFullscreenChange', checkFullscreenStatus)

  // Setup Resize Observer
  if (graphContainerRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      // We only observe one element, check if its size changed
      if (entries && entries.length > 0) {
        // Ensure the element is still mounted and visible before redrawing
        if (graphContainerRef.value && graphContainerRef.value.isConnected) {
          console.log('Container resized, debouncing graph redraw...')
          debouncedDrawGraph() // Call the debounced redraw function
        }
      }
    })
    resizeObserver.observe(graphContainerRef.value) // Observe the container div
  }

  // Initial draw *after* the observer is set up and container ref is available.
  // Use nextTick to ensure the container has dimensions rendered by the browser.
  nextTick(() => {
    console.log('Component mounted, performing initial draw...')
    drawGraph() // Perform the initial draw
  })
})

onBeforeUnmount(() => {
  // Stop simulation
  if (simulation) {
    simulation.stop()
  }
  // Disconnect observer and remove listeners
  if (resizeObserver && graphContainerRef.value) {
    resizeObserver.unobserve(graphContainerRef.value)
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  resizeObserver = null // Clear reference

  document.removeEventListener('fullscreenchange', checkFullscreenStatus)
  document.removeEventListener('webkitfullscreenchange', checkFullscreenStatus)
  document.removeEventListener('mozfullscreenchange', checkFullscreenStatus)
  document.removeEventListener('MSFullscreenChange', checkFullscreenStatus)

  // Cancel any pending debounced calls to prevent errors after unmount
  debouncedDrawGraph.cancel()

  console.log('Component unmounted, cleaned up simulation and listeners.')
})
</script>

<!-- Template and Style remain mostly the same -->
<template>
  <div ref="graphContainerRef" class="dependency-graph-container">
    <button class="fullscreen-button" :title="fullscreenButtonText" @click="toggleFullscreen">
      <span v-if="!isFullscreen">⛶</span>
      <span v-else>↘</span>
    </button>
    <svg ref="svgRef" class="dependency-graph-svg" />
    <!-- Removed the v-if condition for the info text, as drawGraph handles empty state now -->
    <!-- <div class="graph-info">提示信息...</div> -->
  </div>
</template>

<style scoped>
/* Styles remain the same as your previous version */
.dependency-graph-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: sans-serif;
  width: 100%;
  height: 100%; /* Make container fill parent */
  min-height: 350px;
  position: relative;
  background-color: #f9f9f9;
  box-sizing: border-box; /* Include padding/border in element's total width/height */
  overflow: hidden; /* Hide scrollbars if SVG exceeds container */
}

/* Fullscreen styles */
.dependency-graph-container:-webkit-full-screen {
  background-color: #f9f9f9; width: 100%; height: 100%; overflow-y: auto;
}
.dependency-graph-container:-moz-full-screen {
  background-color: #f9f9f9; width: 100%; height: 100%; overflow-y: auto;
}
.dependency-graph-container:-ms-fullscreen {
  background-color: #f9f9f9; width: 100%; height: 100%; overflow-y: auto;
}
.dependency-graph-container:fullscreen {
  background-color: #f9f9f9; width: 100%; height: 100%; overflow-y: auto;
}

.dependency-graph-svg {
  border: 1px solid #ccc;
  border-radius: 4px;
  display: block;
  /* SVG width/height set by D3, let container control size */
  /* width: 100%; */ /* Remove fixed width */
  /* height: auto; */
}

.fullscreen-button {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  padding: 4px 8px;
  background-color: rgba(255, 255, 255, 0.8);
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: background-color 0.2s ease;
}
.fullscreen-button:hover { background-color: rgba(240, 240, 240, 0.9); }
.fullscreen-button span { display: inline-block; width: 1em; text-align: center; }

.graph-info { /* Only used if you add it back for specific messages */
  margin-top: 8px; padding: 5px 10px; font-size: 0.85em; color: #666;
  background-color: #eee; border-radius: 3px; position: relative; z-index: 5;
}

/* :deep styles remain the same */
:deep(.node) { cursor: grab; filter: drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.2)); }
:deep(.node:active) { cursor: grabbing; }
:deep(.node text) { user-select: none; pointer-events: none; font-weight: 500; }
:deep(.link-constraint) { font-weight: bold; pointer-events: none; user-select: none; font-family: monospace; }
:deep(.link-constraint-bg) { pointer-events: none; user-select: none; }
:deep(.links line) { stroke-opacity: 0.7; }
</style>
