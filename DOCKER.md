# Docker Setup

This Docker setup runs the production FastAPI backend and the Next.js frontend.
It mounts your local `data/` directory, so the existing FAISS/Qdrant artifacts are
reused instead of baked into the image.

## Prerequisites

- Docker Desktop
- A populated `.env` file in the project root
- Existing retrieval artifacts in `data/`, especially:
  - `data/cusb_chunks.pkl`
  - `data/cusb_embeddings.npy`
  - `data/cusb_vector.index`

For the most reliable Windows Docker run, the compose file uses FAISS by
default. To force a different backend for Docker only, set:

```env
DOCKER_VECTOR_BACKEND=qdrant
```

## Run

```powershell
docker compose up --build
```

Services:

- Backend: `http://localhost:8080/api/health`
- Frontend: `http://localhost:3000`

## Stop

```powershell
docker compose down
```

## Notes

- The frontend proxies `/api/*` requests to the backend container.
- Uploaded/indexed files are written back to your local `data/` directory.
- Local embedded Qdrant can lock its storage if more than one process opens it.
  If that happens, switch `VECTOR_BACKEND=faiss` or stop the other process.

## Optional GPU Run

First verify Docker can see the GPU:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Then run the GPU backend image:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

For 4GB VRAM, keep reranking disabled:

```env
USE_RERANKER=false
FINAL_TOP_K=3
DENSE_TOP_K=10
BM25_TOP_K=10
```

On a 12GB GPU system, you can try `USE_RERANKER=true` after the basic GPU run
works.
