<script lang="ts">
  import type { SystemStatus } from "../types";
  import { robotAPI } from "../api";
  import { toTitleCase } from "$lib/util";

  interface Props {
    status: SystemStatus | null;
  }

  let { status }: Props = $props();

  async function startSystem() {
    try {
      await robotAPI.startSystem();
    } catch (e) {
      console.error("Failed to start system:", e);
    }
  }

  async function stopSystem() {
    try {
      await robotAPI.stopSystem();
    } catch (e) {
      console.error("Failed to stop system:", e);
    }
  }

  function getLifecycleColor(stage: string): string {
    switch (stage) {
      case "running":
        return "bg-green-500";
      case "paused_by_user":
        return "bg-orange-500";
      case "paused_by_system":
        return "bg-yellow-500";
      case "stopping":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  }

  function formatLifecycleStage(stage: string): string {
    return toTitleCase(stage.replaceAll("_", " "))
  }

  function formatSortingState(state: string): string {
    return toTitleCase(state.replaceAll("_", " "))
  }
</script>

<section class="bg-white border border-gray-200 p-5">
  <h2 class="text-xl font-semibold text-gray-800 mb-5 pb-3 border-b border-gray-100">
    System Status
  </h2>

  {#if status}
    <div class="space-y-3">
      <div class="flex justify-between items-center">
        <label class="text-gray-600 font-medium">Lifecycle:</label>
        <span
          class="px-3 py-1 text-white text-xs font-semibold {getLifecycleColor(
            status.lifecycle_stage,
          )}"
        >
          {formatLifecycleStage(status.lifecycle_stage)}
        </span>
      </div>

      <div class="flex justify-between items-center">
        <label class="text-gray-600 font-medium">Sorting State:</label>
        <span class="text-gray-800">
          {formatSortingState(status.sorting_state)}
        </span>
      </div>

      <div class="flex justify-between items-center">
        <label class="text-gray-600 font-medium">Objects in Frame:</label>
        <span class="text-gray-800 font-mono">{status.objects_in_frame}</span>
      </div>

      <div class="flex justify-between items-center">
        <label class="text-gray-600 font-medium">Conveyor Speed:</label>
        <span class="text-gray-800 font-mono">
          {status.conveyor_speed?.toFixed(4) || "Unknown"} cm/ms
        </span>
      </div>

      <div class="mt-5 pt-5 border-t border-gray-100">
        {#if status.lifecycle_stage === "paused_by_user" || status.lifecycle_stage === "paused_by_system"}
          <button
            onclick={startSystem}
            class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded transition-colors"
          >
            Start System
          </button>
        {:else if status.lifecycle_stage === "running"}
          <button
            onclick={stopSystem}
            class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded transition-colors"
          >
            Stop System
          </button>
        {/if}
      </div>
    </div>
  {:else}
    <div class="text-gray-500 italic">No status data available</div>
  {/if}
</section>
