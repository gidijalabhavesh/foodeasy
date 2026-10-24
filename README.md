# Gather food ordering app

A responsive restaurant menu and cart powered by FastAPI. The browser stores a
random cart ID so separate visitors do not share a cart. The assistant can use
OpenAI when configured; browsing and ordering still work without an API key.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Visit http://localhost:8000. To enable the AI assistant, set `OPENAI_API_KEY`
in your environment before starting the server. The local fallback assistant
can still search the menu and inspect or clear the cart without that key.

## Deploy

1. Push this project to a GitHub repository.
2. In Render, create a Blueprint from that repository and deploy `render.yaml`.
   The API service name is `smart-food-delivery-api`.
3. In Vercel, import the same repository. `vercel.json` serves the `frontend`
   directory and forwards `/api/*` requests to the Render service.
4. If you rename the Render service, change its URL in `vercel.json` and
   redeploy Vercel. Add `OPENAI_API_KEY` to Render only if you want AI-powered
   assistant responses.

The cart store is in memory and intended for a demo. Deployments that need
persistent carts should connect a shared database before production use.
