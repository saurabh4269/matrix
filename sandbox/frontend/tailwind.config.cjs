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
      // Six-tier scale. Use ONLY these in the app:
      //   display  — candidate name, JD title (Fraunces 400)
      //   title    — verdict reasoning, summary headings (Fraunces 400, 22px)
      //   body     — UI text, evidence, status (Inter 400, 16px)
      //   small    — captions, labels (Inter 500, 13px)
      //   micro    — section labels (Inter 500, 11px uppercase tracked)
      fontSize: {
        display: ['clamp(2.5rem, 5vw + 1rem, 4.5rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        title:   ['1.375rem', { lineHeight: '1.6', letterSpacing: '-0.005em' }], // 22px
        body:    ['1rem',     { lineHeight: '1.6' }],                              // 16px
        small:   ['0.8125rem', { lineHeight: '1.5' }],                             // 13px
        micro:   ['0.6875rem', { lineHeight: '1.4', letterSpacing: '0.18em' }],    // 11px tracked
      },
      maxWidth: {
        reading: '64ch',
      },
    },
  },
  plugins: [],
}
