# Bears Part Scout

Auto parts search tool that finds deals from Craigslist, Facebook Marketplace, and eBay.

## Files

- `index.html` - Main web interface
- `apify_integration.js` - Scraper that runs on GitHub Actions
- `search_results.json` - Cached search results
- `config.json` - Search configuration

## How It Works

1. GitHub Actions runs `apify_integration.js` every 6 hours
2. Scrapes Craigslist, FB Marketplace, eBay for parts deals
3. Results saved to search_results.json
4. Website fetches results from GitHub

## Setup

1. Get Apify API token
2. Add to GitHub secrets: APIFY_TOKEN
3. Deploy to Netlify or hosting provider
