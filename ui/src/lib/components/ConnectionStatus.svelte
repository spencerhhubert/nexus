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
    if (isLoading) return "bg-warning-100 text-warning-800 dark:bg-warning-900/20 dark:text-warning-300";
    return isOnline
      ? "bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300"
      : "bg-error-100 text-error-800 dark:bg-error-900/20 dark:text-error-300";
  }
</script>

<div class="px-4 py-2 {getStatusClasses()}">
  {getStatusText()}
</div>
