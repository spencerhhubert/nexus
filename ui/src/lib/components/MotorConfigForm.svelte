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
      id="mainConveyorSpeed"
      label="Main Conveyor Speed"
      bind:value={runtimeParams.mainConveyorSpeed}
      min={-255}
      max={255}
    />
    <NumberInput
      id="feederConveyorSpeed"
      label="Feeder Conveyor Speed"
      bind:value={runtimeParams.feederConveyorSpeed}
      min={-255}
      max={255}
    />
    <NumberInput
      id="firstVibrationHopperMotorSpeed"
      label="First Vibration Hopper Speed"
      bind:value={runtimeParams.firstVibrationHopperMotorSpeed}
      min={-255}
      max={255}
    />
    <NumberInput
      id="secondVibrationHopperMotorSpeed"
      label="Second Vibration Hopper Speed"
      bind:value={runtimeParams.secondVibrationHopperMotorSpeed}
      min={-255}
      max={255}
    />
  </div>

  <div class="border-t border-gray-200 dark:border-gray-600 pt-4">
    <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Pulse/Pause Timing (ms)</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <NumberInput
        id="firstVibrationHopperMotorPulseMs"
        label="First Hopper Pulse Duration"
        bind:value={runtimeParams.firstVibrationHopperMotorPulseMs}
        min={0}
        max={10000}
      />
      <NumberInput
        id="firstVibrationHopperMotorPauseMs"
        label="First Hopper Pause Duration"
        bind:value={runtimeParams.firstVibrationHopperMotorPauseMs}
        min={0}
        max={10000}
      />
      <NumberInput
        id="secondVibrationHopperMotorPulseMs"
        label="Second Hopper Pulse Duration"
        bind:value={runtimeParams.secondVibrationHopperMotorPulseMs}
        min={0}
        max={10000}
      />
      <NumberInput
        id="secondVibrationHopperMotorPauseMs"
        label="Second Hopper Pause Duration"
        bind:value={runtimeParams.secondVibrationHopperMotorPauseMs}
        min={0}
        max={10000}
      />
      <NumberInput
        id="feederConveyorPulseMs"
        label="Feeder Conveyor Pulse Duration"
        bind:value={runtimeParams.feederConveyorPulseMs}
        min={0}
        max={10000}
      />
      <NumberInput
        id="feederConveyorPauseMs"
        label="Feeder Conveyor Pause Duration"
        bind:value={runtimeParams.feederConveyorPauseMs}
        min={0}
        max={10000}
      />
    </div>
  </div>
</div>