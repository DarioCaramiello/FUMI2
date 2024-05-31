class SpatialQueryManager:

    client_postgresql = None

    def __init__(self, client_postgresql) -> None:
        self.client_postgresql = client_postgresql

    def spatial_query_point(self, lon, lat):
        cur = self.client_postgresql.cursor()
        query = sql.SQL("SELECT nome_comune FROM comune WHERE ST_Contains(box, ST_SetSRID(ST_MakePoint(%s, %s), 4326));")
        cur.execute(query, [lon, lat])
        result = cur.fetchall()
        cur.close()

        result_filtrated = []

        for place in result:
            if "Comune" in str(place):
                result_filtrated.append(place)

        return result_filtrated


    def spazial_query_box(self, b_box):
        srid = 4326
        polygon_wkt = f"SRID={srid};POLYGON(({', '.join([f'{x} {y}' for x, y in b_box])}))"
        cur = self.client_postgresql.cursor()
        query = sql.SQL("SELECT * FROM comune WHERE ST_Intersects(box, ST_GeomFromText(%s))")
        cur.execute(query, [polygon_wkt])
        result = cur.fetchall()
        cur.close()

        result_filtrated = []

        for place in result:
            if "Comune" in str(place):
                result_filtrated.append(place)

        return result_filtrated