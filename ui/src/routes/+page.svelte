<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { robotAPI } from "$lib/api";
  import { logger } from "$lib/logger";
  import { controlsPageState } from "$lib/stores/controlsPageState";
  import ConnectionStatus from "$lib/components/ConnectionStatus.svelte";
  import StatusPanel from "$lib/components/SystemStatus.svelte";
  import CameraFeed from "$lib/components/CameraFeed.svelte";
  import MotorControls from "$lib/components/MotorControls.svelte";

  let checkInterval: number;

  onMount(() => {
    attemptConnection();
    checkInterval = setInterval(attemptConnection, 3000);

    robotAPI.on("status_update", (event) => {
      logger.log(1, "Status update received:", event.status.lifecycle_stage);
      controlsPageState.setStatus(event.status);
      
      let currentState: any;
      const unsubscribe = controlsPageState.subscribe(state => currentState = state);
      unsubscribe();
      
      if (!currentState?.isOnline) {
        logger.log(1, "First status update received, marking as online");
        controlsPageState.setOnline(true);
        controlsPageState.setLoading(false);
      }
    });

    robotAPI.on("camera_frame", (event) => {
      logger.log(1, "Camera frame received, size:", event.frame_data.length);
      controlsPageState.setCameraFrame(event.frame_data);
    });

    robotAPI.on("connect", () => {
      logger.log(1, "WebSocket connected");
      controlsPageState.setWsConnected(true);
      controlsPageState.setLoading(false);
    });

    robotAPI.on("disconnect", (event) => {
      logger.log(1, "WebSocket disconnected:", event);
      controlsPageState.setWsConnected(false);
      controlsPageState.reset();
    });

  });

  onDestroy(() => {
    if (checkInterval) clearInterval(checkInterval);
    robotAPI.disconnect();
  });

  async function attemptConnection() {
    let currentState: any;
    const unsubscribe = controlsPageState.subscribe(state => currentState = state);
    unsubscribe();
    
    logger.log(1, "attemptConnection() called, wsConnected:", currentState?.wsConnected);
    if (currentState?.wsConnected) {
      logger.log(1, "Already connected, skipping");
      return;
    }

    try {
      logger.log(1, "Checking if robot is online...");
      const online = await robotAPI.isOnline();
      logger.log(1, "Robot online check result:", online);

      if (online) {
        logger.log(1, "Robot is online, attempting WebSocket connection...");
        robotAPI.connectWebSocket();
        logger.log(1, "WebSocket connection initiated");
      } else {
        logger.log(1, "Robot is not online");
        controlsPageState.reset();
      }
    } catch (e) {
      logger.error(1, "Error during connection attempt:", e);
      controlsPageState.reset();
      controlsPageState.setWsConnected(false);
    }

    const unsubscribe2 = controlsPageState.subscribe(state => currentState = state);
    unsubscribe2();
    if (!currentState?.wsConnected) {
      logger.log(1, "WebSocket not connected, setting loading to false");
      controlsPageState.setLoading(false);
    }
  }
</script>

<svelte:head>
  <title>Sorter</title>
</svelte:head>

<div class="max-w-7xl mx-auto p-5">
  <header
    class="flex justify-between items-center mb-8 pb-5 border-b border-surface-200 dark:border-surface-700"
  >
    <h1 class="text-3xl font-bold text-foreground-light dark:text-foreground-dark">Sorter Controls</h1>
    <ConnectionStatus isOnline={$controlsPageState.isOnline} isLoading={$controlsPageState.isLoading} />
  </header>

  {#if !$controlsPageState.isOnline && !$controlsPageState.isLoading}
    <div class="text-center py-16">
      <h2 class="text-2xl font-semibold text-surface-700 dark:text-surface-300 mb-4">
        Sorter Server Offline
      </h2>
      <p class="text-surface-600 dark:text-surface-400 mb-6">
        Waiting for connection to sorting machine...
      </p>
      <div
        class="w-10 h-10 border-4 border-surface-300 dark:border-surface-600 border-t-primary-500 dark:border-t-primary-400 rounded-full animate-spin mx-auto"
      ></div>
    </div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <StatusPanel pageState={controlsPageState} />
      <CameraFeed cameraFrame={$controlsPageState.cameraFrame} />
      <MotorControls pageState={controlsPageState} />
    </div>
  {/if}
</div>
