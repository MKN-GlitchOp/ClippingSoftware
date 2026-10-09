from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from backend.services import trends, benchmarks

router=APIRouter(prefix='/api/trends',tags=['Monthly Shorts trends'])
Topic=Literal['all','gaming','animals','sports','entertainment','tech','food','places','other','reactions','banter','fails','scares','irl','funny']
Format=Literal['all','ranking','top5','streamer']


def validate_topic(format,topic):
    catalog=trends.MOMENTS if format=='streamer' else trends.TOPICS
    if topic not in catalog and topic not in ('all','other'):
        raise HTTPException(400,'Choose a topic that matches this discovery mode.')


@router.get('')
def report(month:str=Query(default='',max_length=7),format:Format='streamer',topic:Topic='all',sort:Literal['views','pace','likes']='views',period:Literal['month','all']='month',min_views:int=Query(default=0,ge=0,le=1000000000)):
    validate_topic(format,topic)
    try:
        return trends.report(month or benchmarks.now().strftime('%Y-%m'),format,topic,sort,period,min_views)
    except ValueError as exc:
        raise HTTPException(400,str(exc))


class Scan(BaseModel):
    month:str=Field(min_length=7,max_length=7)
    topic:Topic='all'
    format:Format='streamer'
    period:Literal['month','all']='month'


@router.post('/scan',status_code=202)
def scan(request:Scan):
    validate_topic(request.format,request.topic)
    try:
        return trends.start_scan(request.month,'all' if request.topic=='other' else request.topic,request.format,request.period)
    except ValueError as exc:
        raise HTTPException(409 if 'already running' in str(exc) else 400,str(exc))
