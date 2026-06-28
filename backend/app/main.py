from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


# Punctul de pornire al backend-ului. Aici se configureaza aplicatia FastAPI,
# CORS-ul pentru interfata Flutter si se ataseaza rutele REST folosite de GUI.
app = FastAPI(
    title="ECU Calibration Analyzer",
    description=(
        "Backend API for ECU calibration file analysis, map comparison, "
        "explainable tuner recommendations, advisory ML evidence, and PDF reports."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
