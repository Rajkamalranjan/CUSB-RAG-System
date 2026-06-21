# VPS Deployment

## Server

Use an Ubuntu VPS with at least 2 vCPU, 4 GB RAM, and 20 GB free disk space.
Point the domain DNS `A` record to the VPS public IPv4 address before starting.

## One-time setup

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Log out and log back in after adding the Docker group.

## Upload

Clone the repository or copy the project to the server. The runtime needs the
generated `data` directory, including the FAISS files:

```text
data/cusb_chunks.pkl
data/cusb_embeddings.npy
data/cusb_vector.index
```

Create writable directories if they do not exist:

```bash
mkdir -p reports eval annotations
```

## Secrets

Copy `deploy/env.prod.example` to the project-root `.env`, then replace every
placeholder. Never commit the resulting `.env` file.

Rotate any API key that has previously been exposed before deploying.

## Start

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml logs -f backend
```

Wait for `Application startup complete`, then open:

```text
https://your-domain.example
```

Caddy automatically requests and renews the TLS certificate.

## Maintenance

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail 120 backend
docker compose -f docker-compose.prod.yml up --build -d
```
