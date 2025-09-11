import asyncio, json
from dotenv import load_dotenv
from data_retriever.search_engines import GoogleSearchEngine, BraveSearchEngine
from data_retriever import DataRetrieverPipeline, SearchResult
from server import GenerationParams

with open("worker.env", 'r') as file:
    load_dotenv(stream=file)

async def main_google():
    engine = GoogleSearchEngine()
    results = await engine.search(
            query="điểm chuẩn", 
            domain_restrict=None,
            school_domains=["uet.vnu.edu.vn"],
            time_metric="y",
            time_range=1
        )
    with open("results.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(results, ensure_ascii=False))
async def main_brave():
    engine = BraveSearchEngine()
    results = await engine.search(
            query="điểm chuẩn", 
            domain_restrict=None,
            school_domains=["uet.vnu.edu.vn"],
            time_metric="y",
            time_range=None
        )
    with open("results.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(results, ensure_ascii=False))

async def main_pipeline():
    class DummyModel:
        async def rerank_page(self, pages: list[SearchResult], query: str, relative_threshold: float, params: GenerationParams) -> list[SearchResult]:
            """
            Perform llm rerank with pages.
            """
            return pages[:5]
    pipeline = DataRetrieverPipeline(DummyModel())
    await pipeline.start()
    params: GenerationParams = {
        "model_id": "dummy"
    }
    result = await pipeline.retrieve(
        params,
        ["điểm chuẩn uet", "điểm chuẩn hust"]
    )
    with open("total.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(result, ensure_ascii=False))
    await pipeline.stop()
asyncio.run(main_pipeline())