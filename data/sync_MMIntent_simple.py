#!/usr/bin/env python3
"""MMIntentsRAG sync script - simplified for list format"""

import asyncio
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "mm_intents_rag"
VECTOR_SIZE = 4096


async def get_embedding(text: str):
    from services.api.services.embedding_service import get_embedding_service

    svc = get_embedding_service()
    return await svc.generate_embedding(text)


def main():
    json_path = Path(__file__).parent / "../datalake-system/data/MMIntentsRAG.json"

    with open(json_path) as f:
        data = json.load(f)

    intents = data.get("intents", [])
    logger.info(f"Found {len(intents)} intents")

    client = QdrantClient(host="localhost", port=6333)

    # Create collection
    try:
        client.delete_collection(COLLECTION_NAME)
    except:
        pass

    client.create_collection(
        COLLECTION_NAME, vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )

    points = []
    for idx, intent in enumerate(intents):
        name = intent.get("intent_name")
        desc = intent.get("description", "")
        examples = intent.get("examples", [])
        category = intent.get("category", "")

        text = desc + "\n" + "\n".join(examples)

        try:
            embedding = asyncio.run(get_embedding(text))
        except Exception as e:
            logger.warning(f"Failed to embed {name}: {e}")
            continue

        points.append(
            PointStruct(
                id=idx + 1,
                vector=embedding,
                payload={
                    "intent_name": name,
                    "description": desc,
                    "category": category,
                    "examples": examples,
                },
            )
        )
        logger.info(f"Prepared: {name}")

    if points:
        client.upsert(COLLECTION_NAME, points)
        logger.info(f"Uploaded {len(points)} points")
    else:
        logger.warning("No points uploaded")


if __name__ == "__main__":
    main()
