<script lang="ts">
  import { onMount } from 'svelte';
  import { pauseSystem, resumeSystem } from '$lib/api-client';
  import { createPageState } from '$lib/stores/page-state.svelte';
  import VideoFeed from '$lib/components/VideoFeed.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import userSettings from '$lib/stores/user-settings.svelte';
  import { Play, Pause, Settings, Sun, Moon, Wifi, WifiOff, Loader } from 'lucide-svelte';

  const pageState = createPageState();
  let isSettingsOpen = $state(false);

  function toggleTheme() {
    userSettings.update(settings => ({
      ...settings,
      theme: settings.theme === 'light' ? 'dark' : 'light'
    }));
  }

  function openSettings() {
    isSettingsOpen = true;
  }

  function closeSettings() {
    isSettingsOpen = false;
  }

  async function handlePause() {
    try {
      await pauseSystem();
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  }

  async function handleResume() {
    try {
      await resumeSystem();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  }

  onMount(() => {
    return () => {
      pageState.disconnect();
    };
  });
</script>

<svelte:head>
  <title>Sorter</title>
</svelte:head>

<div class="min-h-screen">
<div class="max-w-7xl mx-auto p-5">
  <header class="flex justify-between items-center mb-8 pb-5 border-b border-gray-200 dark:border-gray-700">
    <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">Sorter</h1>

    <div class="flex items-center gap-4">
      <!-- Connection Status -->
      <div class="flex items-center gap-2 px-3 py-1 border border-gray-300 dark:border-gray-600">
        {#if pageState.state.wsConnected}
          <Wifi size={16} class="text-green-500" />
          <span class="text-sm text-gray-700 dark:text-gray-300">Connected</span>
        {:else if pageState.state.reconnecting}
          <Loader size={16} class="text-yellow-500 animate-spin" />
          <span class="text-sm text-gray-700 dark:text-gray-300">Connecting...</span>
        {:else}
          <WifiOff size={16} class="text-red-500" />
          <span class="text-sm text-gray-700 dark:text-gray-300">Disconnected</span>
        {/if}
      </div>

      <!-- Settings Button -->
      <button
        onclick={openSettings}
        class="p-2 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600"
      >
        <Settings size={20} />
      </button>
    </div>
  </header>

  <div class="space-y-6">
    <!-- Camera Feeds -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <VideoFeed camera="main_camera" title="Main Camera" />
      <VideoFeed camera="feeder_camera" title="Feeder Camera" />
    </div>

    <div class="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700">
      <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">System Status</h2>
      <div class="flex items-center gap-4 mb-4">
        <span class="font-medium text-gray-700 dark:text-gray-300">Lifecycle Stage:</span>
        <span class="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-800">
          {pageState.state.lifecycleStage}
        </span>
      </div>
      <div class="flex items-center gap-4 mb-4">
        <span class="font-medium text-gray-700 dark:text-gray-300">Sorting State:</span>
        <span class="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800">
          {pageState.state.sortingState}
        </span>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700">
      <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">Controls</h2>
      <div class="flex gap-4">
        <button
          onclick={handlePause}
          class="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white border border-yellow-600 flex items-center gap-2"
        >
          <Pause size={16} />
          Pause System
        </button>
        <button
          onclick={handleResume}
          class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white border border-green-600 flex items-center gap-2"
        >
          <Play size={16} />
          Resume System
        </button>
      </div>
    </div>
  </div>
</div>
</div>

<Modal isOpen={isSettingsOpen} title="Settings" onClose={closeSettings}>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <span class="text-gray-700 dark:text-gray-300">Theme</span>
      <button
        onclick={toggleTheme}
        class="flex items-center gap-2 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600"
      >
        {#if $userSettings.theme === 'light'}
          <Sun size={16} />
          Light
        {:else}
          <Moon size={16} />
          Dark
        {/if}
      </button>
    </div>
  </div>
</Modal>
