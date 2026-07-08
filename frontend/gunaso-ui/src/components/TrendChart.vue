<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  Chart,
  CategoryScale, LinearScale,
  PointElement, LineElement,
  Filler, Tooltip
} from 'chart.js'

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps({
  data: { type: Array, default: () => [] },
  label: { type: String, default: 'Submissions' }
})

const canvasRef = ref(null)
let chartInstance = null

function buildChart() {
  if (!canvasRef.value) return
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }
  if (!props.data.length) return

  chartInstance = new Chart(canvasRef.value, {
    type: 'line',
    data: {
      labels: props.data.map((d) => d.label || d.date || ''),
      datasets: [{
        label: props.label,
        data: props.data.map((d) => d.count ?? d.value ?? 0),
        borderColor: '#E63946',
        backgroundColor: 'rgba(230, 57, 70, 0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#E63946',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1D3557',
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,0.8)',
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
        }
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { font: { size: 11 }, color: '#94a3b8' }
        },
        y: {
          grid: { color: 'rgba(148,163,184,0.12)' },
          border: { display: false },
          ticks: { font: { size: 11 }, color: '#94a3b8', precision: 0 },
          beginAtZero: true
        }
      }
    }
  })
}

onMounted(buildChart)
watch(() => props.data, buildChart, { deep: true })
onUnmounted(() => { if (chartInstance) chartInstance.destroy() })
</script>

<template>
  <div class="relative" style="height: 190px">
    <div v-if="!data.length" class="absolute inset-0 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
      No data available
    </div>
    <canvas ref="canvasRef" />
  </div>
</template>
