<script lang="ts">
  import { ChevronUp, ChevronDown } from 'lucide-svelte';

  interface CameraPerformanceMetrics {
    fps_1s: number;
    fps_5s: number;
    latency_1s: number;
    latency_5s: number;
  }

  interface Props {
    metrics: CameraPerformanceMetrics | null;
    isOpen: boolean;
    onToggle: () => void;
  }

  let { metrics, isOpen, onToggle }: Props = $props();

  function formatNumber(num: number | null, decimals = 1): string {
    return num?.toFixed(decimals) ?? '0.0';
  }
</script>

{#if isOpen && metrics}
  <div class="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750 p-3">
    <div class="flex items-center justify-between mb-3">
      <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300">Performance Metrics</h4>
      <button
        on:click={onToggle}
        class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      >
        <ChevronUp size={16} class="text-gray-500 dark:text-gray-400" />
      </button>
    </div>

    <div class="grid grid-cols-2 gap-4 text-sm">
      <div>
        <div class="text-gray-600 dark:text-gray-400 mb-1">FPS</div>
        <div class="space-y-1">
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-500">1s:</span>
            <span class="font-mono text-gray-900 dark:text-gray-100">{formatNumber(metrics.fps_1s)}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-500">5s:</span>
            <span class="font-mono text-gray-900 dark:text-gray-100">{formatNumber(metrics.fps_5s)}</span>
          </div>
        </div>
      </div>

      <div>
        <div class="text-gray-600 dark:text-gray-400 mb-1">Latency (ms)</div>
        <div class="space-y-1">
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-500">1s:</span>
            <span class="font-mono text-gray-900 dark:text-gray-100">{formatNumber(metrics.latency_1s)}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-500">5s:</span>
            <span class="font-mono text-gray-900 dark:text-gray-100">{formatNumber(metrics.latency_5s)}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
{:else if !isOpen}
  <button
    on:click={onToggle}
    class="hidden"
  >
    <ChevronDown size={16} />
  </button>
{/if}