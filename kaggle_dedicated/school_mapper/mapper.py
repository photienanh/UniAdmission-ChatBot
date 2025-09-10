import json
from rapidfuzz import process, fuzz

class SchoolMapper:
    def __init__(self, file_path: str) -> None:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.loads(file.read())
        self.acronym_data: list[dict[str, str]] = []
        self.normalized_names: list[str] = []
        self.acronyms: list[str] = []
        for item in data:
            acronym = item["acronym"].lower().strip() if item["acronym"] else ""
            entry = {
                "normalized_name": item["normalized_name"].lower().strip(),
                "name": item["name"].lower().strip(),
                "netloc": [item["netloc"]],
                "acronym": acronym
            }
            self.acronyms.append(acronym)
            self.normalized_names.append(item["normalized_name"])
            self.acronym_data.append(entry)
            
    def domains_from_auto(self, name: str, top_k: int = 3) -> list[str]:
        results: list[str] = []
        acronym = self._direct_acronym(name)
        if acronym: 
            for item in self.acronym_data:
                if item["acronym"] == acronym:
                    results.extend(item["netloc"])
            return results
        acronym = self._direct_name_matching(name)
        if acronym: 
            for item in self.acronym_data:
                if item["acronym"] == acronym:
                    results.extend(item["netloc"])
            return results
        acronyms = self._fuzzy_match_highest(name, top_k)
        for acronym in acronyms:
            for item in self.acronym_data:
                if item["acronym"] in acronyms:
                    results.extend(item["netloc"])
            return results
        return results
    def acronym_from_name(self, name: str) -> str | None:
        acronym = self._direct_acronym(name)
        if acronym: return acronym
        acronym = self._direct_name_matching(name)
        if acronym: return acronym
        acronyms = self._fuzzy_match(name, 1, 0.5)
        if len(acronyms) > 0:
            return acronyms[0]
    def _direct_acronym(self, acronym: str) -> str | None:
        if acronym.lower() in self.acronyms:
            return acronym
    def _direct_name_matching(self, name: str) -> str | None:
        if name.lower() in self.normalized_names:
            for item in self.acronym_data:
                if item["normalized_name"] == name.lower():
                    return item["acronym"]
    def _fuzzy_match(self, query: str, top_k: int, threshold: float) -> list[str]:
        """Use Levenshtein distance"""
        query = query.lower().strip()
        matches = process.extract(query, self.normalized_names, scorer=fuzz.partial_ratio, limit=top_k)
        matched_names: list[str] = []
        threshold = int(threshold * 100)
        for name, score, _ in matches:
            if score >= threshold:
                print(score, name)
                matched_names.append(name)
                
        acronymns: list[str] = []
        for item in self.acronym_data:
            if item["normalized_name"] in matched_names:
                acronymns.append(item["acronym"])
        return acronymns
    def _fuzzy_match_highest(self, query: str, top_k: int) -> list[str]:
        """Use Levenshtein distance"""
        query = query.lower().strip()
        matches = process.extract(query, self.normalized_names, scorer=fuzz.partial_ratio, limit=len(self.normalized_names))
        matched_names: list[str] = []
        max_score = matches[0][1]
        for name, score, _ in matches:
            if score == max_score:
                print( "E",name, score)
                matched_names.append(name)
            elif len(matched_names) < top_k:
                print(name, score)
                matched_names.append(name)
                
        acronymns: list[str] = []
        for item in self.acronym_data:
            if item["normalized_name"] in matched_names:
                acronymns.append(item["acronym"])
        return acronymns
    
if __name__ == "__main__":
    mapper = SchoolMapper("school_mapper/name.json")
    print(mapper.domains_from_auto("đại học công nghệ uet", 5))