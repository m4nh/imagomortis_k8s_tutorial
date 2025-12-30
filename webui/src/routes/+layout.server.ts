import { env } from '$env/dynamic/public';

export const load = async () => {
	return {
		config: {
			uploadServiceUrl: env.PUBLIC_UPLOAD_SERVICE_URL || 'http://localhost:8000',
			apiServiceUrl: env.PUBLIC_API_SERVICE_URL || 'http://localhost:8000'
		}
	};
};
