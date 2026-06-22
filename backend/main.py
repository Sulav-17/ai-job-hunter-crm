from fastapi import FastAPI

app = FastAPI(title="AI Job Hunter CRM")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
