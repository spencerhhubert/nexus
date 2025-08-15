<script lang="ts">
  import { recentTrajectories } from '$lib/stores/app';
  import type { TrajectoryData } from '$lib/stores/app';

  function formatTimestamp(timestamp: number): string {
    return new Date(timestamp).toLocaleTimeString();
  }

  function getClassificationDisplay(trajectory: TrajectoryData): string {
    return trajectory.consensus_classification || 'unknown';
  }

  function getCategoryDisplay(trajectory: TrajectoryData): string {
    return 'unknown'; // TODO: Add category mapping
  }
</script>

<div class="space-y-2 max-h-64 overflow-y-auto">
  <h3 class="text-sm font-medium text-gray-700 mb-2">Recent Trajectories</h3>
  
  {#if $recentTrajectories.length === 0}
    <div class="text-sm text-gray-500 italic">No trajectories yet</div>
  {:else}
    {#each $recentTrajectories as trajectory (trajectory.trajectory_id)}
      <div class="bg-gray-50 p-3 rounded border text-sm">
        <div class="flex justify-between items-start mb-1">
          <span class="font-medium text-gray-800">
            {getClassificationDisplay(trajectory)}
          </span>
          <span class="text-xs text-gray-500">
            {formatTimestamp(trajectory.updated_at)}
          </span>
        </div>
        
        <div class="text-xs text-gray-600 space-y-1">
          <div>Stage: {trajectory.lifecycle_stage}</div>
          <div>Category: {getCategoryDisplay(trajectory)}</div>
          <div>Observations: {trajectory.observation_ids.length}</div>
          {#if trajectory.target_bin}
            <div>Target bin: ({trajectory.target_bin.bin_x}, {trajectory.target_bin.bin_y})</div>
          {/if}
        </div>
      </div>
    {/each}
  {/if}
</div>