/**
 * Data models for the Imagomortis services
 */

/**
 * Image metadata returned by the API
 */
export interface Image {
	id: string;
	created_at: string | null;
	resolution: string | null;
	size: string | null;
}

/**
 * Response from the upload service
 */
export interface UploadResponse {
	uuid: string;
	filename: string;
}
