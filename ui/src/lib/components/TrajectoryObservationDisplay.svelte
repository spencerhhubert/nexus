<script lang="ts">
  import type { Writable } from "svelte/store";

  interface Props {
    pageState: Writable<any>;
  }

  let { pageState }: Props = $props();
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    Trajectories & Observations
  </h2>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
    <!-- Trajectories -->
    <div>
      <h3 class="text-lg font-medium text-foreground-light dark:text-foreground-dark mb-3">
        Trajectories ({$pageState.trajectories.length})
      </h3>
      {#if $pageState.trajectories.length > 0}
        <div class="space-y-2 max-h-64 overflow-y-auto">
          {#each $pageState.trajectories as trajectory (trajectory.trajectory_id)}
            <div class="bg-surface-100 dark:bg-surface-700 p-3 text-sm">
              <div class="font-mono text-xs text-surface-600 dark:text-surface-400">
                {trajectory.trajectory_id.slice(0, 8)}...
              </div>
              <div class="flex justify-between items-center mt-1">
                <span class="text-foreground-light dark:text-foreground-dark">
                  {trajectory.lifecycle_stage}
                </span>
                <span class="text-xs text-surface-500 dark:text-surface-400">
                  {trajectory.observation_ids.length} obs
                </span>
              </div>
              {#if trajectory.consensus_classification}
                <div class="text-xs text-surface-600 dark:text-surface-400 mt-1">
                  Class: {trajectory.consensus_classification}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-surface-500 dark:text-surface-400 italic">No trajectories</div>
      {/if}
    </div>

    <!-- Observations -->
    <div>
      <h3 class="text-lg font-medium text-foreground-light dark:text-foreground-dark mb-3">
        Observations ({$pageState.observations.length})
      </h3>
      {#if $pageState.observations.length > 0}
        <div class="space-y-2 max-h-64 overflow-y-auto">
          {#each $pageState.observations as observation (observation.observation_id)}
            <div class="bg-surface-100 dark:bg-surface-700 p-3 text-sm">
              <div class="font-mono text-xs text-surface-600 dark:text-surface-400">
                {observation.observation_id.slice(0, 8)}...
              </div>
              <div class="flex justify-between items-center mt-1">
                <span class="text-foreground-light dark:text-foreground-dark">
                  ({observation.center_x_percent.toFixed(2)}, {observation.center_y_percent.toFixed(2)})
                </span>
                <span class="text-xs text-surface-500 dark:text-surface-400">
                  {new Date(observation.captured_at_ms).toLocaleTimeString()}
                </span>
              </div>
              {#if observation.trajectory_id}
                <div class="text-xs text-surface-600 dark:text-surface-400 mt-1">
                  Traj: {observation.trajectory_id.slice(0, 8)}...
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-surface-500 dark:text-surface-400 italic">No observations</div>
      {/if}
    </div>
  </div>
</section>