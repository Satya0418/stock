from typing import Dict


class MLSignalEngine:
    def score(self, features: Dict[str, float]) -> Dict[str, float]:
        return {
            'score': 0.0,
            'confidence': 0.0,
        }
