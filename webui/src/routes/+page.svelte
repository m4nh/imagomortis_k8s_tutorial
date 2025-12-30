<script lang="ts">
	import { onMount } from 'svelte';
	import type { Image } from '$lib/services/models';
	import { UploadService } from '$lib/services/UploadService';
	import { ImageService } from '$lib/services/ImageService';

	let images = $state<Image[]>([]);
	let isLoading = $state(false);
	let isUploading = $state(false);
	let error = $state<string | null>(null);
	let uploadError = $state<string | null>(null);
	let uploadSuccess = $state<string | null>(null);
	let uploadService: UploadService = UploadService.getInstance();
	let imageService: ImageService = ImageService.getInstance();


	async function fetchImages() {
		try {
			isLoading = true;
			error = null;
			images = await imageService.getImages();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch images';
		} finally {
			isLoading = false;
		}
	}

	async function handleUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];

		if (!file) return;

		try {
			isUploading = true;
			uploadError = null;
			uploadSuccess = null;

			const response = await uploadService.uploadImage(file);
			uploadSuccess = `Image uploaded successfully! UUID: ${response.uuid}`;

			// Refresh the images list after upload
			await fetchImages();
		} catch (e) {
			uploadError = e instanceof Error ? e.message : 'Upload failed';
		} finally {
			isUploading = false;
			// Reset the input
			input.value = '';
		}
	}

	

	onMount(() => {
		fetchImages();
	});

	

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	function formatSize(size: string | null): string {
		if (!size) return '-';
		const bytes = parseInt(size, 10);
		if (isNaN(bytes)) return size;
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}
</script>

<div class="container mx-auto p-6 max-w-4xl">
	<h1 class="text-3xl font-bold mb-8 text-center">Imago Mortis</h1>

	<!-- Upload Section -->
	<section class="mb-10 p-6 bg-gray-100 rounded-lg">
		<h2 class="text-xl font-semibold mb-4">Upload Image</h2>

		<div class="flex items-center gap-4">
			<input
				type="file"
				accept="image/*"
				onchange={handleUpload}
				disabled={isUploading}
				class="file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-500 file:text-white file:cursor-pointer hover:file:bg-blue-600 disabled:opacity-50"
			/>

			{#if isUploading}
				<span class="text-blue-600">Uploading...</span>
			{/if}
		</div>

		{#if uploadError}
			<p class="mt-3 text-red-600">{uploadError}</p>
		{/if}

		{#if uploadSuccess}
			<p class="mt-3 text-green-600">{uploadSuccess}</p>
		{/if}
	</section>

	<!-- Images Table Section -->
	<section>
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-xl font-semibold">Images</h2>
			<button
				onclick={fetchImages}
				disabled={isLoading}
				class="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
			>
				{isLoading ? 'Loading...' : 'Refresh'}
			</button>
		</div>

		{#if error}
			<p class="text-red-600 mb-4">{error}</p>
		{/if}

		<div class="overflow-x-auto">
			<table class="w-full border-collapse border border-gray-300">
				<thead>
					<tr class="bg-gray-200">
						<th class="border border-gray-300 px-4 py-2 text-left">Preview</th>
						<th class="border border-gray-300 px-4 py-2 text-left">ID</th>
						<th class="border border-gray-300 px-4 py-2 text-left">Created At</th>
						<th class="border border-gray-300 px-4 py-2 text-left">Resolution</th>
						<th class="border border-gray-300 px-4 py-2 text-left">Size</th>
					</tr>
				</thead>
				<tbody>
					{#if images.length === 0}
						<tr>
							<td colspan="5" class="border border-gray-300 px-4 py-8 text-center text-gray-500">
								{isLoading ? 'Loading images...' : 'No images found'}
							</td>
						</tr>
					{:else}
						{#each images as image (image.id)}
							<tr class="hover:bg-gray-50">
								<td class="border border-gray-300 px-4 py-2">
									<img
										src={imageService.getImageUrl(image.id)}
										alt="Preview"
										class="h-12 w-auto object-cover rounded"
									/>
								</td>
								<td class="border border-gray-300 px-4 py-2 font-mono text-sm">{image.id}</td>
								<td class="border border-gray-300 px-4 py-2">{formatDate(image.created_at)}</td>
								<td class="border border-gray-300 px-4 py-2">{image.resolution || '-'}</td>
								<td class="border border-gray-300 px-4 py-2">{formatSize(image.size)}</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>

	</section>
</div>
