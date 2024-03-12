import os
import saucenaoconfig
import logwriter
import sqlite3
from sqlite3 import Error
from colorama import Fore, Style

config = saucenaoconfig.config()


class database():
    def __init__(self):
        self.db_name = config.settings["DATABASE_NAME"]
        self.init_setup()


    def create_connection(self):
        return sqlite3.connect(self.db_name)


    def execute_nonquery(self, query, params = ()) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            try:
                conn = self.create_connection()
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.execute(query, params)
            except Error as e:
                print(f"{Fore.RED}{e}{Style.RESET_ALL}")
                return False
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
            print(f"{Fore.RED}{e}{Style.RESET_ALL}")
            results = None
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
            print(f"{Fore.RED}{e}{Style.RESET_ALL}")
            result = None
        finally:
            if conn:
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
            print(f"{Fore.RED}{e}{Style.RESET_ALL}")
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


    def migrate_log(self):
        unique_files = set(logwriter.extract_log("./saucenao_log.txt"))
        logs = [l.split(",") for l in unique_files]
        queries = []
        for sim, full_path, illus_id, status in logs:
            file_name, ext = os.path.splitext(os.path.split(full_path)[1])
            status = status.replace("\n","")
            queries.append(f'INSERT INTO Images (file_name, full_path, ext) VALUES ("{file_name}", "{full_path}", "{ext}");')
            queries.append("INSERT INTO Saucenao_Results (image_uid, site_flag, site_id, similarity, status)" + 
                           f"VALUES (last_insert_rowid(), {512}, {illus_id}, {sim}, {status == 'n'});")
        self.execute_mass_transaction(queries)
        print("Done")
                
        
#var = database()
#var.migrate_log()