// Apify Integration - Searches Craigslist, Facebook Marketplace, eBay
// Runs via GitHub Actions every 6 hours

const Apify = require('apify');

async function runApifyScraper() {
    const searchTerm = process.argv[2] || "honda civic parts";
    const results = [];
    
    // Run Craigslist Scraper
    try {
        const craigslistInput = {
            "searchTerms": searchTerm,
            "maxItems": 20,
            "proxyConfig": { "useApifyProxy": true }
        };
        
        const craigslistRun = await Apify.call('ivanvs/craigslist-scraper', craigslistInput);
        if (craigslistRun.output) {
            results.push(...craigslistRun.output.map(item => ({
                ...item,
                platform: 'Craigslist'
            })));
        }
    } catch(e) {
        console.log('Craigslist error:', e.message);
    }
    
    // Run Facebook Marketplace Scraper
    try {
        const fbInput = {
            "searchTerm": searchTerm,
            "maxResults": 20,
            "proxyConfig": { "useApifyProxy": true }
        };
        
        const fbRun = await Apify.call('apify/facebook-marketplace-scraper', fbInput);
        if (fbRun.output) {
            results.push(...fbRun.output.map(item => ({
                ...item,
                platform: 'Facebook'
            })));
        }
    } catch(e) {
        console.log('Facebook error:', e.message);
    }
    
    // Run eBay Scraper
    try {
        const ebayInput = {
            "searchTerm": searchTerm,
            "maxItems": 20,
            "proxyConfig": { "useApifyProxy": true }
        };
        
        const ebayRun = await Apify.call('ivanvs/ebay-scraper-ppr', ebayInput);
        if (ebayOutput) {
            results.push(...ebayOutput.map(item => ({
                ...item,
                platform: 'eBay'
            })));
        }
    } catch(e) {
        console.log('eBay error:', e.message);
    }
    
    // Save results
    const fs = require('fs');
    fs.writeFileSync('search_results.json', JSON.stringify(results, null, 2));
    console.log(`Saved ${results.length} results`);
}

runApifyScraper();
