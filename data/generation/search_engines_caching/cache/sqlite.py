from sqlalchemy import (
    create_engine, Engine, Column,  ForeignKey, PrimaryKeyConstraint, 
    Integer, String, Boolean, Float, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base, DeclarativeBase, Session, sessionmaker, relationship
from typing import cast, Optional, Any, Iterable, Literal
import os
import json
from urllib.parse import urlparse

from ..schema import ProcessedResult

Base: DeclarativeBase = declarative_base()

# N UserQuery - 1 WebQuery
# M WebQuery - N Pages

class UserQuery(Base): #type:ignore
    __tablename__ = "user_query_table"

    id = cast(int, Column(Integer, primary_key=True, autoincrement=True))
    message = cast(str, Column(Text, nullable=False))
    
    web_query_id = cast(int, Column(Integer, ForeignKey("web_query_table.id")))
    web_query = cast("WebQuery", relationship("WebQuery", back_populates="user_queries"))
class WebQuery(Base): #type:ignore
    __tablename__ = "web_query_table"
    
    id = cast(int, Column(Integer, primary_key=True, autoincrement=True))
    query = cast(str, Column(Text, nullable=False))
    
    user_queries = relationship("UserQuery", back_populates="web_query")
    pages = cast(list["QueryPageRelation"], relationship("QueryPageRelation", back_populates="query"))
class Page(Base): #type:ignore
    __tablename__ = "page_table"
    
    id = cast(int, Column(Integer, primary_key=True, autoincrement=True))
    url = cast(str, Column(Text, nullable=False))
    title = cast(str, Column(Text, nullable=False))
    description = cast(str, Column(Text, nullable=False))
    timestamp = cast(str, Column(Text, nullable=False))
    
    html = cast(str, Column(Text, nullable=False))
    main_content = cast(str, Column(Text, nullable=False))
    pdf_content = cast(str, Column(JSON, nullable=False))
    image_content = cast(str, Column(JSON, nullable=False))
    
    queries = relationship("QueryPageRelation", back_populates="page")
class QueryPageRelation(Base): #type:ignore
    __tablename__ = "query_page_relation"
    
    query_id = cast(int, Column(Integer, ForeignKey("web_query_table.id"), primary_key=True))
    page_id = cast(int, Column(Integer, ForeignKey("page_table.id"), primary_key=True))
    
    index = cast(int, Column(Integer, nullable=False))
    
    query = relationship("WebQuery", back_populates="pages")
    page = cast("Page", relationship("Page", back_populates="queries"))
    
class CacheSystem:
    engine: Engine
    session: Session
    def __init__(self) -> None:
        raise NotImplementedError(f"Static class does not support instance")
    @classmethod
    def _get_user_query(cls, message: str) -> UserQuery | None:
        ss = CacheSystem.session
        return ss.query(UserQuery).filter_by(message=message).first()
    @classmethod
    def _get_web_query(cls, query: str) -> WebQuery | None:
        ss = CacheSystem.session
        return ss.query(WebQuery).filter_by(query=query).first()
    @classmethod
    def _get_page(cls, url: str) -> Page | None:
        ss = CacheSystem.session
        return ss.query(Page).filter_by(url=url).first()
    @classmethod
    def get_by_user_query(cls, message: str) -> list[ProcessedResult] | None:
        user = cls._get_user_query(message)
        if user != None:
            return cls.get_by_web_query(user.web_query.query)
    @classmethod
    def get_web_query(cls, message: str) -> str:
        return cls._get_user_query(message).web_query.query#type:ignore
    @classmethod
    def get_by_web_query(cls, query: str) -> list[ProcessedResult] | None:
        ss = CacheSystem.session
        web = cls._get_web_query(query)
        if web != None:
            result: list[ProcessedResult] = []
            for rel in web.pages:
                page: Page = rel.page
                if rel == None: raise Exception(f"[Cache] Not found relation of web:{web.id} and page:{page.id}")
                page_info: ProcessedResult = {
                    "url": page.url,
                    "title": page.title,
                    "description": page.description,
                    "timestamp": page.timestamp,
                    "html": page.html,
                    "main_content": page.main_content,
                    "index": rel.index,
                    "pdf_content": json.loads(page.pdf_content),
                    "image_content": json.loads(page.image_content)
                }
                result.append(page_info)
            return result
    @classmethod
    def cache_if_not_exists(
        cls,
        message: str,
        query: str,
        data: list[ProcessedResult]
    ):
        ss = CacheSystem.session
        user = cls._get_user_query(message)
        if user != None: return # Aldready cached
        user = UserQuery()
        user.message = message
        ss.add(user)
        ss.flush()
        
        web = cls._get_web_query(query)
        if web != None: # Aldready cached, only new UserQuery that match web query
            user.web_query_id = web.id
            ss.commit()
            return
        web = WebQuery()
        web.query = query
        ss.add(web)
        ss.flush()
        user.web_query_id = web.id
        
        for index, page_info in enumerate(data):
            page = cls._get_page(page_info["url"])
            if page == None:
                page = Page()
                page.url = page_info["url"]
                page.title = page_info["title"]
                page.description = page_info["description"]
                page.timestamp = page_info["timestamp"]
                page.html = page_info["html"]
                page.main_content = page_info["main_content"]
                page.pdf_content = json.dumps(page_info["pdf_content"])
                page.image_content = json.dumps(page_info["image_content"])
                ss.add(page)
                ss.flush()
            rel = QueryPageRelation()
            rel.page_id = page.id
            rel.query_id = web.id
            rel.index = index
            ss.add(rel)
        ss.commit()
        return True
    
    @classmethod
    def setup(cls, uri: str = "sqlite:///cache/cache.db", echo: bool = False):
        folder_path = os.path.dirname(urlparse(uri).path.lstrip("/"))
        os.makedirs(folder_path, exist_ok=True)
        CacheSystem.engine = create_engine(uri, echo=echo)
        Base.metadata.create_all(CacheSystem.engine)
        CacheSystem.session = sessionmaker(bind=CacheSystem.engine)()
    @classmethod
    def commit(cls):
        CacheSystem.session.commit()
    @classmethod
    def rollback(cls):
        CacheSystem.session.rollback()
    @classmethod
    def close(cls):
        CacheSystem.session.close()
        CacheSystem.engine.dispose()