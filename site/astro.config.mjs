import { defineConfig } from 'astro/config';

// GitHub Pages project site: https://<user>.github.io/<repo>/
const repo = process.env.SITE_BASE ?? '/keystone-fantasy';
const site = process.env.SITE_URL ?? 'https://cole-wyman-1.github.io';

export default defineConfig({
  site,
  base: repo,
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory' },
});
