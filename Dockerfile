# --------------------------------------------------------
# mcp-google-ads – Dockerfile for Vercel / local testing
# --------------------------------------------------------
    FROM python:3.11-slim

    WORKDIR /app
    COPY . .
    RUN pip install --no-cache-dir -r requirements.txt
    
    EXPOSE 8080                   
    
    # Vercel passes $PORT at runtime; default to 8080 locally
    ENV PORT=8080
    CMD ["uvicorn", "mcp_google_ads.main:app", "--host", "0.0.0.0", "--port", "8080"]
