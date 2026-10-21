from __future__ import annotations

import argparse

from agents.tools.functions.ingest.documents import ingest_file_to_qdrant


def ingest_paths(paths: list[str], semantic: bool = True) -> list[dict]:
	"""Ingest evaluation knowledge documents into the configured Qdrant collection."""
	return [ingest_file_to_qdrant(path, semantic=semantic, allow_eval_dataset=True) for path in paths]


def main() -> None:
	parser = argparse.ArgumentParser(description="Ingest documents for RAG evaluation")
	parser.add_argument("paths", nargs="+", help="Documents to ingest")
	parser.add_argument("--no-semantic", action="store_true", help="Use fixed-size chunks")
	args = parser.parse_args()
	for result in ingest_paths(args.paths, semantic=not args.no_semantic):
		print(result)


if __name__ == "__main__":
	main()
