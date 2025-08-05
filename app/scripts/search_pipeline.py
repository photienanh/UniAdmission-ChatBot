if __name__ == "__main__":
    from search_engines import SearchPipeline, ProcessedResult
    pipeline = SearchPipeline()
    result = pipeline("Tuyển sinh Đại học Công nghệ", 5, True)