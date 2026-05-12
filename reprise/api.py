from typing import Annotated, Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from reprise.db import database_session
from reprise.repository import (
    CitationRepository,
    ClozeDeletionRepository,
    MotifRepository,
)
from reprise.schemas import (
    CitationCreate,
    CitationResponse,
    ClozeDeletionCreate,
    ClozeDeletionResponse,
    ClozeDeletionUpdate,
    DeleteResponse,
    MotifCreate,
    MotifListResponse,
    MotifResponse,
    MotifUpdate,
    PaginationParams,
)
from reprise.service import Service

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/motifs")
def get_motifs(query: Annotated[PaginationParams, Query()]) -> MotifListResponse:
    with database_session() as session:
        repository = MotifRepository(session)
        motifs = repository.get_motifs_paginated(query.page, query.page_size)
        total_count = repository.get_motifs_count()

        motifs_list = [
            MotifResponse(
                uuid=motif.uuid,
                content=motif.content,
                created_at=motif.created_at.isoformat(),
                citation=motif.citation.title if motif.citation else None,
                cloze_deletions=(
                    [
                        ClozeDeletionResponse(uuid=cd.uuid, mask_tuples=cd.mask_tuples)
                        for cd in motif.cloze_deletions
                    ]
                    if motif.cloze_deletions
                    else None
                ),
            ).model_dump()
            for motif in motifs
        ]
        return MotifListResponse(motifs=motifs_list, total_count=total_count)


@app.post("/motifs")
def create_motif(body: MotifCreate) -> MotifResponse:
    with database_session() as session:
        repository = MotifRepository(session)
        motif = repository.add_motif(body.content)
        if body.citation:
            citation_repository = CitationRepository(session)
            citation = citation_repository.get_citation_by_title(body.citation)
            if not citation:
                citation = citation_repository.add_citation(body.citation)
            motif = repository.add_citation(motif.uuid, citation)

        if body.auto_generate_cloze_deletions:
            service = Service(session)
            try:
                service.cloze_delete_motif(motif.uuid, n_max=2)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

            session.refresh(motif)

        return MotifResponse(
            uuid=motif.uuid,
            content=motif.content,
            citation=motif.citation.title if motif.citation else None,
            cloze_deletions=(
                [
                    ClozeDeletionResponse(uuid=cd.uuid, mask_tuples=cd.mask_tuples)
                    for cd in motif.cloze_deletions
                ]
                if motif.cloze_deletions
                else None
            ),
            created_at=motif.created_at.isoformat(),
        )


@app.put("/motifs/{uuid}")
def update_motif(uuid: str, body: MotifUpdate) -> MotifResponse:
    with database_session() as session:
        if body.citation:
            citation_repository = CitationRepository(session)
            citation = citation_repository.get_citation_by_title(body.citation)
            if not citation:
                raise HTTPException(
                    status_code=404, detail=f"Citation {body.citation} not found"
                )

        repository = MotifRepository(session)
        motif = repository.update_motif_content(uuid, body.content)

        if body.citation:
            motif = repository.add_citation(motif.uuid, citation)

        return MotifResponse(
            uuid=motif.uuid,
            content=motif.content,
            citation=motif.citation.title if motif.citation else None,
            cloze_deletions=(
                [
                    ClozeDeletionResponse(uuid=cd.uuid, mask_tuples=cd.mask_tuples)
                    for cd in motif.cloze_deletions
                ]
                if motif.cloze_deletions
                else None
            ),
            created_at=motif.created_at.isoformat(),
        )


@app.delete("/motifs/{uuid}")
def delete_motif(uuid: str) -> DeleteResponse:
    with database_session() as session:
        repository = MotifRepository(session)
        repository.delete_motif(uuid)
    return DeleteResponse(message="Motif deleted")


@app.get("/citations")
def get_citations() -> List[CitationResponse]:
    with database_session() as session:
        repository = CitationRepository(session)
        citations = repository.get_citations()
        return [
            CitationResponse(
                uuid=citation.uuid,
                title=citation.title,
                created_at=citation.created_at.isoformat(),
            )
            for citation in citations
        ]


@app.post("/citations")
def create_citation(body: CitationCreate) -> CitationResponse:
    with database_session() as session:
        repository = CitationRepository(session)
        citation = repository.add_citation(body.title)
        return CitationResponse(uuid=citation.uuid, title=citation.title)


@app.post("/reprise")
def reprise() -> List[Dict[str, Any]]:
    with database_session() as session:
        service = Service(session)
        reprisals = service.reprise()
        return [
            MotifResponse(
                uuid=reprisal.motif.uuid,
                content=reprisal.motif.content,
                cloze_deletions=(
                    [
                        ClozeDeletionResponse(
                            uuid=reprisal.cloze_deletion.uuid,
                            mask_tuples=reprisal.cloze_deletion.mask_tuples,
                        )
                    ]
                    if reprisal.cloze_deletion
                    else None
                ),
                created_at=reprisal.motif.created_at.isoformat(),
                citation=(
                    reprisal.motif.citation.title if reprisal.motif.citation else None
                ),
            ).model_dump()
            for reprisal in reprisals
        ]


@app.post("/cloze_deletions")
def create_cloze_deletion(body: ClozeDeletionCreate) -> ClozeDeletionResponse:
    with database_session() as session:
        repository = ClozeDeletionRepository(session)
        cloze_deletion = repository.add_cloze_deletion(
            body.motif_uuid, body.mask_tuples
        )
        return ClozeDeletionResponse(
            uuid=cloze_deletion.uuid,
            mask_tuples=cloze_deletion.mask_tuples,
        )


@app.put("/cloze_deletions")
def update_cloze_deletion(body: ClozeDeletionUpdate) -> ClozeDeletionResponse:
    with database_session() as session:
        repository = ClozeDeletionRepository(session)
        cloze_deletion = repository.update_cloze_deletion(body.uuid, body.mask_tuples)
        return ClozeDeletionResponse(
            uuid=cloze_deletion.uuid,
            mask_tuples=cloze_deletion.mask_tuples,
        )


@app.delete("/cloze_deletions/{uuid}")
def delete_cloze_deletion(uuid: str) -> DeleteResponse:
    with database_session() as session:
        repository = ClozeDeletionRepository(session)
        repository.delete_cloze_deletion(uuid)
        return DeleteResponse(message="Cloze deletion deleted")
