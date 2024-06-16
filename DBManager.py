from itertools import tee
import sqlite3
import werkzeug
import os
import psycopg2

from datetime import datetime


class DBManager(): 

    # Connection and cursor objects 
    __connection = None
    __cursor = None

    # Init function that will store a cursor object once 
    def __init__(self, dbpath='gdal/sqlite-autoconf-3400100/FUMI2.db'):
        self.connect(dbpath)

   
    def execute(self, query):
        # Execute query and return the records
        self.__cursor.execute(query)
        record = self.__cursor.fetchall()
        return record

  
    def update(self, query, values=None):
        if values is not None: self.__cursor.execute(query, values)
        else: self.__cursor.execute(query)
        self.__connection.commit()

    def add(self, table, values):
        query = "INSERT INTO \"{}\" VALUES ({})".format(table, values)
        self.update(query)

    # Simple function that does remove a row from a table, given an id 
    def remove(self, table, key, value):

        # Delete query and update
        query = "DELETE FROM {} WHERE {}=\'{}\'".format(table, key, value)
        self.update(query)

    def add_specific(self, table, columns, values):
        # Create a specific query to insert values in and update
        query = "INSERT INTO \"{}\"({}) VALUES ({})".format(table, columns, values)
        # print(query)
        self.update(query)    

    # Simple function that updates a column with a new value given the table and the key
    def update_column(self, table, column, key, valuekeypair):
        #query = "UPDATE {} SET {}=? WHERE {}=?".format(table, column, key)
        query = f"UPDATE {table} SET {column}=%s WHERE {key}=%s"
        
        #query = "UPDATE " + table + " SET " + column + "=?" + " WHERE " + key + "=?" 
        self.update(query, valuekeypair)    

    # Function that given a column, table and keypair (column-value)) will retrieve its record/s
    def select(self, column, table, key=None, value=None):

        # Query string init
        query = ""

        # If we got a key, we must restrain our search for a specified value
        if key != None:
            
            # Simply build up a query composed by the input values:
            query = "SELECT {} FROM {} WHERE {}=\'{}\'".format(column, table, key, value)
        
        # Otherwise we must return some values for a certain table (without restriction)
        else:

            # As before, we build up the query
            query = "SELECT {} FROM {}".format(column, table) 

        # Execute query 
        record = self.execute(query)

        # Return the record
        return record 

    # Function that given a query string, will perform that query on the database
    def query(self, qstring):

        # query = ''' INSERT INTO projects(name,begin_date,end_date) VALUES(?,?,?) '''
        print("todo")

    ##############################
    #  Connection and utils functions
    # Function that will connect to the database and store the relative objects
    def connect(self, dbpath):
        
        db_params = {
            'host': 'db',  # Il nome del container PostgreSQL nella stessa rete
            'database': 'citizix_db',
            'user': 'citizix_user',
            'password': 'S3cret',
            'port': '5432',  # Assicurati che la porta corrisponda alla configurazione del tuo container PostgreSQL
        }

        try:
            # Init connection and store it
            #self.__connection = sqlite3.connect(dbpath)
            #self.__connection = sqlite3.connect('file:/sqlite3/root/db/fumi2new.db', check_same_thread=False)
            self.__connection = psycopg2.connect(**db_params)

            # Init a cursor to help us with db operatons and store it
            self.__cursor = self.__connection.cursor()

            # Activate the foreign keys 
            #self.__cursor.execute("PRAGMA foreign_keys=ON")

            # Commit
            self.__connection.commit()
                        
        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)

    # Connection function that will establish connection to the dbs
    def tryconn(self):
        
        # We do connect on a try/except block to the db
        try:

            # Init connection 
            if self.__connection is not None and self.__cursor is not None:
                print("Database created and Successfully Connected to SQLite")

            # Init a query 
            #sqlite_select_Query = "select sqlite_version();"
            sqlite_select_Query = "SELECT version();"

            # Execute query with the cursor and fetch the results
            self.__cursor.execute(sqlite_select_Query)
            record = self.__cursor.fetchall()
            print("SQLite Database Version is: ", record)

        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)

    # Function that will close the connection and the cursor
    def close(self):

        # Close cursor and connection if present
        if self.__cursor is not None: 
            self.__cursor.close()
        
        if self.__connection is not None:
            self.__connection.close()


# Class that wraps methods and logic of the database usage 
class DBProxy():
    
    # Init function with an object off dbmanager
    def __init__(self, dbpath='gdal/sqlite-autoconf-3400100/FUMI2.db'):
        self.__db = DBManager(dbpath)

    # add to Dario
    def return_user(self):
        record = self.__db.execute("select * from user")
        return record

    # add to Dario
    def return_all_jobs(self):
        record = self.__db.execute(" SELECT J.JOBID, JI.NAME_SIM, JI.\"DATE\", JI.\"TIME\", JI.DURATION, JI.COMMON, JI.LONG, JI.LAT, JI.TEMPERATURE, JI.CODICE_GISA, U.USERNAME, U.FIRSTNAME, U.LASTNAME FROM JOBS J JOIN JOBINFO JI ON J.JOBID = JI.JOBID JOIN \"USER\" U ON J.USERNAME = U.USERNAME;")
        return record
   
    #  Specific functions that have some purpose for our application (i.e: check users)
    def user_exists(self, username, password):

        # We check if the user exists performing a query with our select function
        record = self.__db.select("\"PASSWORD\"", "\"USER\"", "USERNAME", username)

        # Check if password is the same as the submitted one and return the result
        if record:
            return True if werkzeug.security.check_password_hash(record[0][0], password) else False
        else:
            return False

    # Function that calls the add_specific function from the DBManager class
    def specific_insert(self, table, columns, values):
        self.__db.add_specific(table, columns, values)

    # Function that calls the remove function from the DBManager class
    def delete_row(self, table, key, value):
        self.__db.remove(table, key, value)

    # Function that returns a specific value given the table, column and key 
    def specific_select(self, table, column, key, value):
        
        # We select a single value from the given table
        record =self.__db.select(column, table, key, value)

        # If the record is something we return the first occurence else none
        if record:
            return record[0][0]
        else:
            return None

    # Function that calls the update column function from the DBManager class
    def update_column(self, table, column, key, valuekeypair):
        self.__db.update_column(table, column, key, valuekeypair)

    # Simple function that returns a boolean regarding the activation status of an user
    def user_active(self, username):

        # We checkk if the user is active performing a simple query 
        record = self.__db.select("ACTIVE", "\"USER\"", "USERNAME", username)

        # Now we check if the user is active by controlling his role (0 non active, 1 active)
        if record: 
            return True if record[0][0]==1 else False
        else:
            return False 

    def is_admin(self, username):

        # We check if the user is an admin using the select function
        record = self.__db.select("\"ROLE\"", "\"USER\"", "USERNAME", username)

        # Now we check if the user is an admin by controlling his role (0 normal user, 1 admin)
        if record: 
            return True if record[0][0]==1 else False
        else:
            return False 

    # Simple function that uses db functionalities to update the last access
    def update_access(self, user):

        # Using the self.__db update access function
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S") 
        self.__db.update_column("\"USER\"", "LASTACCESS", "USERNAME", [dt_string, user]) 

    # Simple function that retrieves last access from the db
    def get_last_access(self, user):

        # Simply return the query value 
        return self.__db.select("LASTACCESS", "\"USER\"", "USERNAME", user)[0][0]

    # Simple function that given profile elements will update the corrispondent one 
    # in the database if different than an empty value
    def update_profile(self, user, firstname, lastname, password, telephone):

        # Update the values if different than the empty string
        if firstname != "": 
            self.__db.update_column("\"USER\"", "FIRSTNAME", "USERNAME", [firstname, user])

        # Update the values if different than the empty string
        if lastname != "": 
            self.__db.update_column("\"USER\"", "LASTNAME", "USERNAME", [lastname, user])

        # Update the values if different than the empty string
        if password != "": 
            self.__db.update_column("\"USER\"", "PASSWORD", "USERNAME", [password, user])

        # Update the values if different than the empty string
        if telephone != "": 
            self.__db.update_column("\"USER\"", "TELEPHONE", "USERNAME", [telephone, user])

    # Simple function that returns profile elements to show in the placeholders
    def get_profile(self, user):

        # Returning 
        profile_values = self.__db.select("FIRSTNAME, LASTNAME, TELEPHONE", "\"USER\"", "USERNAME", user)
        return profile_values[0]

    # Simple function that will return all the users in the system to be shown in the admin panel
    def fetch_users(self):
        # We build up a custom query because we'd like to show only users that are not admin. 
        #query = "SELECT FIRSTNAME, LASTNAME, USERNAME, TELEPHONE, EMAIL, ACTIVE FROM USER WHERE ROLE!=1"
        # query = "SELECT firstname, lastname, username, telephone, email, struttura, ruolotec, active FROM \"USER\" WHERE \"ROLE\"!=1"
        query = "SELECT firstname, lastname, username, telephone, email, struttura, ruolotec, active FROM \"USER\" ;"
        return self.__db.execute(query)

    def add_user(self, username, firstname, lastname, email, cellulare, struttura, ruolo):
        values = [username, firstname, lastname, email, cellulare, struttura, ruolo, 0]
        query = "INSERT INTO \"USER\" (USERNAME, FIRSTNAME, LASTNAME, EMAIL, TELEPHONE, STRUTTURA, RUOLOTEC, ACTIVE) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        self.__db.update(query, values)

    def add_group(self, name_group):
        value = [name_group]
        query = "INSERT INTO GROUPS (NAME_GROUP) VALUES (%s);"
        self.__db.update(query, value)
   
    def add_user_to_group(self, user, group, read_permisssion, write_permission):
        values = [user, group, read_permisssion, write_permission] 
        query = "INSERT INTO USER_GROUP (USERNAME, NAME_GROUP, READ_PERMISSION, WRITE_PERMISSION) VALUES (%s, %s, %s, %s);"
        # query = "INSERT INTO USER_GROUP (USERNAME, NAME_GROUP, READ_PERMISSION, WRITE_PERMISSION) VALUES \'{}\', {}, {}, {});".format(user, group, read_permisssion, write_permission)
        #self.__db.update(query)
        self.__db.update(query, values)
    
    def remove_user_to_group(self, user, group):
        # query = "DELETE FROM USER_GROUP WHERE USERNAME=\'{}\' ;".format(user)
        # self.__db.update(query)
        value = [user, group]
        query = "DELETE FROM USER_GROUP WHERE USERNAME=%s AND NAME_GROUP=%s;"
        self.__db.update(query, value)
 
    def change_user_permissions(self, user, group, permission, new_state):

        query = ""

        if permission == True : 
            query = "UPDATE USER_GROUP SET READ_PERMISSION=%s WHERE USERNAME=%s AND NAME_GROUP=%s ;"
        elif permission == False:
            query = "UPDATE USER_GROUP SET WRITE_PERMISSION=%s WHERE USERNAME=%s AND NAME_GROUP=%s ;"
            

        values = [new_state, user, group ]
        # query = "UPDATE USER_GROUP SET %s=%s WHERE USERNAME=%s AND NAME_GROUP=%s ;"
        self.__db.update(query, values)

    def get_info_job(self, id_job):
        query = "SELECT  \"TIME\", DURATION, \"DATE\", LONG, LAT FROM JOBINFO WHERE JOBID=\'{}\';".format(id_job)
        return self.__db.execute(query)

    # ritorna tutti i gruppi presenti nel sistema 
    def get_all_groups(self):
        query="SELECT NAME_GROUP FROM GROUPS;"
        return self.__db.execute(query)
    
    # ritorna tutti i gruppi di cui fa parte l'user
    def get_groups_user(self, user):
        query = "SELECT g.NAME_GROUP FROM USER_GROUP ug JOIN GROUPS g ON ug.NAME_GROUP = g.NAME_GROUP WHERE ug.USERNAME = \'{}\';".format(user)
        return self.__db.execute(query)

    def get_permission_of_group(self, user, group):
        query = "SELECT READ_PERMISSION, WRITE_PERMISSION FROM USER_GROUP WHERE USERNAME=\'{}\' AND NAME_GROUP=\'{}\' ;".format(user, group)
        return self.__db.execute(query)

    # ritorna tutte le associazioni gruppi-user
    def get_all_groups_with_user(self):
        query = "SELECT * FROM USER_GROUP;"
        return self.__db.execute(query)

    # Simple function that delete an user given his name
    def delete_user(self, user):

        # Querying the user table
        # query = 'DELETE FROM USER WHERE USERNAME=?'
        query = 'DELETE FROM \"USER\" WHERE USERNAME=%s'

        # Usin the update function to commit 
        self.__db.update(query, (user,))

    def create_group(self, name_group):
        quey = "INSERT INTO GROUPS (NAME_GROUP) VALUES (\'{}\');".format(name_group)
        self.__db.update(query)

    def fetch_jobs(self, user):
        query = '''SELECT NAME_SIM,\"DATE\",\"TIME\",DURATION,COMMON,LONG,LAT,TEMPERATURE,CODICE_GISA,JOBINFO.JOBID,GROUPS.NAME_GROUP
                    FROM JOBINFO 
                    JOIN JOBS ON JOBINFO.JOBID=JOBS.JOBID 
                    JOIN \"USER\" ON JOBS.USERNAME=\"USER\".USERNAME 
                    JOIN SIMULATION_GROUP ON JOBINFO.JOBID = SIMULATION_GROUP.JOBID
                    JOIN GROUPS ON SIMULATION_GROUP.NAME_GROUP = GROUPS.NAME_GROUP
                    WHERE \"USER\".USERNAME=\'{}\' 
                '''.format(user)        
        # returns values
        return self.__db.execute(query)
    
    def fetch_user_group(self, user, group):
        query = '''SELECT NAME_SIM,\"DATE\",\"TIME\",DURATION,COMMON,LONG,LAT,TEMPERATURE,CODICE_GISA,JOBINFO.JOBID,SIMULATION_GROUP.NAME_GROUP,JOBINFO.SEARCH_FIELD
                    FROM JOBINFO 
                    JOIN JOBS ON JOBINFO.JOBID=JOBS.JOBID 
                    JOIN \"USER\" ON JOBS.USERNAME=\"USER\".USERNAME 
                    JOIN SIMULATION_GROUP ON JOBINFO.JOBID = SIMULATION_GROUP.JOBID
                    JOIN GROUPS ON SIMULATION_GROUP.NAME_GROUP = GROUPS.NAME_GROUP
                    WHERE \"USER\".USERNAME=\'{}\' AND GROUPS.NAME_GROUP=\'{}\' ;
                '''.format(user, group)        
        # returns values
        return self.__db.execute(query)
        
    # Simple function that given a jobid, will return the output path associated 
    # with it
    def get_KML_path(self, jobid, basefolder="root"):

        # We use the select function to achieve this
        user_path = self.__db.select("PATH", "JOBIDENTIFIER", "JOBID", jobid)[0][0]

        # We then concat the root path to the outputh path
        storage_path = werkzeug.security.safe_join('storage/fumi2', user_path)

        # Then we get the name of the kml file
        filename = ""
        for file in os.listdir(werkzeug.security.safe_join(basefolder, storage_path)):
            if file.endswith(".kml"):
                filename=file

        # We then return the total filepath
        return werkzeug.security.safe_join(storage_path, filename)

    # Simple function that will return an output path associated with a specific job id 
    def get_output_path(self, jobid, basefolder="root"):

        # We use the select function to achieve this
        user_path = self.__db.select("PATH", "JOBIDENTIFIER", "JOBID", jobid)[0][0]

        # We then concat the root path to the outputh path and return it
        storage_path = werkzeug.security.safe_join('storage/fumi2', user_path)

        # Then we return the basefolder joined the storage 
        return werkzeug.security.safe_join(basefolder, storage_path)

    # Simple function that given a jobid will set the associated state in the 
    # JOBINFO table as true
    def set_complete(self, jobid):

        self.__db.update_column("JOBINFO", "COMPLETED", "JOBID", [1, jobid])

    # Simple function that insert a new job into the database, into the JOBINFO relative table.
    def new_job(self, jobinfo, user_groups, job_id):
        
        completed = 0

        string_search = ""

        for info in jobinfo:
            string_search = string_search + "; " + info + "; "

        print("- dbmanager - new job - " + str(string_search), flush=True)
        
         
        query_jobinfo = "INSERT INTO JOBINFO VALUES(\'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', \'{}\')".format(
            jobinfo[0], # job_id
            jobinfo[1], # name_simul
            jobinfo[2], # date
            jobinfo[3], # ora
            jobinfo[4], # durata
            jobinfo[5], # comuni
            jobinfo[6], # lon
            jobinfo[7], # lat
            jobinfo[8], # temp
            jobinfo[9], # codice_GISA
            completed,
            string_search
        )

        # print("[*] DBManager.py -- query_jobinfo = " + query_jobinfo, flush=True)
        query_jobs = "INSERT INTO JOBS VALUES(\'{}\', \'{}\')".format(jobinfo[0], jobinfo[10])
        # print("[*] DBManager -- query_job = " clear+ query_jobs, flush=True)
        self.__db.update(query_jobs)
        self.__db.update(query_jobinfo)

        for group in user_groups:
            query = "INSERT INTO SIMULATION_GROUP VALUES(\'{}\', \'{}\')".format(job_id, group[0])
            self.__db.update(query)

    # Simple function that will insert values into the JOBIDENTIFER table 
    def new_jobidentifier(self, jobidentifier_info):

        # The jobinfo array is so composed: 
        # jobid, date, time, path. 
        # We use those information to use the corrent index to pass into the insert value.
        query = "INSERT INTO JOBIDENTIFIER VALUES ({}, '{}', '{}', '{}')".format(
            jobidentifier_info[0],
            jobidentifier_info[1],
            jobidentifier_info[2],
            jobidentifier_info[3]
        )

        # Then we execute the query. 
        self.__db.update(query)

    # Simple function that will update values into the JOBIDENTIFER table 
    def update_jobidentifier(self, jobidentifier_info):

        # The jobinfo array is so composed: 
        # jobid, date, time, path. 
        # We use those information to use the corrent index to pass into the add column value.
        self.__db.update_column("JOBIDENTIFIER", "DATE", "JOBID", [jobidentifier_info[1], jobidentifier_info[0]])
        self.__db.update_column("JOBIDENTIFIER", "TIME", "JOBID", [jobidentifier_info[2], jobidentifier_info[0]])
        self.__db.update_column("JOBIDENTIFIER", "PATH", "JOBID", [jobidentifier_info[3], jobidentifier_info[0]])

    def generate_docs(self, docs, title):
        # open doc file and define table template
        f = open(docs, "w+")
        f.write(title + "\n")
        table_template = "|{}|{}|\n| :-: | :-:|\n".format(
            "COLUMN", "DESCRIPTION")
        # open database
        conn = sqlite3.connect("gdal/sqlite-autoconf-3400100/FUMI2.db")
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for table in c.fetchall():
            # print table name
            table_name = table[0].upper()
            f.write("### {}\n".format(table_name))
            f.write(table_template)
            # print table columns
            c.execute("SELECT * FROM {};".format(table_name))
            cols = [description[0] for description in c.description]
            for col in cols:
                f.write("| {} | |\n".format(col))
        f.close()
