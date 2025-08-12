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

<section class="bg-white border border-gray-200 p-5">
  <h2 class="text-xl font-semibold text-gray-800 mb-5 pb-3 border-b border-gray-100">
    Motor Controls
  </h2>

  {#if motors && motors.length > 0}
    <div class="space-y-5">
      {#each motors as motor (motor.motor_id)}
        <div class="bg-gray-50 p-4">
          <label class="block font-semibold text-gray-700 mb-3">
            {motor.display_name}
          </label>
          <div class="grid grid-cols-[auto_1fr_auto] gap-3 items-center">
            <span class="text-sm text-gray-600">
              Current: {motor.current_speed}
            </span>
            <input
              type="range"
              min={motor.min_speed}
              max={motor.max_speed}
              value={motor.current_speed}
              onchange={(e) => setMotorSpeed(motor.motor_id, parseInt((e.target as HTMLInputElement).value))}
              class="flex-1"
            />
            <input
              type="number"
              min={motor.min_speed}
              max={motor.max_speed}
              value={motor.current_speed}
              onchange={(e) => setMotorSpeed(motor.motor_id, parseInt((e.target as HTMLInputElement).value))}
              class="w-20 px-2 py-1 border border-gray-300 text-center"
            />
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-gray-500 italic">No motor data available</div>
  {/if}
</section>
