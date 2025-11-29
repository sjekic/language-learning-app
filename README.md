# Language Learning App - UI Only

A beautiful, interactive language learning story generator built with React, TypeScript, and Tailwind CSS.

## Features

- 📚 **Story Generator** - Create custom stories based on language level (A1-C1), genre, and custom prompts
- 🎯 **Interactive Reading** - Read stories page-by-page with smooth navigation
- 📝 **Vocabulary Tracker** - Hover over words to collect them in your personal vocabulary list
- 🎨 **Modern UI** - Clean, responsive design with smooth animations
- 🌍 **Multiple Languages** - Support for English, Spanish, French, German, Italian, Japanese, and Chinese

## Tech Stack

- **Frontend**: React 19, TypeScript
- **Routing**: React Router v7
- **Styling**: Tailwind CSS 4
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Build Tool**: Vite

## Getting Started

### Prerequisites

- Node.js 20.19+ or 22.12+
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd language-learning-app
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser to `http://localhost:5173`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── components/     # Reusable UI components
├── layouts/        # Layout components (Auth, Main)
├── pages/          # Page components
├── lib/            # Utility functions
└── assets/         # Static assets
```

## Features in Detail

### Story Generation
- Select target language and CEFR level (A1-C1)
- Choose from multiple genres (Fantasy, Sci-Fi, Adventure, Mystery, Slice of Life)
- Write custom prompts to guide story creation
- Generates 10-page stories (currently using mock data)

### Interactive Reading
- Page-by-page navigation
- Hover over any word to add it to your vocabulary
- Clean, distraction-free reading experience
- Responsive design for all devices

### Vocabulary Collection
- Automatically collects words you hover over
- Displays in a sidebar vocabulary list
- Removes punctuation for cleaner word storage

## Current Limitations

- **Mock AI**: Stories are currently generated using mock data, not real AI
- **No Persistence**: Data is stored in browser memory only (cleared on refresh)
- **No Authentication**: Login/signup pages are UI-only mockups
- **No Translations**: Vocabulary sidebar doesn't provide translations yet

## Future Enhancements

- Real AI story generation (OpenAI, Anthropic, Google Gemini)
- User authentication and profiles
- Data persistence (database integration)
- Word translations and definitions
- Audio narration
- Comprehension quizzes
- Progress tracking and analytics

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
