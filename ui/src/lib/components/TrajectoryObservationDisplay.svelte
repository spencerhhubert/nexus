<script lang="ts">
  import type { Writable } from "svelte/store";
  import type { TrajectoryData } from "../types";
  import { createEventDispatcher } from 'svelte';

  interface Props {
    pageState: Writable<any>;
  }

  let { pageState }: Props = $props();
  
  const dispatch = createEventDispatcher<{
    selectTrajectory: TrajectoryData;
  }>();

  let trajectoryContainer = $state<HTMLDivElement>();
  let selectedTrajectoryId = $state<string | null>(null);

  // Auto-scroll to bottom when new trajectories arrive
  $effect(() => {
    if (trajectoryContainer && $pageState.trajectories.length > 0) {
      trajectoryContainer.scrollTop = trajectoryContainer.scrollHeight;
    }
  });

  function selectTrajectory(trajectory: TrajectoryData) {
    selectedTrajectoryId = trajectory.trajectory_id;
    dispatch('selectTrajectory', trajectory);
  }
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    Recent Trajectories ({$pageState.trajectories.length})
  </h2>

  {#if $pageState.trajectories.length > 0}
    <div 
      bind:this={trajectoryContainer}
      class="space-y-2 max-h-96 overflow-y-auto pr-2"
    >
      {#each $pageState.trajectories as trajectory (trajectory.trajectory_id)}
        <button
          onclick={() => selectTrajectory(trajectory)}
          class="w-full text-left bg-surface-100 dark:bg-surface-700 p-3 text-sm border-2 transition-colors {
            selectedTrajectoryId === trajectory.trajectory_id 
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
              : 'border-transparent hover:border-surface-300 dark:hover:border-surface-600'
          }"
        >
          <div class="font-mono text-xs text-surface-600 dark:text-surface-400">
            {trajectory.trajectory_id.slice(0, 8)}...
          </div>
          <div class="flex justify-between items-center mt-1">
            <span class="text-foreground-light dark:text-foreground-dark">
              {trajectory.lifecycle_stage.replace(/_/g, ' ')}
            </span>
            <span class="text-xs text-surface-500 dark:text-surface-400">
              {trajectory.observation_ids.length} obs
            </span>
          </div>
          {#if trajectory.consensus_classification}
            <div class="text-xs text-surface-600 dark:text-surface-400 mt-1 truncate">
              {trajectory.consensus_classification}
            </div>
          {/if}
          <div class="text-xs text-surface-500 dark:text-surface-400 mt-1">
            {new Date(trajectory.updated_at).toLocaleTimeString()}
          </div>
        </button>
      {/each}
    </div>
  {:else}
    <div class="text-center text-surface-500 dark:text-surface-400 italic py-16">
      No trajectories yet
    </div>
  {/if}
</section>