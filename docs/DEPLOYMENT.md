# 🚀 Vercel Deployment & Database Setup Guide

This guide covers how to deploy the **AI Car Lease & Loan Negotiator** to **Vercel** with a public cloud database (Neon, Supabase, or Vercel Postgres) so anyone on the web can access it.

---

## 1. Prerequisites

1. A free [Vercel Account](https://vercel.com).
2. A free PostgreSQL database instance from any provider:
   - **[Neon Serverless Postgres](https://neon.tech)** (Recommended — 30 seconds setup, free tier)
   - **[Supabase](https://supabase.com)**
   - **[Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres)**

---

## 2. Configure Your Cloud Database

1. Create a new PostgreSQL database on Neon or Supabase.
2. Copy your connection URI (it looks like):
   ```
   postgresql://user:password@ep-sample-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
3. The application will automatically create the `contracts` and `audit_logs` tables on first run.

---

## 3. Deploy to Vercel in 2 Minutes

### Method A: Deploy via Vercel CLI (Fastest)

1. Install the Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Inside the project root (`AI-Driven-Car-Lease-Loan-Negotiator`), run:
   ```bash
   vercel
   ```

3. Follow the CLI prompts to link the project to your Vercel account.

4. Set the Environment Variables in the Vercel Dashboard or CLI:
   ```bash
   vercel env add HF_TOKEN
   # Paste: your_huggingface_token_here (optional)

   vercel env add ADMIN_SECRET_KEY
   # Paste: your_chosen_secret_admin_password

   vercel env add DATABASE_URL
   # Paste your Neon or Supabase connection string:
   # postgresql://user:password@host/dbname?sslmode=require
   ```

5. Deploy to Production:
   ```bash
   vercel --prod
   ```

### Method B: Deploy via Vercel Dashboard

1. Push your repository to GitHub or GitLab.
2. In the Vercel Dashboard, click **Add New Project** and select your repository.
3. In **Build and Output Settings**:
   - Vercel automatically detects `vercel.json` in the root.
4. Expand **Environment Variables** and add:
   - `ADMIN_SECRET_KEY`: `12345` (or your private password)
   - `HF_TOKEN`: your Hugging Face API token (optional)
   - `DATABASE_URL`: `postgresql://<user>:<password>@<host>/<database>?sslmode=require` (e.g. from Neon or Supabase)
5. Click **Deploy**!

---

## 4. Architecture on Vercel

```
Incoming Request
      │
      ├─── Static Assets (HTML, CSS, JS, Three.js) ───> Vercel Edge Global CDN
      │
      └─── API Endpoints (/upload, /decode-vin, /chat) ───> Vercel Serverless Function (api/index.py)
                                                                 │
                                                                 ├─── Cloud PostgreSQL (Neon / Supabase)
                                                                 └─── HuggingFace / NHTSA APIs
```

---

## 5. Security & Private Admin Telemetry

- The user-facing dashboard has **no login barrier** — anyone with the Vercel URL can analyze contracts, decode VINs, and chat with the coach.
- **Audit Logs** (`/api/admin/logs`) are locked behind `ADMIN_SECRET_KEY`.
- Only you can view the system activity logs by clicking the lock icon in the top right or bottom of the sidebar and entering your `ADMIN_SECRET_KEY`.
