import plugin from 'tailwindcss/plugin';

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        soft: '0 20px 60px -30px rgba(15, 23, 42, 0.35)',
      },
      backgroundImage: {
        grid: 'radial-gradient(circle at 1px 1px, rgba(148, 163, 184, 0.16) 1px, transparent 0)',
      },
    },
  },
  plugins: [
    plugin(({ addVariant }) => {
      addVariant('light', '.light &');
    }),
  ],
};
