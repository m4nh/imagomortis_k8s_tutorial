import { getGlobalConfig } from '$lib/config';
import type { Image } from './models';

/**
 * Get the API service URL from the global config
 * @returns The API service URL as a string
 */
function getApiServiceUrl(): string {
	return getGlobalConfig().apiServiceUrl;
}

/**
 * Service class for interacting with the images API
 */
export class ImageService {
	private baseUrl: string;
	private static instance: ImageService;

	/**
	 * Get the singleton instance of ImageService
	 * @returns The ImageService instance
	 */
	static getInstance(): ImageService {
		if (!ImageService.instance) {
			ImageService.instance = new ImageService();
		}
		return ImageService.instance;
	}

	private constructor(baseUrl?: string) {
		this.baseUrl = baseUrl || getApiServiceUrl();
	}

	/**
	 * Get all images metadata from the server
	 * @returns Promise with array of Image objects
	 * @throws Error if the request fails
	 */
	async getImages(): Promise<Image[]> {
		const response = await fetch(`${this.baseUrl}/images`);

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch images' }));
			throw new Error(errorData.detail || `Failed to fetch images with status ${response.status}`);
		}

		return response.json();
	}

	/**
	 * Get a single image by ID
	 * @param imageId - The UUID of the image
	 * @returns Promise with the image as a Blob
	 * @throws Error if the request fails or image not found
	 */
	async getImage(imageId: string): Promise<Blob> {
		const response = await fetch(`${this.baseUrl}/images/${imageId}`);

		if (!response.ok) {
			if (response.status === 404) {
				throw new Error('Image not found');
			}
			const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch image' }));
			throw new Error(errorData.detail || `Failed to fetch image with status ${response.status}`);
		}

		return response.blob();
	}

	/**
	 * Get the URL for an image by ID (for use in img src)
	 * @param imageId - The UUID of the image
	 * @returns The URL string for the image
	 */
	getImageUrl(imageId: string): string {
		return `${this.baseUrl}/images/${imageId}?t=${Date.now()}`;
	}
}
