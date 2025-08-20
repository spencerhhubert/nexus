<script lang="ts">
  import type { Writable } from "svelte/store";
  import { robotAPI } from "../api";
  import { logger } from "../logger";
  import { toTitleCase } from "$lib/util";

  interface Props {
    pageState: Writable<any>;
  }

  let { pageState }: Props = $props();

  async function startSystem() {
    try {
      await robotAPI.startSystem();
    } catch (e) {
      logger.error(0, "Failed to start system:", e);
    }
  }

  async function stopSystem() {
    try {
      await robotAPI.stopSystem();
    } catch (e) {
      logger.error(0, "Failed to stop system:", e);
    }
  }

  function getLifecycleColor(stage: string): string {
    switch (stage) {
      case "running":
        return "bg-success-500";
      case "paused_by_user":
        return "bg-warning-500";
      case "paused_by_system":
        return "bg-warning-600";
      case "stopping":
        return "bg-error-500";
      default:
        return "bg-surface-500";
    }
  }

  function formatLifecycleStage(stage: string): string {
    return toTitleCase(stage.replaceAll("_", " "))
  }

  function formatSortingState(state: string): string {
    return toTitleCase(state.replaceAll("_", " "))
  }
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    System Status
  </h2>

  {#if $pageState.status}
    <div class="space-y-3">
      <div class="flex justify-between items-center">
        <span class="text-surface-600 dark:text-surface-400 font-medium">Lifecycle:</span>
        <span
          class="px-3 py-1 text-white text-xs font-semibold {getLifecycleColor(
            $pageState.status.lifecycle_stage,
          )}"
        >
          {formatLifecycleStage($pageState.status.lifecycle_stage)}
        </span>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-surface-600 dark:text-surface-400 font-medium">Sorting State:</span>
        <span class="text-foreground-light dark:text-foreground-dark">
          {formatSortingState($pageState.status.sorting_state)}
        </span>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-surface-600 dark:text-surface-400 font-medium">Objects in Frame:</span>
        <span class="text-foreground-light dark:text-foreground-dark font-mono">{$pageState.status.objects_in_frame}</span>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-surface-600 dark:text-surface-400 font-medium">Speed (1s avg):</span>
        <span class="text-foreground-light dark:text-foreground-dark font-mono">
          {$pageState.status.average_speed_1s ? ($pageState.status.average_speed_1s * 10).toFixed(3) : "Unknown"} m/s
        </span>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-surface-600 dark:text-surface-400 font-medium">Speed (5s avg):</span>
        <span class="text-foreground-light dark:text-foreground-dark font-mono">
          {$pageState.status.average_speed_5s ? ($pageState.status.average_speed_5s * 10).toFixed(3) : "Unknown"} m/s
        </span>
      </div>

      <div class="mt-5 pt-5 border-t border-surface-200 dark:border-surface-700">
        {#if $pageState.status.lifecycle_stage === "paused_by_user" || $pageState.status.lifecycle_stage === "paused_by_system"}
          <button
            onclick={startSystem}
            class="w-full bg-success-600 hover:bg-success-700 text-white font-semibold py-3 px-4 rounded transition-colors"
          >
            Start System
          </button>
        {:else if $pageState.status.lifecycle_stage === "running"}
          <button
            onclick={stopSystem}
            class="w-full bg-error-600 hover:bg-error-700 text-white font-semibold py-3 px-4 rounded transition-colors"
          >
            Stop System
          </button>
        {/if}
      </div>
    </div>
  {:else}
    <div class="text-surface-500 dark:text-surface-400 italic">No status data available</div>
  {/if}
</section>
