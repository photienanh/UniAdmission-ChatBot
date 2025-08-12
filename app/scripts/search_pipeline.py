if __name__ == "__main__":
    from search_engines.pipeline import SearchPipeline, ProcessedResult
    pipeline = SearchPipeline()
    result = pipeline("ba công khai đại học hà nội", 3, False)