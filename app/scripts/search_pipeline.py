import asyncio
if __name__ == "__main__":
    # from search_engines.pipeline import SearchPipeline, ProcessedResult
    # async def main():
    #     pipeline = SearchPipeline(
    #         page_timeout=10,
    #         file_timeout=30,
    #         concurrent_page=4,
    #         concurrent_processor_download=4
    #     )
    #     result = await pipeline.call_fast("ba công khai đại học hà nội", 5, False)
    #     print("Finished")
    #     await pipeline.close()
    # asyncio.run(main())
    from search_engines_caching import Websearch
    async def main():
        ws = Websearch("intfloat/multilingual-e5-small")
        await ws(
            "ba công khai đại học bách khoa hà nội", 
            "ba công khai đại học bách khoa hà nội", 
            5, 10, True, "google", True, False)
        await ws.close()
        del ws
    asyncio.run(main())