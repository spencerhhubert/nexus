<script lang="ts">
  import { onMount } from 'svelte';
  import { createPageState } from '$lib/stores/page-state.svelte';
  import AppHeader from '$lib/components/AppHeader.svelte';
  import CameraFeeds from '$lib/components/CameraFeeds.svelte';
  import SystemStatus from '$lib/components/SystemStatus.svelte';
  import SystemControls from '$lib/components/SystemControls.svelte';
  import SettingsModal from '$lib/components/SettingsModal.svelte';
  import MotorConfigModal from '$lib/components/MotorConfigModal.svelte';
  import KnownObjectsList from '$lib/components/KnownObjectsList.svelte';

  const pageState = createPageState();
  let isSettingsOpen = $state(false);
  let isMotorConfigOpen = $state(false);

  function openSettings() {
    isSettingsOpen = true;
  }

  function closeSettings() {
    isSettingsOpen = false;
  }

  function openMotorConfig() {
    isMotorConfigOpen = true;
  }

  function closeMotorConfig() {
    isMotorConfigOpen = false;
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

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
  <AppHeader isConnected={pageState.state.wsConnected} isReconnecting={pageState.state.reconnecting} onSettingsOpen={openSettings} />

  <div class="container mx-auto p-6">
    <div class="flex gap-6 h-[calc(100vh-120px)]">
      <!-- Known Objects List - Left Panel -->
      <div class="w-80 flex-shrink-0">
        <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 h-full">
          <KnownObjectsList />
        </div>
      </div>

      <!-- Main Content - Center Panel -->
      <div class="flex-1 space-y-6">
        <CameraFeeds />
        <SystemStatus
          lifecycleStage={pageState.state.lifecycleStage}
          sortingState={pageState.state.sortingState}
          encoder={pageState.state.encoder}
        />
        <SystemControls onMotorConfigOpen={openMotorConfig} />
      </div>
    </div>
  </div>
</div>

<SettingsModal isOpen={isSettingsOpen} onClose={closeSettings} />
<MotorConfigModal isOpen={isMotorConfigOpen} onClose={closeMotorConfig} />