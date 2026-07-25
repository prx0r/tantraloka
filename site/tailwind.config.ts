import type { Config } from 'tailwindcss'
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        ink: '#1a1a2e',
        parchment: '#f5f0e8',
        gold: '#c9a84c',
        rust: '#8b4513',
        deep: '#16213e',
        muted: '#6b7280',
      },
    },
  },
  plugins: [],
}
export default config
