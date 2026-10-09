from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.services import benchmarks

router = APIRouter(prefix='/api/benchmarks', tags=['Public Shorts database'])


class Collection(BaseModel):
    query: str = Field(default='', max_length=120)
    urls: list[str] = Field(default_factory=list, max_length=10)
    profile: Literal['auto','gaming','education','podcast','story'] = 'auto'
    refresh: bool = False


@router.get('')
def library(q: str = Query(default='', max_length=120)):
    return {**benchmarks.list_records(q), 'job':benchmarks.status()}


@router.get('/status')
def status():
    return benchmarks.status()


@router.get('/export')
def export():
    return JSONResponse(benchmarks.list_records(limit=100000), headers={'Content-Disposition':'attachment; filename="public_shorts.json"'})


@router.post('/collect', status_code=202)
def collect(request: Collection):
    try:
        return benchmarks.start_collection(request.query, request.urls, request.profile, request.refresh)
    except ValueError as exc:
        raise HTTPException(409 if 'already running' in str(exc) else 400, str(exc))
