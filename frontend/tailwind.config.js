/**
 * ==============================================================================
 * Tailwind CSS Configuration
 * ==============================================================================
 * 
 * Tailwind CSS is a utility-first CSS framework that provides:
 * - Pre-defined utility classes for styling
 * - Responsive design utilities
 * - Dark mode support
 * - Custom theme configuration
 * 
 * This file customizes the default Tailwind theme with:
 * - Custom colors for bullish/bearish indicators
 * - Extended animations for alerts
 * - Custom breakpoints for responsive design
 * ==============================================================================
 */

/** @type {import('tailwindcss').Config} */
export default {
  // Files to scan for class names
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  
  // Dark mode configuration
  // 'class' means dark mode is toggled via a class on the HTML element
  darkMode: 'class',
  
  theme: {
    extend: {
      // Custom colors for stock market indicators
      colors: {
        // Bullish (positive) colors - green shades
        bullish: {
          light: '#86efac',   // Light green for backgrounds
          DEFAULT: '#22c55e', // Standard green
          dark: '#166534',    // Dark green for text
        },
        // Bearish (negative) colors - red shades
        bearish: {
          light: '#fca5a5',   // Light red for backgrounds
          DEFAULT: '#ef4444', // Standard red
          dark: '#991b1b',    // Dark red for text
        },
        // Neutral colors - gray shades
        neutral: {
          light: '#e5e7eb',
          DEFAULT: '#9ca3af',
          dark: '#4b5563',
        },
        // Dashboard background colors
        dashboard: {
          bg: '#0f172a',      // Dark blue background
          card: '#1e293b',    // Card background
          border: '#334155',  // Border color
        },
      },
      
      // Custom animations
      animation: {
        // Pulse animation for live indicators
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        // Fade in animation for new data
        'fade-in': 'fadeIn 0.3s ease-in-out',
        // Slide in from right (for alerts)
        'slide-in-right': 'slideInRight 0.3s ease-out',
        // Number counting animation
        'number-change': 'numberPulse 0.5s ease-in-out',
      },
      
      // Keyframes for custom animations
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        numberPulse: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
        },
      },
      
      // Custom box shadows for cards
      boxShadow: {
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
      },
      
      // Custom fonts (optional)
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
    },
  },
  
  // Tailwind plugins (none needed for this project)
  plugins: [],
};
