import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .routers import auth, expenses

logger = logging.getLogger("app")

app = FastAPI(title="Expense Tracker API")
app.include_router(auth.router)
app.include_router(expenses.router)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/health")
def health():
    return {"status": "ok"}