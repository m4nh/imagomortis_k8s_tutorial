import { getContext, setContext } from 'svelte';

export interface AppConfig {
	uploadServiceUrl: string;
	apiServiceUrl: string;
}

const CONFIG_KEY = 'app-config';

export function setConfig(config: AppConfig) {
	setContext(CONFIG_KEY, config);
}

export function getConfig(): AppConfig {
	return getContext<AppConfig>(CONFIG_KEY);
}

// For use outside of components (in service files)
let globalConfig: AppConfig | null = null;

export function initGlobalConfig(config: AppConfig) {
	globalConfig = config;
}

export function getGlobalConfig(): AppConfig {
	if (!globalConfig) {
		throw new Error('Config not initialized. Make sure +layout.svelte has loaded.');
	}
	return globalConfig;
}
