<script lang="ts">
  import type { MotorInfo } from "../types";
  import { robotAPI } from "../api";

  interface Props {
    motors: MotorInfo[] | null;
  }

  let { motors }: Props = $props();

  async function setMotorSpeed(motorId: string, speed: number) {
    try {
      await robotAPI.setMotorSpeed({ motor_id: motorId, speed });
    } catch (e) {
      console.error("Failed to set motor speed:", e);
    }
  }
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    Motor Controls
  </h2>

  {#if motors && motors.length > 0}
    <div class="space-y-5">
      {#each motors as motor (motor.motor_id)}
        <div class="bg-surface-100 dark:bg-surface-700 p-4">
          <h3 class="block font-semibold text-foreground-light dark:text-foreground-dark mb-3">
            {motor.display_name}
          </h3>
          <div class="grid grid-cols-[auto_1fr_auto] gap-3 items-center">
            <span class="text-sm text-surface-600 dark:text-surface-400">
              Current: {motor.current_speed}
            </span>
            <input
              type="range"
              min={motor.min_speed}
              max={motor.max_speed}
              value={motor.current_speed}
              onchange={(e) => setMotorSpeed(motor.motor_id, parseInt((e.target as HTMLInputElement).value))}
              class="flex-1 accent-primary-500"
            />
            <input
              type="number"
              min={motor.min_speed}
              max={motor.max_speed}
              value={motor.current_speed}
              onchange={(e) => setMotorSpeed(motor.motor_id, parseInt((e.target as HTMLInputElement).value))}
              class="w-20 px-2 py-1 border border-surface-300 dark:border-surface-600 bg-surface-50 dark:bg-surface-800 text-foreground-light dark:text-foreground-dark text-center"
            />
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-surface-500 dark:text-surface-400 italic">No motor data available</div>
  {/if}
</section>
