# HealthFlow AI - Web Frontend

A responsive, production-ready healthcare orchestration web app built with **Next.js 16 (App Router)**, **TypeScript**, and **Tailwind CSS v4**, designed for seamless deployment to **Vercel**.

---

## Features

1. 🩺 **Pre-Admission Clinical Review Portal (HITL & Clearance):**
   * Real-time monitoring of parallel clearance branches: Scheduling, Insurance 270/278, and Clinical Risk.
   * Hierarchical Gate assessment with ASA, RCRI, and active contraindication flags.
   * Cryptographic Attestation console generating ECDSA NIST P-256 signatures to resume paused LangGraph checkpoints.

2. 📱 **Patient Twilio 2-Way SMS Mobile Simulator:**
   * Interactive smartphone interface simulating real patient interactions.
   * Test appointment slot confirmation ("Option B") and Post-Op Day 1/3/7 symptom surveys.
   * Evaluates compound negation natural language responses (e.g. "No fever or redness").

3. 📈 **Post-Discharge & Revenue Cycle Engine:**
   * Procedure-specific recovery trajectory curves (CPT 27130 Total Hip Arthroplasty).
   * Dual-direction billing discrepancy auditor demonstrating:
     * **Down-coding protection:** Catches omitted CKD 3a comorbidity, protecting **+$3,800.00** in hospital reimbursement.
     * **Up-coding fraud prevention:** Eliminates liability from unsubstantiated heart failure billing.

4. 🔒 **Statutory HIPAA Immutable Audit Trail (WORM):**
   * Live stream of append-only audit events with actor ID, resource URI, and SHA-256 payload hashes.
   * One-click cryptographic integrity verification asserting zero tampering.

---

## Local Development

### 1. Install Dependencies
```bash
cd /Users/anmoljaising/healthflow/frontend
npm install
```

### 2. Run the Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) with your browser.

---

## Deployment to Vercel

### Option 1: Vercel CLI (Fastest)
From the `frontend` directory:
```bash
npm i -g vercel
vercel
```
Follow the interactive prompts to link your Vercel account and deploy in under 60 seconds.

### Option 2: Vercel Web Dashboard (Git Integration)
1. Push your repository to GitHub.
2. In the [Vercel Dashboard](https://vercel.com), click **Add New Project**.
3. Select your repository and set the **Root Directory** to `frontend`.
4. Click **Deploy**.
