import sqlite3
from sqlite3 import Error
import src.saucenaoconfig as saucenaoconfig
from enum import Enum

config = saucenaoconfig.config


class __database():
    def __init__(self):
        self.db_instance = config.settings["IMG_DATABASE"] if not saucenaoconfig.IS_DEBUG else config.settings["TEST_IMG_DATABASE"]
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
            conn.row_factory = sqlite3.Row
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
            conn.rollback()
            raise Exception(f"Error:{e}\nQuery:{query}\nParmas:{params}")
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
            raise Exception(f"Error:{e}\nQuery:{query}\nParmas:{params}")
        finally:
            if conn:
                conn.close()


    def init_setup(self):
        for x in ["Saucenao_Results", "Images"]:
            self.execute_nonquery(f"""
                CREATE TABLE IF NOT EXISTS Status_{x} (
                    status          INTEGER     PRIMARY KEY,
                    status_type     TEXT
                )
            """)
        if not self.execute_query("SELECT * FROM Status_Saucenao_Results"):
            self.execute_change("""
                INSERT INTO Status_Saucenao_Results VALUES
                (0, "Unknown"),
                (1, "No Match")
            """)
        if not self.execute_query("SELECT * FROM Status_Images"):
            self.execute_change("""
                INSERT INTO Status_Images VALUES
                (1, "Full Scan"),
                (2, "MD5 Only Scan")
            """)

        self.execute_nonquery("""
            CREATE TABLE IF NOT EXISTS Images (
                image_uid INTEGER PRIMARY KEY,
                file_name TEXT,
                full_path TEXT    UNIQUE
                                  NOT NULL,
                ext       TEXT,
                md5       TEXT    UNIQUE
                                  NOT NULL,
                status    INTEGER DEFAULT 1,
                FOREIGN KEY (status)
                    REFERENCES Status_Images(status)
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
                    REFERENCES Status_Saucenao_Results(status)
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


db_handler = __database()


class Parameter():
    class Type(Enum):
        AND = 0,
        OR = 1

    class Condition(Enum):
        EQUAL = 0,
        GREATER = 1,
        GRTOREQUAL = 2,
        LESS = 3,
        LESOREQUAL = 4,
        IN = 5

    def __init__(self, col_name:str, value, search_condition:Condition = Condition.EQUAL, search_type:Type = Type.AND):
        """An object to simplify writing conditional clauses to query strings.

        Args:
            col_name (str): Name of the column to be searched.
            value (any): Value to search for.
            search_condition (search_condition, optional): The type of condition to search for i.e. '=', 'IN', '>', etc. Defaults to 'EQUAL'. If value is list, overrides to 'IN'
            search_type (search_type, optional): Specify whether searching by AND or OR. Defaults to 'AND'.
        """
        self.col_name = col_name
        self.value = value
        self.condition = search_condition if not type(value) is list else self.Condition.IN
        self.type = search_type 
        
   
    def __get_condition(self):
        match self.condition:
            case self.Condition.EQUAL:
                return " = "
            case self.Condition.GREATER:
                return " > "
            case self.Condition.GRTOREQUAL:
                return " >= "
            case self.Condition.LESS:
                return " < "
            case self.Condition.LESOREQUAL:
                return " <= "
            case self.Condition.IN:
                return " IN "


    def __get_type(self):
        match self.type:
            case self.Type.AND:
                return " AND "
            case self.Type.OR:
                return " OR "
        
        
    def get_where(self) -> str:
        query = f"{self.__get_type()}{self.col_name}{self.__get_condition()}"
        if type(self.value) is list:
            query += f"({','.join('?' for _ in self.value)})"
        else:
            query += "?"
        return query