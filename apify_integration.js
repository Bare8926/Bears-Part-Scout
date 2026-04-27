#!/usr/bin/env node
/**
 * Bears Part Scout - Apify Integration
 * Searches Craigslist, Facebook Marketplace, eBay, and Google
 */

const https = require('https');
const fs = require('fs');

const APIFY_TOKEN = process.env.APIFY_TOKEN;

// Helper function to make API requests
function apifyRequest(url, data) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify(data);
        const urlObj = new URL(url);
        
        const options = {
            hostname: urlObj.hostname,
            path: urlObj.pathname + urlObj.search,
            method: data ? 'POST' : 'GET',
            headers: {
                'Authorization': `Bearer ${APIFY_TOKEN}`,
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };
        
        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch(e) {
                    resolve(body);
                }
            });
        });
        
        req.on('error', reject);
        
        if (data) {
            req.write(postData);
        }
        req.end();
    });
}

async function searchCraigslist(query, location = "losangeles") {
    const searchUrl = `https://${location}.craigslist.org/search/sss?query=${encodeURIComponent(query)}`;
    const url = "https://api.apify.com/v2/acts/ivanvs~craigslist-scraper/run-sync";
    
    try {
        console.log("  Calling Craigslist API with:", JSON.stringify({ urls: [searchUrl] }));
        const data = await apifyRequest(url, {
            urls: [searchUrl]
        });
        console.log("  Craigslist API response:", JSON.stringify(data).substring(0, 500));
        
        if (data.data && data.data.defaultDatasetId) {
            const datasetId = data.data.defaultDatasetId;
            const itemsUrl = `https://api.apify.com/v2/datasets/${datasetId}/items`;
            const items = await apifyRequest(itemsUrl);
            
            return items.map(item => ({
                title: item.title || "N/A",
                price: item.price || "N/A",
                location: item.location || "N/A",
                url: item.url || "",
                date: item.datetime || "",
                platform: "Craigslist"
            }));
        }
    } catch (e) {
        console.error("Craigslist error:", e.message);
    }
    return [];
}

async function searchFacebook(query, location = "losangeles") {
    const searchUrl = `https://www.facebook.com/marketplace/${location}/search/?query=${encodeURIComponent(query)}`;
    const url = "https://api.apify.com/v2/acts/apify~facebook-marketplace-scraper/run-sync";
    
    try {
        console.log("  Calling Facebook API with:", JSON.stringify({ urls: [searchUrl] }));
        const data = await apifyRequest(url, {
            urls: [searchUrl]
        });
        console.log("  Facebook API response:", JSON.stringify(data).substring(0, 500));
        
        if (data.data && data.data.defaultDatasetId) {
            const datasetId = data.data.defaultDatasetId;
            const itemsUrl = `https://api.apify.com/v2/datasets/${datasetId}/items`;
            const items = await apifyRequest(itemsUrl);
            
            return items.map(item => {
                const price = item.listing_price || {};
                const priceStr = (price.formatted_amount) ? price.formatted_amount : "N/A";
                return {
                    title: item.name || "N/A",
                    price: priceStr,
                    location: (item.location && item.location.city) ? item.location.city : "N/A",
                    url: item.listingUrl || "",
                    date: item.createdAt || "",
                    platform: "Facebook"
                };
            });
        }
    } catch (e) {
        console.error("Facebook error:", e.message);
    }
    return [];
}

async function searchEbay(query) {
    const searchUrl = `https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(query)}`;
    const url = "https://api.apify.com/v2/acts/dtrungtin~ebay-items-scraper/run-sync";
    
    try {
        console.log("  Calling eBay API with:", JSON.stringify({ urls: [searchUrl] }));
        const data = await apifyRequest(url, {
            urls: [searchUrl]
        });
        console.log("  eBay API response:", JSON.stringify(data).substring(0, 500));
        
        if (data.data && data.data.defaultDatasetId) {
            const datasetId = data.data.defaultDatasetId;
            const itemsUrl = `https://api.apify.com/v2/datasets/${datasetId}/items`;
            const items = await apifyRequest(itemsUrl);
            
            return items.map(item => ({
                title: item.title || "N/A",
                price: item.price || "N/A",
                location: item.location || "N/A",
                url: item.url || "",
                date: item.date || "",
                platform: "eBay"
            }));
        }
    } catch (e) {
        console.error("eBay error:", e.message);
    }
    return [];
}

async function searchGoogle(query) {
    const url = "https://api.apify.com/v2/acts/apidojo~google-search-scraper/run-sync";
    
    try {
        console.log("  Calling Google API with:", JSON.stringify({ queries: [query], numResults: 10 }));
        const data = await apifyRequest(url, {
            queries: [query],
            numResults: 10
        });
        console.log("  Google API response:", JSON.stringify(data).substring(0, 500));
        
        if (data.data && data.data.defaultDatasetId) {
            const datasetId = data.data.defaultDatasetId;
            const itemsUrl = `https://api.apify.com/v2/datasets/${datasetId}/items`;
            const items = await apifyRequest(itemsUrl);
            
            return items.map(item => ({
                title: item.title || "N/A",
                url: item.url || "",
                snippet: item.snippet || "",
                platform: "Google"
            }));
        }
    } catch (e) {
        console.error("Google error:", e.message);
    }
    return [];
}

async function searchAll(query) {
    console.log(`Searching for: ${query}`);
    
    console.log("Searching Craigslist...");
    const craigslistResults = await searchCraigslist(query);
    console.log(`  Found ${craigslistResults.length} results`);
    
    console.log("Searching Facebook Marketplace...");
    const fbResults = await searchFacebook(query);
    console.log(`  Found ${fbResults.length} results`);
    
    console.log("Searching eBay...");
    const ebayResults = await searchEbay(query);
    console.log(`  Found ${ebayResults.length} results`);
    
    console.log("Searching Google...");
    const googleResults = await searchGoogle(query);
    console.log(`  Found ${googleResults.length} results`);
    
    const allResults = [...craigslistResults, ...fbResults, ...ebayResults, ...googleResults];
    
    const results = {
        timestamp: new Date().toISOString(),
        query: query,
        count: allResults.length,
        results: allResults
    };
    
    fs.writeFileSync("search_results.json", JSON.stringify(results, null, 2));
    console.log(`\nTotal: ${allResults.length} results saved to search_results.json`);
    
    return results;
}

// Run from command line
const query = process.argv.slice(2).join(" ") || "honda civic brake calipers";
searchAll(query).then(results => {
    console.log("\nFirst 3 results:");
    results.results.slice(0, 3).forEach(r => {
        console.log(`  - ${r.title} (${r.platform})`);
    });
}).catch(console.error);

