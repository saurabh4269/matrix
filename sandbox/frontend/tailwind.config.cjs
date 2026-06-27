/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#FBF8F2',
        card: '#FFFFFF',
        ink: {
          DEFAULT: '#1A1A1A',
          secondary: '#5A5A5A',
          tertiary: '#9A9A9A',
        },
        hairline: '#EAE6DC',
        action: '#1F2933',
        accent: '#B8843B',
        signal: {
          verified: '#B8843B',
          claimed: '#C9C2B1',
          concern: '#A85B3A',
        },
      },
      fontFamily: {
        serif: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        display: ['clamp(2.5rem, 5vw + 1rem, 4.5rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        heading: ['clamp(1.5rem, 2vw + 0.5rem, 2rem)', { lineHeight: '1.2', letterSpacing: '-0.01em' }],
      },
      maxWidth: {
        reading: '64ch',
      },
    },
  },
  plugins: [],
}
