Rare Parts Hunter - MVP

Files:
- check_ebay.py — main scraper and notifier
- config.json — search config
- seen.json — created at runtime to track seen items

Deployment (GitHub Actions recommended):
1. Create a repo and push this directory.
2. Add a GitHub Actions workflow to run check_ebay.py on schedule (every 6 hours).
3. Set repository secrets for SENDGRID_API_KEY or SMTP credentials and EMAIL_METHOD.

I can create the Actions workflow for you and show how to add secrets. If you want, I can also push to a new GitHub repo (I'll need permission to create it or you can create one and invite me)."}]}