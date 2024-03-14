import sys
import sqlite3
from sqlite3 import Error
import src.saucenaoconfig as saucenaoconfig

IS_DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None 

config = saucenaoconfig.config()


class database():
    def __init__(self):
        self.db_instance = config.settings["IMG_DATABASE"] if not IS_DEBUG else config.settings["TEST_IMG_DATABASE"]
        self.init_setup()


    def create_connection(self):
        return sqlite3.connect(self.db_instance)


    def execute_nonquery(self, query, params = ()) -> bool:
        with sqlite3.connect(self.db_instance) as conn:
            try:
                conn = self.create_connection()
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.execute(query, params)
            except Error as e:
                raise Exception(f"Error:{e}\nQuery:{query}\nParmas:{params}")
            finally:
                if conn:
                    conn.close()
                    
            return True

                
    def execute_query(self, query, params = ()) -> list[any]:
        results = None
        try:
            conn = self.create_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute(query, params)
            results = cursor.fetchall()
        except Error as e:
            raise Exception(f"Error:{e}\nQuery:{query}\nParmas:{params}")
        finally:
            if conn:
                conn.close()
                
        return results


    def execute_change(self, query, params = ()) -> int:
        result = None
        try:
            conn = self.create_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute(query, params)
            conn.commit()
            result = cursor.lastrowid
        except Error as e:
            raise Exception(f"Error:{e}\nQuery:{query}\nParmas:{params}")
        finally:
            if conn:
                conn.rollback()
                conn.close()
                
        return result


    def execute_mass_transaction(self, queries:str | list[str], params = ()):
        """Used for larged scaled queries, such as large data transfers.

        Args:
            queries (list[str]): List of all queries to be provided
        """
        try:
            conn = self.create_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("BEGIN TRANSACTION")

            if queries is str:
                cursor.executemany(queries, params)
            else:
                for query in queries:
                    cursor.execute(query, params)

            cursor.execute("END TRANSACTION")
            conn.commit()
        except Error as e:
            raise Exception(f"Error:{e}\nQuery:{query}\nParmas:{params}")
        finally:
            if conn:
                conn.close()


    def init_setup(self):
        self.execute_nonquery("""
            CREATE TABLE IF NOT EXISTS Status (
                status          INTEGER     UNIQUE,
                status_type     TEXT
            )
        """)
        if not self.execute_query("SELECT * FROM Status"):
            self.execute_change("""
                INSERT INTO Status VALUES
                (0, "Unknown"),
                (1, "No Match")
            """)

        self.execute_nonquery("""
            CREATE TABLE IF NOT EXISTS Images (
                image_uid   INTEGER     PRIMARY KEY,
                file_name   TEXT,
                full_path   TEXT        UNIQUE,
                ext         TEXT
            )
        """)
        self.execute_nonquery("""
            CREATE TABLE IF NOT EXISTS Saucenao_Results (
                result_uid  INTEGER     PRIMARY KEY,
                image_uid   INTEGER,
                site_flag   INTEGER,
                site_id     INTEGER,
                similarity  REAL,
                status      INTEGER,
                FOREIGN KEY (image_uid)
                    REFERENCES Images(image_uid) ON DELETE CASCADE,
                FOREIGN KEY (status)
                    REFERENCES Status(status)
            )
        """)
        # Maybe add this later, but for now we're only using danbooru
        #FOREIGN KEY (site_flag)
        #    REFERENCES Websites (site_flag)
        #websites_table_query = """
        #    CREATE TABLE IF NOT EXISTS Websites (
        #        site_flag      INTEGER     PRIMARY KEY,
        #        hostname       TEXT,
        #    )
        #"""


class Image:
    def __init__(self, datarow):
        self.image_uid = datarow[0]
        self.file_name = datarow[1]
        self.full_path = datarow[2]
        self.ext = datarow[3]

class Saucenao_Result:
    def __init__(self, datarow):
        self.result_uid = datarow[0]
        self.image_uid = datarow[1]
        self.site_flag = datarow[2]
        self.site_id = datarow[3]
        self.similarity = datarow[4]
        self.status = datarow[5]