/**
 * Data models for the Imagomortis services
 */

/**
 * Image metadata returned by the API
 */

export interface Job {
	job_id?: string;
	completed?: boolean;
	completed_at?: string | null;
	progress?: Record<string, number> | null;
	error?: string;
	failed?: boolean;
	failed_at?: string | null;
}

export interface Image {
	id: string;
	created_at: string | null;
	resolution: string | null;
	size: string | null;
	job?: Job | null;
}

/**
 * Response from the upload service
 */
export interface UploadResponse {
	uuid: string;
	filename: string;
}
