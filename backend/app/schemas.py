"""
Pydantic v2 schemas for the Marchiol Pricing API.
All user-facing labels and error strings are in Italian.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Catalog schemas ────────────────────────────────────────────────────────────

class ClientBrief(BaseModel):
    client_code: str
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    branch: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None


class ArticleBrief(BaseModel):
    article_code: str
    article_desc: Optional[str] = None
    sco_code: str
    sco_desc: Optional[str] = None


# ── Client context schemas ─────────────────────────────────────────────────────

class CartelliniItem(BaseModel):
    sco_code: str
    sco_desc: Optional[str] = None
    contract_discount_pct: float = Field(
        description="Sconto contrattualizzato (floor) per questa SCO, da 0 a 1"
    )


class OfferBrief(BaseModel):
    offer_num: str
    offer_row: Optional[str] = None
    article_code: str
    article_desc: Optional[str] = None
    offer_date: Optional[str] = None
    qty: Optional[float] = None
    list_price: Optional[float] = None
    net_price: Optional[float] = None
    discount_pct: Optional[float] = None
    row_status: Optional[str] = None


class ClientContext(BaseModel):
    client_code: str
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    branch: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    agent: Optional[str] = None
    potential: Optional[str] = None
    num_employees: Optional[float] = None
    cartellini: list[CartelliniItem] = Field(default_factory=list)
    recent_offers: list[OfferBrief] = Field(default_factory=list)


# ── Pricing schemas ────────────────────────────────────────────────────────────

class RecommendItem(BaseModel):
    article_code: str
    qty: float = Field(gt=0, description="Quantità richiesta")


class RecommendRequest(BaseModel):
    client_code: str
    items: list[RecommendItem] = Field(min_length=1)


class ExplanationStep(BaseModel):
    step: str
    pool_size: int
    median_discount: Optional[float] = None
    used: bool
    detail: Optional[str] = None


class ActivePromo(BaseModel):
    promo_id: str
    promo_type: str


class RecommendResponse(BaseModel):
    client_code: str
    article_code: str
    qty: float

    suggested_discount_pct: float = Field(
        description="Sconto suggerito (0–1)"
    )
    min_discount_pct: float = Field(
        description="25° percentile del pool — sconto minimo di riferimento"
    )
    max_discount_pct: float = Field(
        description="75° percentile del pool — sconto massimo di riferimento"
    )
    contract_floor_pct: Optional[float] = Field(
        default=None,
        description="Sconto minimo contrattuale (cartellino), se presente"
    )
    expected_margin_pct: float = Field(
        description="Margine percentuale atteso"
    )
    expected_margin_eur: float = Field(
        description="Margine assoluto atteso (€) per la quantità richiesta"
    )
    unit_cost_used: float = Field(
        description="Costo unitario mediano (ultimi 12 mesi)"
    )
    list_price_used: float = Field(
        description="Prezzo di listino mediano (ultimi 12 mesi)"
    )
    requires_deroga: bool = Field(
        description="True se il suggerito è sotto il floor contrattuale"
    )
    active_promo: Optional[ActivePromo] = Field(
        default=None,
        description="Promozione attiva per questo cliente/articolo, se presente"
    )
    explanation_trace: list[ExplanationStep] = Field(
        description="Traccia del ragionamento passo per passo"
    )
    data_sufficiency: Literal["high", "medium", "low", "insufficient"] = Field(
        description="Qualità del dato: high=cliente specifico, medium=tipo cliente, low=geografico/globale, insufficient=dati insufficienti"
    )
