import { getGlobalConfig } from '$lib/config';
import type { UploadResponse } from './models';

/**
 * Service class for interacting with the upload server
 */
export class UploadService {
	private baseUrl: string;
	private static instance: UploadService;

	/**
	 * Get the singleton instance of UploadService
	 * @returns The UploadService instance
	 */
	static getInstance(): UploadService {
		if (!UploadService.instance) {
			UploadService.instance = new UploadService();
		}
		return UploadService.instance;
	}

	private constructor(baseUrl?: string) {
		this.baseUrl = baseUrl || getGlobalConfig().uploadServiceUrl;
	}

	/**
	 * Upload an image file to the server
	 * @param file - The image file to upload
	 * @returns Promise with the upload response containing uuid and filename
	 * @throws Error if the upload fails or file is not an image
	 */
	async uploadImage(file: File): Promise<UploadResponse> {
		if (!file.type.startsWith('image/')) {
			throw new Error('File must be an image');
		}

		const formData = new FormData();
		formData.append('file', file);

		const response = await fetch(`${this.baseUrl}/upload`, {
			method: 'POST',
			body: formData
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
			throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
		}

		return response.json();
	}
}
