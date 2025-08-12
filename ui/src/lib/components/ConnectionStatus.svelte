<script lang="ts">
  interface Props {
    isOnline: boolean;
    isLoading: boolean;
  }

  let { isOnline, isLoading }: Props = $props();

  function getStatusText(): string {
    if (isLoading) return "Connecting...";
    return isOnline ? "Connected" : "Offline";
  }

  function getStatusClasses(): string {
    if (isLoading) return "bg-yellow-100 text-yellow-800";
    return isOnline
      ? "bg-green-100 text-green-800"
      : "bg-red-100 text-red-800";
  }
</script>

<div class="px-4 py-2 font-semibold {getStatusClasses()}">
  {getStatusText()}
</div>
