/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./pages/**/*.{ts,tsx,js,jsx}', './components/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      animation: {
        'blob': 'blob 7s infinite',
        'fade-in': 'fade-in 0.8s ease-out',
        'fade-in-delay': 'fade-in 0.8s ease-out 0.2s both',
        'fade-in-delay-2': 'fade-in 0.8s ease-out 0.4s both',
        'fade-in-delay-3': 'fade-in 0.8s ease-out 0.6s both',
        'spin-slow': 'spin-slow 3s linear infinite',
        'progress': 'progress 2s ease-in-out infinite',
      },
      keyframes: {
        blob: {
          '0%, 100%': {
            transform: 'translate(0, 0) scale(1)',
          },
          '33%': {
            transform: 'translate(30px, -50px) scale(1.1)',
          },
          '66%': {
            transform: 'translate(-20px, 20px) scale(0.9)',
          },
        },
        'fade-in': {
          from: {
            opacity: '0',
            transform: 'translateY(20px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        'spin-slow': {
          from: {
            transform: 'rotate(0deg)',
          },
          to: {
            transform: 'rotate(360deg)',
          },
        },
        progress: {
          '0%': {
            width: '0%',
          },
          '50%': {
            width: '70%',
          },
          '100%': {
            width: '100%',
          },
        },
      },
    },
  },
  plugins: [],
};

