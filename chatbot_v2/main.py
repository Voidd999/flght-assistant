from fastapi import FastAPI
from chatbot_v2.routes import chat_router, new_router  # Absolute import
from fastapi.middleware.cors import CORSMiddleware
import logging
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="Flight Assistant API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Register routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(new_router, prefix="/api/v1")
# Add CORS middleware
logger = logging.getLogger("fastapi")
logger.info("FastAPI application started with colored logging")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize any necessary components on startup"""
    pass


@app.get("/api/v1/")
async def root():
    return {"message": "Welcome to the Flight Assistant API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("chatbot_v2.main:app", host="0.0.0.0", port=8000, reload=True, workers=4)
