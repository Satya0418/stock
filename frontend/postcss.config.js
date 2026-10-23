/**
 * ==============================================================================
 * PostCSS Configuration
 * ==============================================================================
 * 
 * PostCSS is a tool for transforming CSS with JavaScript plugins.
 * We use it with Tailwind CSS to:
 * - Process Tailwind directives (@tailwind, @apply, etc.)
 * - Add vendor prefixes with Autoprefixer
 * ==============================================================================
 */

export default {
  plugins: {
    // Tailwind CSS plugin processes Tailwind directives
    tailwindcss: {},
    
    // Autoprefixer adds vendor prefixes for browser compatibility
    autoprefixer: {},
  },
};
