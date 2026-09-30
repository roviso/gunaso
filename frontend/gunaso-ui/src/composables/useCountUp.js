import { ref, watch, onBeforeUnmount } from 'vue'

// Animates a number from 0 to `source()` once it becomes available.
// Respects prefers-reduced-motion by jumping straight to the value.
export function useCountUp(source, duration = 1400) {
  const display = ref(0)
  let frame = null
  const reduce = typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  watch(source, (target) => {
    if (frame) cancelAnimationFrame(frame)
    if (target == null || Number.isNaN(Number(target))) return
    const end = Number(target)
    if (reduce || end === 0) {
      display.value = end
      return
    }
    const start = performance.now()
    const decimals = Number.isInteger(end) ? 0 : 1
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      display.value = Number((end * eased).toFixed(decimals))
      if (t < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
  }, { immediate: true })

  onBeforeUnmount(() => frame && cancelAnimationFrame(frame))
  return display
}
