#!/usr/bin/env node
/**
 * Bears Part Scout - Apify Integration
 * Uses free RSS feeds where possible, Apify for others
 */

const https = require('https');
const fs = require('fs');

const APIFY_TOKEN = process.env.APIFY_TOKEN;

// Helper function to make HTTP requests
function httpRequest(url) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        
        const options = {
            hostname: urlObj.hostname,
            path: urlObj.pathname + urlObj.search,
            method: 'GET'
        };
        
        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => resolve(body));
        });
        
        req.on('error', reject);
        req.end();
    });
}

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

// FREE: Craigslist RSS feed
async function searchCraigslist(query, location = "losangeles") {
    const rssUrl = `https://${location}.craigslist.org/search/sss?query=${encodeURIComponent(query)}&format=rss`;
    
    try {
        console.log("  Fetching Craigslist RSS:", rssUrl);
        const xml = await httpRequest(rssUrl);
        
        // Simple XML parsing
        const items = [];
        const itemRegex = /<item>([\s\S]*?)<\/item>/g;
        let match;
        
        while ((match = itemRegex.exec(xml)) !== null) {
            const itemXml = match[1];
            const title = itemXml.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/)?.[1] || 
                        itemXml.match(/<title>(.*?)<\/title>/)?.[1] || "N/A";
            const link = itemXml.match(/<link>(.*?)<\/link>/)?.[1] || "";
            const price = itemXml.match(/<price>(.*?)<\/price>/)?.[1] || "N/A";
            const date = itemXml.match(/<dc:date>(.*?)<\/dc:date>/)?.[1] || "";
            const locationMatch = itemXml.match(/<location>(.*?)<\/location>/);
            const location = locationMatch ? locationMatch[1] : "N/A";
            
            if (title && title !== "N/A") {
                items.push({
                    title: title.trim(),
                    price: price,
                    location: location,
                    url: link,
                    date: date,
                    platform: "Craigslist"
                });
            }
        }
        
        console.log(`  Found ${items.length} Craigslist results`);
        return items.slice(0, 20);
    } catch (e) {
        console.error("Craigslist error:", e.message);
    }
    return [];
}

// eBay - try using Apify
async function searchEbay(query) {
    const searchUrl = `https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(query)}`;
    const url = "https://api.apify.com/v2/acts/memo23~apify-ebay-search-cheerio/run-sync";
    
    try {
        console.log("  Calling eBay API...");
        const data = await apifyRequest(url, {
            startUrls: [{ url: searchUrl }]
        });
        console.log("  eBay response:", JSON.stringify(data).substring(0, 300));
        
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

// Facebook - try Apify
async function searchFacebook(query, location = "losangeles") {
    const searchUrl = `https://www.facebook.com/marketplace/${location}/search/?query=${encodeURIComponent(query)}`;
    const url = "https://api.apify.com/v2/acts/apify~facebook-marketplace-scraper/run-sync";
    
    try {
        console.log("  Calling Facebook API...");
        const data = await apifyRequest(url, {
            startUrls: [{ url: searchUrl }]
        });
        
        if (data.data && data.data.defaultDatasetId) {
            const datasetId = data.data.defaultDatasetId;
            const itemsUrl = `https://api.apify.com/v2/datasets/${datasetId}/items`;
            const items = await apifyRequest(itemsUrl);
            
            return items.map(item => ({
                title: item.name || item.title || "N/A",
                price: item.priceFormatted || item.listing_price?.formatted_amount || "N/A",
                location: item.location?.city || "N/A",
                url: item.listingUrl || "",
                date: item.createdAt || "",
                platform: "Facebook"
            }));
        }
    } catch (e) {
        console.error("Facebook error:", e.message);
    }
    return [];
}

// Google - try Apify
async function searchGoogle(query) {
    const url = "https://api.apify.com/v2/acts/apidojo~google-search-scraper/run-sync";
    
    try {
        console.log("  Calling Google API...");
        const data = await apifyRequest(url, {
            queries: [{ query: query, numResults: 10 }]
        });
        
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
    
    console.log("Searching Craigslist (free RSS)...");
    const craigslistResults = await searchCraigslist(query);
    
    console.log("Searching eBay...");
    const ebayResults = await searchEbay(query);
    
    console.log("Searching Facebook Marketplace...");
    const fbResults = await searchFacebook(query);
    
    console.log("Searching Google...");
    const googleResults = await searchGoogle(query);
    
    const allResults = [...craigslistResults, ...ebayResults, ...fbResults, ...googleResults];
    
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
const query = process.argv.slice(2).join(" ") || "honda civic parts";
searchAll(query).then(results => {
    console.log("\nFirst 3 results:");
    results.results.slice(0, 3).forEach(r => {
        console.log(`  - ${r.title} (${r.platform})`);
    });
}).catch(console.error);
