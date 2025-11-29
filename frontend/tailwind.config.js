/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0f',
          800: '#13131a',
          700: '#1a1a24',
        },
        neon: {
          purple: '#a855f7',
          cyan: '#06b6d4',
          pink: '#ec4899',
        },
        primary: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
          950: '#2e1065',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-cosmic': 'linear-gradient(to bottom, #0a0a0f, #1a1a24, #2d1b69)',
        'gradient-aurora': 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)',
      },
    },
  },
  plugins: [],
}
