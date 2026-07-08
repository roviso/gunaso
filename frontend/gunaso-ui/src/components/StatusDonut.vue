<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Chart, ArcElement, Tooltip, Legend, DoughnutController } from 'chart.js'

Chart.register(ArcElement, Tooltip, Legend, DoughnutController)

const props = defineProps({
  data: { type: Object, default: () => ({}) }
})

const STATUS_COLORS = {
  submitted:    '#F59E0B',
  acknowledged: '#06B6D4',
  in_review:    '#3B82F6',
  resolved:     '#22C55E',
  escalated:    '#F97316',
  rejected:     '#EF4444',
  closed:       '#6B7280',
}

const STATUS_LABELS = {
  submitted: 'Submitted', acknowledged: 'Acknowledged', in_review: 'In Review',
  resolved: 'Resolved', escalated: 'Escalated', rejected: 'Rejected', closed: 'Closed',
}

const canvasRef = ref(null)
let chartInstance = null

function buildChart() {
  if (!canvasRef.value) return
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }

  const entries = Object.entries(props.data).filter(([, v]) => v > 0)
  if (!entries.length) return

  chartInstance = new Chart(canvasRef.value, {
    type: 'doughnut',
    data: {
      labels: entries.map(([k]) => STATUS_LABELS[k] || k),
      datasets: [{
        data: entries.map(([, v]) => v),
        backgroundColor: entries.map(([k]) => STATUS_COLORS[k] || '#94a3b8'),
        borderWidth: 0,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { size: 11 },
            padding: 10,
            color: '#64748b',
            boxWidth: 10,
            boxHeight: 10,
          }
        },
        tooltip: {
          backgroundColor: '#1D3557',
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,0.8)',
          padding: 10,
          cornerRadius: 8,
          displayColors: true,
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
    <div v-if="!Object.values(data).some(v => v > 0)"
      class="absolute inset-0 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
      No data available
    </div>
    <canvas ref="canvasRef" />
  </div>
</template>
