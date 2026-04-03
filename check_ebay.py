#!/usr/bin/env python3
"""
Rare Parts Hunter - eBay scraper
"""
import os
import json
import sys
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

print("=== RARE PARTS HUNTER STARTING ===", flush=True)

CONFIG_PATH = 'config.json'
SEEN_PATH = 'seen.json'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_seen():
    if not os.path.exists(SEEN_PATH):
        return set()
    with open(SEEN_PATH, 'r') as f:
        try:
            return set(json.load(f))
        except:
            return set()

def save_seen(seen):
    with open(SEEN_PATH, 'w') as f:
        json.dump(list(seen), f)

def scrape_listings(query):
    url = f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=10"
    print(f"Fetching: {url}", flush=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    resp = session.get(url, timeout=30)
    print(f"Response status: {resp.status_code}", flush=True)
    
    if resp.status_code != 200:
        print(f"ERROR: eBay returned {resp.status_code}", flush=True)
        return []
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find ALL list items - try multiple approaches
    items = soup.find_all('li', class_=re.compile('s-item'))
    if not items:
        items = soup.select('ul.srp-list li')
    if not items:
        items = soup.select('.srp-results li')
    if not items:
        items = soup.find_all('li', recursive=False)
    
    print(f"Found {len(items)} raw list items", flush=True)
    
    results = []
    for item in items:
        # Try multiple ways to get title
        title = ""
        for selector in ['.s-item__title', '.itmtitle', 'h3', '.item-title', '[itemprop="name"]']:
            title_elem = item.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break
        
        if not title:
            continue
        if 'Shop on eBay' in title:
            continue
            
        # Get link
        link = ""
        for selector in ['.s-item__link', 'a[href*="/itm/"]', 'a.item-link']:
            link_elem = item.select_one(selector)
            if link_elem:
                link = link_elem.get('href', '')
                break
        
        # Get price
        price = 9999999.0
        for selector in ['.s-item__price', '.price', '.item-price']:
            price_elem = item.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group())
                    except:
                        pass
                break
        
        # Get item ID
        item_id = None
        if link:
            id_match = re.search(r'/itm/(\d+)', link)
            if id_match:
                item_id = id_match.group(1)
            else:
                item_id = link
        
        if item_id:
            results.append({
                'id': item_id,
                'title': title,
                'price': price,
                'link': link
            })
    
    return results

def send_email_sendgrid(to_email, subject, html_content):
    api_key = os.getenv('SENDGRID_API_KEY')
    print(f"SENDGRID_API_KEY present: {bool(api_key)}", flush=True)
    if not api_key:
        print("ERROR: SENDGRID_API_KEY not set!", flush=True)
        return
    
    url = 'https://api.sendgrid.com/v3/mail/send'
    payload = {
        'personalizations': [{'to': [{'email': to_email}], 'subject': subject}],
        'from': {'email': 'no-reply@rareparts.example'},
        'content': [{'type': 'text/html', 'value': html_content}]
    }
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    r = requests.post(url, headers=headers, json=payload)
    print(f"SendGrid response: {r.status_code}", flush=True)
    if r.status_code >= 400:
        print(f"SendGrid error: {r.text}", flush=True)
    else:
        print("Email sent successfully!", flush=True)

def notify_matches(matches, config):
    if not matches:
        print("No matches to notify", flush=True)
        return
    to_email = config['email']
    subject = f"Rare Parts Hunter: {len(matches)} new match(es)"
    html_lines = [f"<h2>{subject}</h2>", '<ul>']
    for m in matches:
        html_lines.append(f"<li><a href=\"{m['link']}\">{m['title']}</a> — ${m['price']}</li>")
    html_lines.append('</ul>')
    html_content = '\n'.join(html_lines)
    method = os.getenv('EMAIL_METHOD', 'sendgrid').lower()
    print(f"Sending email via {method}", flush=True)
    if method == 'sendgrid':
        send_email_sendgrid(to_email, subject, html_content)

def main():
    config = load_config()
    query = config['query']
    max_price = float(config.get('max_price', 9999999))
    seen = load_seen()
    print(f"Searching for: {query} (max ${max_price})", flush=True)
    
    items = scrape_listings(query)
    print(f"=== FOUND {len(items)} PARSED ITEMS ===", flush=True)
    
    new_matches = []
    for it in items:
        if not it['id']:
            continue
        if it['id'] in seen:
            continue
        if it['price'] <= max_price:
            print(f"NEW MATCH: {it['title']} — ${it['price']}", flush=True)
            new_matches.append(it)
            seen.add(it['id'])
        else:
            print(f"Too expensive: {it['title'][:50]} — ${it['price']}", flush=True)
    
    print(f"=== {len(new_matches)} NEW MATCHES ===", flush=True)
    
    if new_matches:
        notify_matches(new_matches, config)
    
    save_seen(seen)
    print("=== DONE ===", flush=True)

if __name__ == '__main__':
    main()
