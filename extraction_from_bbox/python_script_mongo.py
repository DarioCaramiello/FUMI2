from pymongo import MongoClient
import psycopg2
from psycopg2 import sql
from pykml import parser
from pykml.factory import nsmap

conn_params = {
            "host": "db",
            "database": "citizix_db",
            "user": "citizix_user",
            "password": "S3cret"
        }

client_postgresql = psycopg2.connect(**conn_params)

client_mongodb = MongoClient("mongodb://localhost:27017/")


def inizialize_postgresql_from_mongodb(client_mongodb, client_postgresql):

    # create a table with 2 fields : long_name (text) - box (geometry-polygon - projection 4326)
    cur = client_postgresql.cursor()

    create_table_query = sql.SQL("""
    CREATE TABLE IF NOT EXISTS comune (
        id INT PRIMARY KEY,
        nome_comune TEXT,
        box GEOMETRY(Polygon, 4326)
    )
    """)

    cur.execute(create_table_query)
    cur.close()
    client_postgresql.commit()

    # extracting collection places from MONGODB
    db = client_mongodb['test-db']
    collection = db['places']
    places = collection.find()

    id_test = 0

    for place in places:

        # step 1 : extracting name and bounding box form 'places' collection from mongodb
        long_name = place['long_name']['it']
        bounding_box = place['bbox']

        # step 2
        # create a new tupla with long_name and bounding_box extracted
        # insert the new tupla into the table in postgresql
        polygon_wkt = f"POLYGON(({', '.join([f'{x} {y}' for x, y in bounding_box['coordinates']])}))"
        cur = client_postgresql.cursor()
        query = sql.SQL("INSERT INTO comune (id, nome_comune, box) VALUES (%s, %s, ST_GeomFromText(%s))")
        # if long_name == "Comune di Valverde" or long_name == "Comune di Calliano":
        #    pass
        # else:
        cur.execute(query, [id_test, long_name, polygon_wkt])
        id_test+=1
        print("[*] Insert : " + long_name + " -- box : " + str(bounding_box['coordinates']))
        cur.close()
        client_postgresql.commit()

    print("[*] Municipalities table created and populated")


'''
def read_polygon_from_kml(name_file):

    namespace = {"ns": nsmap[None]}
    coordinates_list_out = []
    coordinates_list_out2 = []

    with open(name_file) as f:
        root = parser.parse(f).getroot()
        pms = root.xpath(".//ns:Placemark[.//ns:LineString]",   namespaces=namespace)

        for pm in pms:

            string_coordinates = pm.LineString.coordinates

            
            print("[*] LineString ------------------------- ")
            print(string_coordinates)
            print("[*] LineString ------------------------- ")
            

            coordinates_list = str(string_coordinates).split()
            # Itera attraverso le coppie di coordinate e aggiungi all'array
            for coordinate_pair in coordinates_list:
                lon, lat = coordinate_pair.split(',')
                coordinates_list_out.append([float(lon), float(lat)])

            coordinates_list_out2.append(coordinates_list_out)
            # print("Array di coordinate:")
            # print(coordinates_array)
    return coordinates_list_out2



class HandlerSpatialQuery:

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
'''


if __name__ == '__main__':

    inizialize_postgresql_from_mongodb(client_mongodb, client_postgresql)

    
    # postgresql_query_handler = HandlerSpatialQuery(client_postgresql)

    '''
    result_query_point = postgresql_query_handler.spatial_query_point(14.2681, 40.8518)

    print("[*] point spatial query : ")
    for i in result_query_point:
        print("Common : " + str(i))


    port_of_naples_bbox = [
        [14.235, 40.8245],
        [14.293, 40.8245],
        [14.293, 40.8525],
        [14.235, 40.8525],
        [14.235, 40.8245]
    ]

    campania_bbox = [
        [13.5, 40.6],
        [15.2, 40.6],
        [15.2, 41.3],
        [13.5, 41.3],
        [13.5, 40.6]
    ]

    result_query_box = postgresql_query_handler.spazial_query_box(port_of_naples_bbox)
    print("[*] box spatial query - port of naples: ")
    for i in result_query_box:
        print("Common : " + str(i[1]))

    print("[----------------------------------------------]")


    result_query_box2 = postgresql_query_handler.spazial_query_box(campania_bbox)
    print("[*] box spatial query - campania :")
    for i in result_query_box2:
        print("Common : " + str(i[1]))
    '''

    # result_linestring = read_polygon_from_kml('/mydata.kml')
    # print(result_linestring)
    # print(str(type(result_linestring)))

    '''
    query_result = postgresql_query_handler.spazial_query_box(result_linestring[-1])

    for i in query_result:
        print("Common : " + str(i[1]))
    '''

