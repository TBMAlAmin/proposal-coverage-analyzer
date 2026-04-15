from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark import run_benchmark


def main() -> None:
    dataset = ROOT / "data" / "benchmark" / "coverage_benchmark.json"
    report = run_benchmark(dataset)
    print(f"Overall accuracy: {report['overall_accuracy']:.3f}")
    print(f"Cases: {report['total_cases']}")
    print(f"Labeled items: {report['total_items']}")
    print("")
    for result in report["results"]:
        print(
            f"- {result.name}: accuracy={result.accuracy:.3f} "
            f"({result.correct}/{result.total}), expected covered={result.covered_expected}, "
            f"partial={result.partial_expected}, missing={result.missing_expected}"
        )


if __name__ == "__main__":
    main()
