from __future__ import annotations

from fastapi import APIRouter

from app.generation.verify import verify_draft
from app.models import AskRequest, AskResponse, VerifyRequest, VerifyResponse
from app.pipeline import answer_question

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    return answer_question(req.question, req.scope)


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    return verify_draft(req.draft, req.scope)
