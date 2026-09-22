import { defineConfig } from 'astro/config';

// GitHub Pages project site: https://<user>.github.io/<repo>/
const repo = process.env.SITE_BASE ?? '/keystone-fantasy';
const site = process.env.SITE_URL ?? 'https://cole-wyman-1.github.io';

export default defineConfig({
  site,
  base: repo,
  output: 'static',
  trailingSlash: 'always',
  // Inline all CSS: pages are cached by browsers/CDN across frequent deploys, and a cached page
  // pointing at a hashed CSS file from an older build would render unstyled.
  build: { format: 'directory', inlineStylesheets: 'always' },
});
