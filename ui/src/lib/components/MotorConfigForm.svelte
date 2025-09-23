<script lang="ts">
  import NumberInput from './NumberInput.svelte';

  interface Props {
    runtimeParams: any;
  }

  let { runtimeParams }: Props = $props();
</script>

<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <NumberInput
      id="main_conveyor_speed"
      label="Main Conveyor Speed"
      bind:value={runtimeParams.main_conveyor_speed}
      min={-255}
      max={255}
    />
    <NumberInput
      id="feeder_conveyor_speed"
      label="Feeder Conveyor Speed"
      bind:value={runtimeParams.feeder_conveyor_speed}
      min={-255}
      max={255}
    />
    <NumberInput
      id="first_vibration_hopper_motor_speed"
      label="First Vibration Hopper Speed"
      bind:value={runtimeParams.first_vibration_hopper_motor_speed}
      min={-255}
      max={255}
    />
    <NumberInput
      id="second_vibration_hopper_motor_speed"
      label="Second Vibration Hopper Speed"
      bind:value={runtimeParams.second_vibration_hopper_motor_speed}
      min={-255}
      max={255}
    />
  </div>

  <div class="pt-4">
    <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Pulse/Pause Timing (ms)</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <NumberInput
        id="first_vibration_hopper_motor_pulse_ms"
        label="First Hopper Pulse Duration"
        bind:value={runtimeParams.first_vibration_hopper_motor_pulse_ms}
        min={0}
        max={10000}
      />
      <NumberInput
        id="first_vibration_hopper_motor_pause_ms"
        label="First Hopper Pause Duration"
        bind:value={runtimeParams.first_vibration_hopper_motor_pause_ms}
        min={0}
        max={10000}
      />
      <NumberInput
        id="second_vibration_hopper_motor_pulse_ms"
        label="Second Hopper Pulse Duration"
        bind:value={runtimeParams.second_vibration_hopper_motor_pulse_ms}
        min={0}
        max={10000}
      />
      <NumberInput
        id="second_vibration_hopper_motor_pause_ms"
        label="Second Hopper Pause Duration"
        bind:value={runtimeParams.second_vibration_hopper_motor_pause_ms}
        min={0}
        max={10000}
      />
      <NumberInput
        id="feeder_conveyor_pulse_ms"
        label="Feeder Conveyor Pulse Duration"
        bind:value={runtimeParams.feeder_conveyor_pulse_ms}
        min={0}
        max={10000}
      />
      <NumberInput
        id="feeder_conveyor_pause_ms"
        label="Feeder Conveyor Pause Duration"
        bind:value={runtimeParams.feeder_conveyor_pause_ms}
        min={0}
        max={10000}
      />
      <NumberInput
        id="feeder_conveyor_pulse_duration_ms"
        label="Feeder Conveyor First Feeder Empty Pulse Duration"
        bind:value={runtimeParams.feeder_conveyor_pulse_duration_ms}
        min={0}
      />
    </div>
  </div>
</div>
