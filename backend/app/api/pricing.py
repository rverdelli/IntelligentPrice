"""
POST /pricing/recommend
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db
from app.domain.pricing import recommend_discount
from app.schemas import RecommendRequest, RecommendResponse

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.post("/recommend", response_model=list[RecommendResponse])
def pricing_recommend(
    body: RecommendRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> list[RecommendResponse]:
    """
    Raccomandazione di sconto per uno o più articoli per lo stesso cliente.

    Ritorna una lista di raccomandazioni, una per ogni articolo in input.
    HTTP 422 se un articolo non ha storico sufficiente.
    HTTP 404 se il cliente non esiste.
    """
    results = []
    for item in body.items:
        try:
            rec = recommend_discount(
                client_code=body.client_code,
                article_code=item.article_code,
                qty=item.qty,
                con=db,
            )
        except ValueError as exc:
            msg = str(exc)
            if "Cliente non trovato" in msg:
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=422, detail=msg)

        results.append(
            RecommendResponse(
                client_code=body.client_code,
                article_code=item.article_code,
                qty=item.qty,
                **rec,
            )
        )

    return results
