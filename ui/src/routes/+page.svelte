<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { robotAPI } from "$lib/api";
  import type { SystemStatus } from "$lib/types";
  import ConnectionStatus from "$lib/components/ConnectionStatus.svelte";
  import StatusPanel from "$lib/components/SystemStatus.svelte";
  import CameraFeed from "$lib/components/CameraFeed.svelte";
  import MotorControls from "$lib/components/MotorControls.svelte";
  import TrajectoryList from "$lib/components/TrajectoryList.svelte";
  import {
    systemStatus,
    cameraFrame,
    connectionState,
    recentTrajectories,
    updateSystemStatus,
    updateCameraFrame,
    updateConnectionState,
    addObservation,
    addTrajectory,
    updateTrajectory,
  } from "$lib/stores/app";

  let checkInterval: number;

  onMount(() => {
    attemptConnection();
    checkInterval = setInterval(attemptConnection, 3000);

    robotAPI.on("status_update", (event) => {
      console.log("Status update received:", event.status.lifecycle_stage);
      updateSystemStatus(event.status);
      if (!$connectionState.isOnline) {
        console.log("First status update received, marking as online");
        updateConnectionState({ isOnline: true, isLoading: false });
      }
    });

    robotAPI.on("camera_frame", (event) => {
      console.log("Camera frame received, size:", event.frame_data.length);
      updateCameraFrame(event.frame_data, event.frame_id);
    });

    robotAPI.on("observation", (event) => {
      console.log("Observation received:", event.observation.observation_id);
      addObservation(event.observation);
    });

    robotAPI.on("trajectory", (event) => {
      console.log("Trajectory received:", event.trajectory.trajectory_id);
      // Check if trajectory exists
      const existingIndex = $recentTrajectories.findIndex(
        t => t.trajectory_id === event.trajectory.trajectory_id
      );
      
      if (existingIndex >= 0) {
        updateTrajectory(event.trajectory.trajectory_id, event.trajectory);
      } else {
        addTrajectory(event.trajectory);
      }
    });

    robotAPI.on("connect", () => {
      console.log("WebSocket connected");
      updateConnectionState({ wsConnected: true, isLoading: false });
    });

    robotAPI.on("disconnect", (event) => {
      console.log("WebSocket disconnected:", event);
      updateConnectionState({ 
        wsConnected: false, 
        isOnline: false 
      });
    });

  });

  onDestroy(() => {
    if (checkInterval) clearInterval(checkInterval);
    robotAPI.disconnect();
  });

  async function attemptConnection() {
    console.log("attemptConnection() called, wsConnected:", $connectionState.wsConnected);
    if ($connectionState.wsConnected) {
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
        console.log("WebSocket connection initiated");
      } else {
        console.log("Robot is not online");
        updateConnectionState({ isOnline: false });
      }
    } catch (e) {
      console.error("Error during connection attempt:", e);
      updateConnectionState({ 
        isOnline: false, 
        wsConnected: false 
      });
    }

    if (!$connectionState.wsConnected) {
      console.log("WebSocket not connected, setting loading to false");
      updateConnectionState({ isLoading: false });
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
    <ConnectionStatus isOnline={$connectionState.isOnline} isLoading={$connectionState.isLoading} />
  </header>

  {#if !$connectionState.isOnline && !$connectionState.isLoading}
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
    <div class="grid grid-cols-2 gap-4 h-[calc(100vh-200px)]">
      <!-- Top Left: Camera Feed -->
      <div class="border border-gray-300 rounded-lg">
        <CameraFeed cameraFrame={$cameraFrame} />
      </div>
      
      <!-- Top Right: Classification -->
      <div class="border border-gray-300 rounded-lg p-4">
        <h2 class="text-lg font-semibold mb-4">Classification</h2>
        <div class="space-y-4">
          <!-- Stock image placeholder -->
          <div class="bg-yellow-200 h-32 flex items-center justify-center rounded">
            <p class="text-sm text-center">
              Stock image we will pull<br/>based on classification id
            </p>
          </div>
          
          <!-- Trajectory thumbnails -->
          <div class="flex space-x-2 overflow-x-auto">
            <div class="bg-blue-200 w-16 h-16 flex-shrink-0 rounded"></div>
            <div class="bg-blue-200 w-16 h-16 flex-shrink-0 rounded"></div>
            <div class="bg-blue-200 w-16 h-16 flex-shrink-0 rounded"></div>
            <div class="bg-blue-200 w-16 h-16 flex-shrink-0 rounded"></div>
          </div>
          
          <!-- Piece info -->
          <div class="bg-gray-100 p-3 rounded">
            {#if $recentTrajectories.length > 0}
              {@const latest = $recentTrajectories[0]}
              <div><strong>Piece ID:</strong> {latest.consensus_classification || 'unknown'}</div>
              <div><strong>Category:</strong> unknown</div>
              {#if latest.target_bin}
                <div><strong>Bin coordinates:</strong> ({latest.target_bin.bin_x}, {latest.target_bin.bin_y})</div>
              {:else}
                <div><strong>Bin coordinates:</strong> Not assigned</div>
              {/if}
            {:else}
              <div>No trajectory data</div>
            {/if}
          </div>
          
          <!-- Scrollable trajectories list -->
          <div class="flex-1 overflow-y-auto">
            <TrajectoryList />
          </div>
        </div>
      </div>
      
      <!-- Bottom Left: System Status -->
      <div class="border border-gray-300 rounded-lg">
        <StatusPanel status={$systemStatus} />
      </div>
      
      <!-- Bottom Right: Controls -->
      <div class="border border-gray-300 rounded-lg">
        <MotorControls motors={$systemStatus?.motors || null} />
      </div>
    </div>
  {/if}
</div>
