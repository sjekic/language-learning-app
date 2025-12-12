const BOOK_SERVICE_URL = import.meta.env.VITE_BOOK_SERVICE_URL || 'http://localhost:8003';

export interface GenerateStoryRequest {
    language: string;
    level: string;
    genre: string;
    prompt: string;
}

export interface StoryStatus {
    story_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    story?: {
        title: string;
        content: string[];
    };
    chunks_completed?: number;
}

export async function generateStory(request: GenerateStoryRequest): Promise<{ story_id: string }> {
    const response = await fetch(`${BOOK_SERVICE_URL}/api/books/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        throw new Error('Failed to start story generation');
    }

    return response.json();
}

export async function getStoryStatus(storyId: string): Promise<StoryStatus> {
    const response = await fetch(`${BOOK_SERVICE_URL}/api/books/${storyId}/status`);

    if (!response.ok) {
        throw new Error('Failed to get story status');
    }

    return response.json();
}

export async function pollStoryCompletion(
    storyId: string,
    onProgress?: (status: StoryStatus) => void,
    intervalMs: number = 3000,
    maxAttempts: number = 100
): Promise<StoryStatus> {
    return new Promise((resolve, reject) => {
        let attempts = 0;

        const poll = async () => {
            try {
                const status = await getStoryStatus(storyId);
                
                if (onProgress) onProgress(status);

                if (status.status === 'completed') {
                    resolve(status);
                    return;
                }

                if (status.status === 'failed') {
                    reject(new Error('Story generation failed'));
                    return;
                }

                attempts++;
                if (attempts >= maxAttempts) {
                    reject(new Error('Story generation timed out'));
                    return;
                }

                setTimeout(poll, intervalMs);
            } catch (error) {
                reject(error);
            }
        };

        poll();
    });
}