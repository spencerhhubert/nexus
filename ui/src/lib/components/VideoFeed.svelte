<script lang="ts">
  import { getPageState } from '$lib/stores/page-state.svelte';
  import { Camera, Activity } from 'lucide-svelte';
  import CameraPerformanceMetrics from './CameraPerformanceMetrics.svelte';

  interface Props {
    camera: 'main_camera' | 'feeder_camera';
    title: string;
  }

  let { camera, title }: Props = $props();

  const pageState = getPageState();
  let isPerformanceOpen = $state(false);

  function togglePerformance() {
    isPerformanceOpen = !isPerformanceOpen;
  }

  const frame = $derived(() => {
    return camera === 'main_camera'
      ? pageState.state.mainCameraFrame
      : pageState.state.feederCameraFrame;
  });

  const performanceMetrics = $derived(() => {
    return camera === 'main_camera'
      ? pageState.state.mainCameraPerformance
      : pageState.state.feederCameraPerformance;
  });

  const imageSrc = $derived(() => {
    const currentFrame = frame();
    return currentFrame ? `data:image/jpeg;base64,${currentFrame.data}` : null;
  });

  const lastUpdate = $derived(() => {
    const currentFrame = frame();
    return currentFrame ? new Date(currentFrame.timestamp).toLocaleTimeString() : 'No data';
  });
</script>

<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
  <div class="p-6">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      <div class="flex items-center gap-3">
        <button
          on:click={togglePerformance}
          class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title="Performance metrics"
        >
          <Activity size={18} class="text-gray-500 dark:text-gray-400" />
        </button>
        <span class="text-sm text-gray-500 dark:text-gray-400">
          Last: {lastUpdate()}
        </span>
      </div>
    </div>

    <div class="relative bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600" style="aspect-ratio: 4/3;">
      {#if imageSrc()}
        <img
          src={imageSrc()}
          alt="{title} feed"
          class="w-full h-full object-cover"
        />
      {:else}
        <div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
          <div class="text-center">
            <Camera size={48} class="mx-auto mb-2" />
            <div>No video feed</div>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <CameraPerformanceMetrics
    metrics={performanceMetrics()}
    isOpen={isPerformanceOpen}
    onToggle={togglePerformance}
  />
</div>
