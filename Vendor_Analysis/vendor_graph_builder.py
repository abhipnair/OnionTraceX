from collections import defaultdict

class VendorGraphBuilder:
    def __init__(self, pool):
        self.pool = pool

    async def build_graph(self):
        async with self.pool.acquire() as conn:

            artifacts = await conn.fetch("""
                SELECT vendor_id, artifact_type, artifact_value
                FROM VendorArtifacts
                WHERE vendor_id IS NOT NULL;
            """)

        artifact_map = defaultdict(list)

        for row in artifacts:
            key = (row["artifact_type"], row["artifact_value"])
            artifact_map[key].append(row["vendor_id"])

        edges = defaultdict(int)

        for (_, _), vendors in artifact_map.items():
            for i in range(len(vendors)):
                for j in range(i + 1, len(vendors)):
                    pair = tuple(sorted((vendors[i], vendors[j])))
                    edges[pair] += 1

        nodes = list(set(v["vendor_id"] for v in artifacts))

        return {
            "nodes": nodes,
            "edges": [
                {"source": k[0], "target": k[1], "weight": v}
                for k, v in edges.items()
            ]
        }
