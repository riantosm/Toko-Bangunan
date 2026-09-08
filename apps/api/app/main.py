from fastapi import FastAPI

app = FastAPI(title="Toko Bangunan API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
