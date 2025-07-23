import os
from config import *
from utility import ProcessingManager
import sqlite3
from concurrent.futures import ThreadPoolExecutor

alchemy_db_path = "sqlite:///data/sqlite/sqlite.db"
db_path = "data/sqlite/sqlite.db"

def retrieve_all_doc_ids(file_path: str):
    conn = sqlite3.connect(file_path)
    conn.execute("PRAGMA journal_model=WAL")
    with conn:
        query = "SELECT id FROM document"
        res = conn.execute(query)
        ids = [row[0] for row in res.fetchall()]
        return ids
def run():
    ids = retrieve_all_doc_ids(db_path)
    db_executor = ThreadPoolExecutor(1) # Only support 1 executor
    cmd_logger = lambda tid:CmdLogger()
    simple_processor = lambda tid:Crawler4AIProcessor() # Just diffirent in this line
    sqlite_provider = lambda tid:SQLiteProvider(db_path, db_executor)
    sqlite_consumer = lambda tid:SQLiteConsumer(db_path, db_executor, min_threshold=2000)
    manager = ProcessingManager(
        num_workers=4,
        concurrent_per_worker=4,
        ids=ids,
        provider_factory=sqlite_provider,
        consumer_factory=sqlite_consumer,
        processor_factory=simple_processor,
        logger_factory=cmd_logger
    )
    manager.run()


if __name__ == "__main__":
    run()