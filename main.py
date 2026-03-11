"""
FastAPI wrapping the `identify` function from pydref
(https://github.com/abes-esr/pydref/blob/master/pydref.py)

Install dependencies:
    pip install fastapi uvicorn

Run:
    uvicorn main:app --reload
"""

from pydref import Pydref
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
import httpx

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Pydref Identify API",
    description=(
        "Expose la fonction `identify` de la librairie "
        "[pydref](https://github.com/abes-esr/pydref) "
        "pour rechercher des notices d'autorité dans "
        "[IdRef](https://www.idref.fr/)."
    ),
    version="1.0.0",
    contact={
        "name": "MESRE",
    },
)

@app.get(
    "/identify",
    summary="Rechercher une autorité IdRef",
    description=(
        "Interroge l'index IdRef (via pydref.identify) à partir d'un nom, "
        "d'un prénom et/ou d'un PPN. "
        "Retourne les notices d'autorité correspondantes."
    ),
    response_description="Liste de notices d'autorité IdRef correspondantes",
    tags=["identify"],
)
async def identify(
    name: Optional[str] = Query(
        default=None,
        description="Nom de famille de la personne",
        example="Jean Dupont",
    ),
):
    pydref_instance = Pydref()
    import asyncio

    loop = asyncio.get_event_loop()
    raw_results = await loop.run_in_executor(
        None,
        lambda: pydref_instance.identify(query=name),
    )
    return JSONResponse(content=raw_results)

@app.get("/health", tags=["meta"], summary="Health check")
async def health():
    return {"status": "ok", "pydref_installed": _USE_PYDREF}
