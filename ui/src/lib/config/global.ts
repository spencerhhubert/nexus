export interface GlobalUIConfig {}

export const DEFAULT_GLOBAL_CONFIG: GlobalUIConfig = {};

function createGlobalConfigStore() {
  let config = DEFAULT_GLOBAL_CONFIG;

  return {
    get: () => config,
    update: (newConfig: Partial<GlobalUIConfig>) => {
      config = { ...config, ...newConfig };
    },
  };
}

export const globalConfig = createGlobalConfigStore();
