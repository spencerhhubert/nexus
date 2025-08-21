export interface GlobalUIConfig {
  observations: {
    maxCount: number;
    maxAgeMs: number;
  };
  trajectories: {
    maxCount: number;
    maxAgeMs: number;
  };
}

export const DEFAULT_GLOBAL_CONFIG: GlobalUIConfig = {
  observations: {
    maxCount: 1000,
    maxAgeMs: 5 * 60 * 1000, // 5 minutes
  },
  trajectories: {
    maxCount: 100,
    maxAgeMs: 10 * 60 * 1000, // 10 minutes
  },
};

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
