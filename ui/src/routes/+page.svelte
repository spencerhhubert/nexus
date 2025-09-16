<script lang="ts">
  import { getLifecycleStage, pauseSystem, resumeSystem } from '$lib/api-client';

  let lifecycleStage = 'unknown';
  let loading = false;

  async function fetchLifecycleStage() {
    try {
      loading = true;
      lifecycleStage = await getLifecycleStage();
    } catch (error) {
      console.error('Failed to fetch lifecycle stage:', error);
      lifecycleStage = 'error';
    } finally {
      loading = false;
    }
  }

  async function handlePause() {
    try {
      await pauseSystem();
      await fetchLifecycleStage();
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  }

  async function handleResume() {
    try {
      await resumeSystem();
      await fetchLifecycleStage();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  }
</script>

<svelte:head>
  <title>Sorter</title>
</svelte:head>

<div class="max-w-7xl mx-auto p-5">
  <header class="flex justify-between items-center mb-8 pb-5 border-b border-surface-200 dark:border-surface-700">
    <h1 class="text-3xl font-bold text-foreground-light dark:text-foreground-dark">Sorter</h1>
  </header>

  <div class="space-y-6">
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
      <h2 class="text-xl font-semibold mb-4">System Status</h2>
      <div class="flex items-center gap-4 mb-4">
        <span class="font-medium">Lifecycle Stage:</span>
        <span class="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
          {loading ? 'Loading...' : lifecycleStage}
        </span>
        <button
          on:click={fetchLifecycleStage}
          class="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
          disabled={loading}
        >
          Refresh
        </button>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
      <h2 class="text-xl font-semibold mb-4">Controls</h2>
      <div class="flex gap-4">
        <button
          on:click={handlePause}
          class="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded"
        >
          Pause System
        </button>
        <button
          on:click={handleResume}
          class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded"
        >
          Resume System
        </button>
      </div>
    </div>
  </div>
</div>