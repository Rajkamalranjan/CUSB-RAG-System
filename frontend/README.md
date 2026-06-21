# CUSB RAG Frontend

Target production frontend: Next.js + TailwindCSS + citation panel + streaming chat.

Run locally without Docker:

```powershell
..\scripts\start_frontend.ps1
```

The app proxies `/api/*` to `http://127.0.0.1:8080` by default. Override with:

```powershell
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8080"
npm run dev
```
