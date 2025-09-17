<script lang="ts">
  import { onMount } from 'svelte';
  import { createPageState } from '$lib/stores/page-state.svelte';
  import AppHeader from '$lib/components/AppHeader.svelte';
  import CameraFeeds from '$lib/components/CameraFeeds.svelte';
  import SystemStatus from '$lib/components/SystemStatus.svelte';
  import SystemControls from '$lib/components/SystemControls.svelte';
  import SettingsModal from '$lib/components/SettingsModal.svelte';
  import MotorConfigModal from '$lib/components/MotorConfigModal.svelte';

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
  <AppHeader isConnected={pageState.state.wsConnected} onSettingsOpen={openSettings} />

  <div class="container mx-auto p-6">
    <div class="space-y-6">
      <CameraFeeds />
      <SystemStatus
        lifecycleStage={pageState.state.lifecycleStage}
        sortingState={pageState.state.sortingState}
      />
      <SystemControls onMotorConfigOpen={openMotorConfig} />
    </div>
  </div>
</div>

<SettingsModal isOpen={isSettingsOpen} onClose={closeSettings} />
<MotorConfigModal isOpen={isMotorConfigOpen} onClose={closeMotorConfig} />