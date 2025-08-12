<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { robotAPI } from "$lib/api";
  import type { SystemStatus } from "$lib/types";
  import ConnectionStatus from "$lib/components/ConnectionStatus.svelte";
  import StatusPanel from "$lib/components/SystemStatus.svelte";
  import CameraFeed from "$lib/components/CameraFeed.svelte";
  import MotorControls from "$lib/components/MotorControls.svelte";


  let isOnline = $state(false);
  let isLoading = $state(true);
  let status = $state<SystemStatus | null>(null);
  let cameraFrame = $state<string | null>(null);

  let checkInterval: number;
  let wsConnected = $state(false);

  onMount(() => {
    attemptConnection();
    checkInterval = setInterval(attemptConnection, 3000);

    robotAPI.on("status_update", (event) => {
      console.log("Status update received:", event.status.lifecycle_stage);
      status = event.status;
      if (!isOnline) {
        console.log("First status update received, marking as online");
        isOnline = true;
        isLoading = false;
      }
    });

    robotAPI.on("camera_frame", (event) => {
      console.log("Camera frame received, size:", event.frame_data.length);
      cameraFrame = event.frame_data;
    });


  });

  onDestroy(() => {
    if (checkInterval) clearInterval(checkInterval);
    robotAPI.disconnect();
  });

  async function attemptConnection() {
    console.log("attemptConnection() called, wsConnected:", wsConnected);
    if (wsConnected) {
      console.log("Already connected, skipping");
      return;
    }

    try {
      console.log("Checking if robot is online...");
      const online = await robotAPI.isOnline();
      console.log("Robot online check result:", online);

      if (online) {
        console.log("Robot is online, attempting WebSocket connection...");
        robotAPI.connectWebSocket();
        wsConnected = true;
        console.log("WebSocket connection initiated");
      } else {
        console.log("Robot is not online");
      }
    } catch (e) {
      console.error("Error during connection attempt:", e);
      isOnline = false;
      status = null;
      wsConnected = false;
    }

    if (!wsConnected) {
      console.log("WebSocket not connected, setting loading to false");
      isLoading = false;
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
    <ConnectionStatus {isOnline} {isLoading} />
  </header>

  {#if !isOnline && !isLoading}
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
      <StatusPanel {status} />
      <CameraFeed {cameraFrame} />
      <MotorControls motors={status?.motors || null} />
    </div>
  {/if}
</div>
