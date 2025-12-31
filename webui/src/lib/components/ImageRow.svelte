<script lang="ts">
    import { ImageService } from "$lib/services/ImageService";
    import type { Image } from "$lib/services/models";


    type Props ={
        image:Image
    }
    let {image}:Props=$props();
    const imageService =  ImageService.getInstance();

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

{#if image}
<tr class="hover:bg-gray-50">
    <td class="border border-gray-300 px-4 py-2">
        <img
            src={imageService.getImageUrl(image.id)}
            alt="Preview"
            class="h-12 w-auto object-cover rounded"
        />
    </td>
    <td class="border border-gray-300 px-4 py-2 font-mono text-sm">{image.id}</td>
    <td class="border border-gray-300 px-4 py-2 align-top max-w-xs">
        {#if image.job}
            <div class="text-sm font-semibold truncate">{image.job.job_id || 'job'}</div>
            {#if image.job.completed}
                <div class="text-xs text-green-600">Completed {formatDate(image.job.completed_at!)}</div>
            {/if}

            {#if image.job.progress && Object.keys(image.job.progress).length > 0}
                <div class="mt-2 space-y-2">
                    {#each Object.entries(image.job.progress) as [label, val] (label)}
                        <div>
                            <div class="text-xs text-gray-600 flex justify-between mb-1">
                                <span class="truncate">{label}</span>
                                <span class="ml-2">{Math.round(val)}%</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded h-2">
                                <div class="bg-blue-500 h-2 rounded" style="width: {Math.min(Math.max(val, 0), 100)}%;"></div>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        {:else}
            -
        {/if}
    </td>
    <td class="border border-gray-300 px-4 py-2">{formatDate(image.created_at)}</td>
    <td class="border border-gray-300 px-4 py-2">{image.resolution || '-'}</td>
    <td class="border border-gray-300 px-4 py-2">{formatSize(image.size)}</td>
</tr>
{/if}