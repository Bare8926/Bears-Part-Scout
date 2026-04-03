"""
Rare Parts Hunter - eBay scraper
Checks eBay search results and emails new matches.

Config: rare-parts-hunter/config.json
Secrets (set in GitHub Actions or environment):
- EMAIL_METHOD: 'sendgrid' or 'smtp'

For SendGrid:
- SENDGRID_API_KEY

For SMTP:
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASS

This is a simple MVP scraper. It saves seen item IDs to seen.json to avoid duplicate alerts.
"""
import os
import json
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO)
HERE = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(HERE, 'config.json')
SEEN_PATH = os.path.join(HERE, 'seen.json')


def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def load_seen():
    if not os.path.exists(SEEN_PATH):
        return set()
    with open(SEEN_PATH, 'r') as f:
        try:
            return set(json.load(f))
        except Exception:
            return set()


def save_seen(seen):
    with open(SEEN_PATH, 'w') as f:
        json.dump(list(seen), f)


def build_search_url(query: str):
    # Basic eBay search URL; adjust _sop for sort order if needed
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=10"


def parse_price(price_str: str) -> float:
    # Remove dollar sign, commas, and anything after space (e.g., "$123.45  BIN")
    if not price_str:
        return 9999999.0
    s = price_str.replace('$', '').replace(',', '').strip()
    parts = s.split(' ')
    try:
        return float(parts[0])
    except Exception:
        return 9999999.0


def scrape_listings(query: str) -> List[dict]:
    url = build_search_url(query)
    logging.info('Fetching %s', url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; RarePartsHunter/1.0; +https://example.com)'
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = []
    for item in soup.select('.s-item'):
        title_tag = item.select_one('.s-item__title')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link_tag = item.select_one('.s-item__link')
        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else None
        price_tag = item.select_one('.s-item__price')
        price = parse_price(price_tag.get_text(strip=True)) if price_tag else 9999999.0
        # eBay item ID may be in the link as /itm/<id>
        item_id = None
        if link:
            import re
            m = re.search(r'/itm/([0-9]+)', link)
            if m:
                item_id = m.group(1)
            else:
                # fallback to using the link itself
                item_id = link
        items.append({'id': item_id, 'title': title, 'price': price, 'link': link})
    return items


def send_email_sendgrid(to_email: str, subject: str, html_content: str):
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key:
        raise RuntimeError('SENDGRID_API_KEY not set')
    url = 'https://api.sendgrid.com/v3/mail/send'
    payload = {
        'personalizations': [{'to': [{'email': to_email}], 'subject': subject}],
        'from': {'email': 'no-reply@rareparts.example'},
        'content': [{'type': 'text/html', 'value': html_content}]
    }
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code >= 400:
        logging.error('SendGrid error %s: %s', r.status_code, r.text)
        r.raise_for_status()


def send_email_smtp(to_email: str, subject: str, html_content: str):
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASS')
    if not host or not user or not password:
        raise RuntimeError('SMTP credentials not set in environment')
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = to_email
    part = MIMEText(html_content, 'html')
    msg.attach(part)
    s = smtplib.SMTP(host, port, timeout=30)
    try:
        s.starttls()
    except Exception:
        pass
    s.login(user, password)
    s.sendmail(user, [to_email], msg.as_string())
    s.quit()


def notify_matches(matches: List[dict], config):
    if not matches:
        logging.info('No new matches to notify')
        return
    to_email = config['email']
    subject = f"Rare Parts Hunter: {len(matches)} new match(es) for '{config['query']}'"
    html_lines = [f"<h2>{subject}</h2>", '<ul>']
    for m in matches:
        html_lines.append(f"<li><a href=\"{m['link']}\">{m['title']}</a> — ${m['price']}</li>")
    html_lines.append('</ul>')
    html_content = '\n'.join(html_lines)
    method = os.getenv('EMAIL_METHOD', 'sendgrid').lower()
    logging.info('Sending email via %s', method)
    try:
        if method == 'sendgrid':
            send_email_sendgrid(to_email, subject, html_content)
        elif method == 'smtp':
            send_email_smtp(to_email, subject, html_content)
        else:
            logging.warning('Unknown EMAIL_METHOD: %s - skipping notification', method)
    except Exception as e:
        logging.warning('Failed to send email notification: %s - matches will still be tracked', e)


def main():
    print("=== RARE PARTS HUNTER STARTING ===")
    config = load_config()
    query = config['query']
    max_price = float(config.get('max_price', 9999999))
    seen = load_seen()
    items = scrape_listings(query)
    print(f'=== FOUND {len(items)} TOTAL ITEMS ===')
    new_matches = []
    for it in items:
        if not it['id']:
            continue
        if it['id'] in seen:
            print(f'Seen (skipping): {it["title"]}')
            continue
        if it['price'] <= max_price:
            print(f'NEW MATCH: {it["title"]} — ${it["price"]}')
            new_matches.append(it)
            seen.add(it['id'])
        else:
            print(f'Too expensive (skipping): {it["title"]} — ${it["price"]}')
    print(f'=== {len(new_matches)} NEW MATCHES UNDER ${max_price} ===')
    if new_matches:
        print('=== SENDING EMAIL NOTIFICATION ===')
        notify_matches(new_matches, config)
    save_seen(seen)
    print('=== DONE ===')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception('Script failed: %s', e)
        raise
