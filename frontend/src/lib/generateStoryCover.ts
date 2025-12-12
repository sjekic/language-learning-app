// Generate beautiful gradient cover images for stories

export type StoryGenre = 'fantasy' | 'sci-fi' | 'adventure' | 'mystery' | 'slice-of-life';

interface GradientConfig {
    colors: string[];
    angle: number;
}

const genreGradients: Record<StoryGenre, GradientConfig> = {
    fantasy: {
        colors: ['#667eea', '#764ba2', '#f093fb'],
        angle: 135,
    },
    'sci-fi': {
        colors: ['#06b6d4', '#3b82f6', '#8b5cf6'],
        angle: 180,
    },
    adventure: {
        colors: ['#f59e0b', '#ef4444', '#ec4899'],
        angle: 45,
    },
    mystery: {
        colors: ['#6366f1', '#8b5cf6', '#a855f7'],
        angle: 90,
    },
    'slice-of-life': {
        colors: ['#10b981', '#06b6d4', '#3b82f6'],
        angle: 225,
    },
};

export const generateStoryCover = (
    genre: StoryGenre,
    _title: string,
    width: number = 400,
    height: number = 600
): string => {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    if (!ctx) return '';

    const gradient = genreGradients[genre] || genreGradients.fantasy;

    // Create gradient background
    const angle = gradient.angle * (Math.PI / 180);
    const x1 = width / 2 + Math.cos(angle) * width / 2;
    const y1 = height / 2 + Math.sin(angle) * height / 2;
    const x2 = width / 2 - Math.cos(angle) * width / 2;
    const y2 = height / 2 - Math.sin(angle) * height / 2;

    const grd = ctx.createLinearGradient(x1, y1, x2, y2);
    gradient.colors.forEach((color, index) => {
        grd.addColorStop(index / (gradient.colors.length - 1), color);
    });

    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, width, height);

    // Add abstract shapes/orbs for visual interest
    addAbstractShapes(ctx, width, height);

    // Add subtle noise texture
    addNoiseTexture(ctx, width, height);

    return canvas.toDataURL('image/png');
};

function addAbstractShapes(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number
) {
    // Large orb
    const orb1 = ctx.createRadialGradient(
        width * 0.7,
        height * 0.3,
        0,
        width * 0.7,
        height * 0.3,
        width * 0.4
    );
    orb1.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
    orb1.addColorStop(0.5, 'rgba(255, 255, 255, 0.05)');
    orb1.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = orb1;
    ctx.fillRect(0, 0, width, height);

    // Small orb
    const orb2 = ctx.createRadialGradient(
        width * 0.2,
        height * 0.8,
        0,
        width * 0.2,
        height * 0.8,
        width * 0.25
    );
    orb2.addColorStop(0, 'rgba(255, 255, 255, 0.1)');
    orb2.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = orb2;
    ctx.fillRect(0, 0, width, height);
}

function addNoiseTexture(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number
) {
    const imageData = ctx.getImageData(0, 0, width, height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
        const noise = Math.random() * 10 - 5;
        data[i] += noise;
        data[i + 1] += noise;
        data[i + 2] += noise;
    }

    ctx.putImageData(imageData, 0, 0);
}

// Preload function to avoid runtime generation lag
export const preloadStoryCover = (genre: StoryGenre, title: string): void => {
    // Generate in background
    setTimeout(() => {
        generateStoryCover(genre, title);
    }, 0);
};
