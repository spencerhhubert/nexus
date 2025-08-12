<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { robotAPI } from "$lib/api";
  import type { SystemStatus, MotorInfo } from "$lib/types";

  let isOnline = $state(false);
  let isLoading = $state(true);
  let status = $state<SystemStatus | null>(null);
  let cameraFrame = $state<string | null>(null);
  let logs = $state<
    Array<{ level: string; message: string; timestamp: number }>
  >([]);

  let checkInterval: number;

  onMount(() => {
    checkConnection();
    checkInterval = setInterval(checkConnection, 2000);

    robotAPI.on("status_update", (event) => {
      status = event.status;
    });

    robotAPI.on("camera_frame", (event) => {
      cameraFrame = event.frame_data;
    });

    robotAPI.on("log", (event) => {
      logs = [...logs.slice(-99), event];
    });
  });

  onDestroy(() => {
    if (checkInterval) clearInterval(checkInterval);
    robotAPI.disconnect();
  });

  async function checkConnection() {
    try {
      const online = await robotAPI.isOnline();
      if (online && !isOnline) {
        status = await robotAPI.getStatus();
        robotAPI.connectWebSocket();
      }
      isOnline = online;
    } catch (e) {
      isOnline = false;
      status = null;
    } finally {
      isLoading = false;
    }
  }

  async function startSystem() {
    try {
      await robotAPI.startSystem();
      status = await robotAPI.getStatus();
    } catch (e) {
      console.error("Failed to start system:", e);
    }
  }

  async function stopSystem() {
    try {
      await robotAPI.stopSystem();
      status = await robotAPI.getStatus();
    } catch (e) {
      console.error("Failed to stop system:", e);
    }
  }

  async function setMotorSpeed(motorId: string, speed: number) {
    try {
      await robotAPI.setMotorSpeed({ motor_id: motorId, speed });
    } catch (e) {
      console.error("Failed to set motor speed:", e);
    }
  }

  function getLifecycleColor(stage: string): string {
    switch (stage) {
      case "running":
        return "green";
      case "paused_by_user":
        return "orange";
      case "stopping":
        return "red";
      default:
        return "gray";
    }
  }
</script>

<svelte:head>
  <title>Sorting Machine Controls</title>
</svelte:head>

<div class="container">
  <header>
    <h1>Sorting Machine Controls</h1>
    <div
      class="connection-status"
      class:online={isOnline}
      class:offline={!isOnline}
    >
      {isLoading ? "Connecting..." : isOnline ? "Connected" : "Offline"}
    </div>
  </header>

  {#if !isOnline}
    <div class="offline-message">
      <h2>Robot Server Offline</h2>
      <p>Waiting for connection to robot system...</p>
      <div class="spinner"></div>
    </div>
  {:else if status}
    <div class="control-grid">
      <!-- System Status -->
      <section class="status-panel">
        <h2>System Status</h2>
        <div class="status-item">
          <label>Lifecycle:</label>
          <span
            class="lifecycle-badge"
            style="background-color: {getLifecycleColor(
              status.lifecycle_stage,
            )}"
          >
            {status.lifecycle_stage.replace("_", " ").toUpperCase()}
          </span>
        </div>
        <div class="status-item">
          <label>Sorting State:</label>
          <span>{status.sorting_state.replace("_", " ").toUpperCase()}</span>
        </div>
        <div class="status-item">
          <label>Objects in Frame:</label>
          <span>{status.objects_in_frame}</span>
        </div>
        <div class="status-item">
          <label>Conveyor Speed:</label>
          <span>{status.conveyor_speed?.toFixed(4) || "Unknown"} cm/ms</span>
        </div>

        <div class="system-controls">
          {#if status.lifecycle_stage === "paused_by_user"}
            <button class="start-btn" onclick={startSystem}>Start System</button
            >
          {:else if status.lifecycle_stage === "running"}
            <button class="stop-btn" onclick={stopSystem}>Stop System</button>
          {/if}
        </div>
      </section>

      <!-- Camera Feed -->
      <section class="camera-panel">
        <h2>Camera Feed</h2>
        <div class="camera-container">
          {#if cameraFrame}
            <img src="data:image/jpeg;base64,{cameraFrame}" alt="Camera feed" />
          {:else}
            <div class="no-camera">No camera feed</div>
          {/if}
        </div>
      </section>

      <!-- Motor Controls -->
      <section class="motors-panel">
        <h2>Motor Controls</h2>
        {#each status.motors as motor (motor.motor_id)}
          <div class="motor-control">
            <label>{motor.display_name}</label>
            <div class="motor-inputs">
              <span class="current-speed">Current: {motor.current_speed}</span>
              <input
                type="range"
                min={motor.min_speed}
                max={motor.max_speed}
                value={motor.current_speed}
                onchange={(e) =>
                  setMotorSpeed(motor.motor_id, parseInt(e.target.value))}
              />
              <input
                type="number"
                min={motor.min_speed}
                max={motor.max_speed}
                value={motor.current_speed}
                onchange={(e) =>
                  setMotorSpeed(motor.motor_id, parseInt(e.target.value))}
                class="speed-input"
              />
            </div>
          </div>
        {/each}
      </section>

      <!-- Logs -->
      <section class="logs-panel">
        <h2>System Logs</h2>
        <div class="logs-container">
          {#each logs.slice(-20) as log (log.timestamp)}
            <div class="log-entry {log.level.toLowerCase()}">
              <span class="timestamp"
                >{new Date(log.timestamp).toLocaleTimeString()}</span
              >
              <span class="level">{log.level}</span>
              <span class="message">{log.message}</span>
            </div>
          {/each}
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
    font-family:
      -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 20px;
  }

  h1 {
    margin: 0;
    color: #333;
  }

  .connection-status {
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: 600;
  }

  .connection-status.online {
    background-color: #d4edda;
    color: #155724;
  }

  .connection-status.offline {
    background-color: #f8d7da;
    color: #721c24;
  }

  .offline-message {
    text-align: center;
    padding: 60px 20px;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #007bff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 20px auto;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .control-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  section {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
  }

  section h2 {
    margin-top: 0;
    margin-bottom: 20px;
    color: #333;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
  }

  .status-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .lifecycle-badge {
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .system-controls {
    margin-top: 20px;
  }

  .start-btn,
  .stop-btn {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
  }

  .start-btn {
    background-color: #28a745;
    color: white;
  }

  .stop-btn {
    background-color: #dc3545;
    color: white;
  }

  .camera-container {
    background: #f8f9fa;
    border-radius: 4px;
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .camera-container img {
    max-width: 100%;
    max-height: 400px;
    border-radius: 4px;
  }

  .no-camera {
    color: #666;
    font-style: italic;
  }

  .motor-control {
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 4px;
  }

  .motor-control label {
    display: block;
    margin-bottom: 10px;
    font-weight: 600;
  }

  .motor-inputs {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 10px;
    align-items: center;
  }

  .current-speed {
    font-size: 12px;
    color: #666;
  }

  .speed-input {
    width: 80px;
    padding: 4px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }

  .logs-container {
    max-height: 300px;
    overflow-y: auto;
    background: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
  }

  .log-entry {
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 10px;
    padding: 4px 0;
    border-bottom: 1px solid #eee;
    font-size: 12px;
  }

  .log-entry.error {
    color: #dc3545;
  }

  .log-entry.warning {
    color: #ffc107;
  }

  .timestamp {
    color: #666;
  }

  .level {
    font-weight: 600;
    text-transform: uppercase;
  }

  @media (max-width: 768px) {
    .control-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
