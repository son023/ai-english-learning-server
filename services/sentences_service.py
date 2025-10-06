import os
import csv
from typing import List, Dict


class SentencesService:
    """Service to load structured sentences from a CSV source.

    The CSV is expected to have three columns (with header):
    "chủ đề","tình huống","câu tiếng anh"
    """

    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path

    def load_sentences(self) -> List[Dict[str, str]]:
        if not os.path.exists(self.csv_path):
            return []

        rows: List[Dict[str, str]] = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            _ = next(reader, None)  # skip header
            for r in reader:
                if not r or len(r) < 3:
                    continue
                topic, scenario, sentence = r[0], r[1], r[2]
                topic = topic.strip().strip('"')
                scenario = scenario.strip().strip('"')
                sentence = sentence.strip().strip('"')
                if not topic or not scenario or not sentence:
                    continue
                rows.append({
                    "topic": topic,
                    "scenario": scenario,
                    "sentence": sentence,
                })

        return rows


