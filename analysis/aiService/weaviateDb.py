import logging
from contextlib import contextmanager

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.data import DataObject
from weaviate.classes.query import MetadataQuery
from weaviate.util import generate_uuid5

logger = logging.getLogger(__name__)

WEAVIATE_HOST = "localhost"
WEAVIATE_HTTP_PORT = 8999
WEAVIATE_GRPC_PORT = 50051

# Cosine distance cutoff for example lookups. Measured with 150-word transcript chunks
# as queries: relevant examples ~0.3-0.7, same category from another product ~0.75,
# unrelated text ~0.89. Lower it to be stricter.
MAX_DISTANCE = 0.8


@contextmanager
def _client():
    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST, port=WEAVIATE_HTTP_PORT, grpc_port=WEAVIATE_GRPC_PORT
    )
    try:
        yield client
    finally:
        client.close()


def storeData(name, contents):
    with _client() as client:
        if not client.collections.exists(name):
            print("creating the " + str(name) + " schema")
            client.collections.create(
                name,
                properties=[Property(name="content", data_type=DataType.TEXT)],
                # Embed only the text: by default Weaviate prepends the collection name to every
                # stored object (but not to queries), which skews all distances.
                vector_config=Configure.Vectors.text2vec_transformers(vectorize_collection_name=False),
            )
        collection = client.collections.get(name)
        objects = []
        for content in contents:
            properties = {"content": content}
            objects.append(DataObject(properties=properties, uuid=generate_uuid5(properties)))
        if objects:
            collection.data.insert_many(objects)


def fetch_top_k_nearest_content(name, queries, k_size=2, max_distance=MAX_DISTANCE):
    """Return up to k_size (content, distance) pairs nearest to any of the query texts.

    Matches farther than max_distance are dropped, so fewer than k_size (or none)
    may come back. Pass max_distance=None to disable the cutoff.

    Returns [] if Weaviate is unreachable or the collection doesn't exist, so
    classification still works without examples.
    """
    if isinstance(queries, str):
        queries = [queries]
    try:
        with _client() as client:
            if not client.collections.exists(name):
                return []
            collection = client.collections.get(name)
            best = {}
            for query in queries:
                res = collection.query.near_text(
                    query=query,
                    limit=k_size,
                    distance=max_distance,
                    return_metadata=MetadataQuery(distance=True),
                )
                for obj in res.objects:
                    content = obj.properties["content"]
                    distance = obj.metadata.distance
                    if content not in best or distance < best[content]:
                        best[content] = distance
            return sorted(best.items(), key=lambda item: item[1])[:k_size]
    except Exception as exc:
        print(f"Weaviate lookup failed for {name}: {exc}")
        logger.warning("Weaviate lookup failed for %s: %s", name, exc)
        return []


# opening_statement_example = [
#     "Excellent, well, I haven?t spoken to you about this before, but I want to show you some exciting information about Gaboderm ointment for your moderate to severe eczema patients.
#     These are patients who are having frequent flares, so the chances are that you?ll be seeing them in the practice on a regular basis. It would be great if you could identify one of these patients to use
#     Gaboderm in and see how it reduces their flares for yourself.",
#     "Thank you, Doctor, for your time. This call is about the lipid management of your CHD patients.",
#     "So, it's about your CHD risk patients who, despite maximum statin and Acetamib therapy, do not reach their LDL targets. Is that alright with you?",
# ]
# storeData("OPENING_STATEMENT_EXAMPLE", opening_statement_example)

# print(fetch_top_k_content("OPENING_STATEMENT_EXAMPLE", 3, []))
# print(fetch_top_k_nearest_content("OPENING_STATEMENT_EXAMPLE",  "are you alright", 2,['distance']))
