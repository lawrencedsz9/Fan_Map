/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        ghibli: {
          // Soft backgrounds inspired by Studio Ghibli
          bg: '#F4F1E8',
          light: '#FDFBF7',
          darker: '#E8E4D8',
          // Forest greens
          forest: '#6B8E6F',
          leaf: '#7BA67F',
          sage: '#9CB5A0',
          // Warm earth tones
          cream: '#F7F2E8',
          sand: '#D4C4B0',
          earth: '#8B7355',
          // Sky and water blues
          sky: '#87CEEB',
          water: '#7AAFB8',
          deep_blue: '#4A6FA5',
          // Warm accents
          peach: '#E89B7A',
          coral: '#D97A62',
          gold: '#D4A574',
          // Text colors
          dark: '#1F1F1F',
          text: '#3C3C3C',
          white: '#FFFFFF',
        },
      },
      fontFamily: {
        sans: ['Rubik', 'system-ui', 'sans-serif'],
        display: ['Fredoka One', 'sans-serif'],
        heading: ['Righteous', 'sans-serif'],
        mono: ['Courier Prime', 'monospace'],
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
        '6': '6px',
      },
      boxShadow: {
        'ghibli': '2px 2px 4px rgba(139, 69, 19, 0.15)',
        'ghibli-lg': '4px 4px 8px rgba(139, 69, 19, 0.2)',
        'ghibli-xl': '6px 6px 12px rgba(139, 69, 19, 0.25)',
        'ghibli-forest': '2px 2px 4px #6B8E6F',
        'ghibli-peach': '2px 2px 4px #E89B7A',
        'ghibli-water': '2px 2px 4px #7AAFB8',
      },
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.2)' },
        },
        pop: {
          '0%': { transform: 'scale(0)', opacity: '0' },
          '50%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      animation: {
        pulse: 'pulse 0.5s infinite',
        pop: 'pop 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      },
    },
  },
  plugins: [],
}
