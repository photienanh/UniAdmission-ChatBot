import sqlite3
class PerformanceSQLite:
    def __init__(self, file_path: str, auto_start: bool = True):
        self.file_path = file_path
        if auto_start:
            self.setup()
    def setup(self):
        self.conn = sqlite3.connect(self.file_path)
        self.conn.execute("PRAGMA journal_model=WAL")
    def add_html(self, school_id: int, url: str, index: int, html: str):
        with self.conn:
            query = "INSERT INTO document (school_id, url, doc_index, html) VALUES (?, ?, ?, ?)"
            self.conn.execute(
                query,
                (school_id, url, index, html)
            )
    def retrieve_html(self, id: int) -> tuple[str, str, str]:
        with self.conn:
            query = "SELECT url, title, html FROM document WHERE id = ?"
            res = self.conn.execute(query, (id, ))
            row = res.fetchone()
            if row is None:
                err = f"Not found {id}"
                raise Exception(err)
            else:
                return row
    def add_text(self, id: int, title: str, text: str):
        with self.conn:
            query = "UPDATE document SET text = ?, title = ? WHERE id = ?"
            self.conn.execute(
                query, (text, id, title)
            )
    def add_valid_travel_log(self, school_id: int, index: int, score: float, retry: int, from_url: str, url: str):
        with self.conn:
            query = "INSERT INTO travel_log (school_id, travel_index, valid, score, retry, from_url, url) VALUES (?, ?, ?, ?, ?, ?, ?)"
            self.conn.execute(
                query,
                (school_id, index, 1, score, retry, from_url, url)
            )
    def add_invalid_travel_log(self, school_id: int, index: int, from_url: str, url: str):
        with self.conn:
            query = "INSERT INTO travel_log (school_id, travel_index, valid, from_url, url) VALUES (?, ?, ?, ?, ?)"
            self.conn.execute(
                query,
                (school_id, index, 0, from_url, url)
            )
    def add_error_log(self, school_id: int, time: str, index: int, retry: int, from_url: str, url: str, content: str):
        with self.conn:
            query = "INSERT INTO error_log (school_id, time, travel_index, retry, from_url, url, content) VALUES (?, ?, ?, ?, ?, ?, ?)"
            self.conn.execute(
                query,
                (school_id, time, index, retry, from_url, url, content)
            )
    def close(self):
        self.conn.close()
        
