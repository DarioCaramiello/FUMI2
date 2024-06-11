import os
import time
import subprocess
import threading
import re

from werkzeug.security import safe_join
from shutil import copyfile, copytree, rmtree
from DBManager import DBProxy
from timeit import default_timer as timer
from datetime import date
from ParserManager import Parser, JOBINFO
from datetime import datetime
from SpatialQueryManager import SpatialQueryManager


class SbatchManager():

    scratch_path = None
    storage_path = None
    model_path = None
    root_path = None
    sbatch_file = None
    job_name = None
    db = None

    def __init__(self, scratch_path, storage_path, model_path, root_path, sbatch_file, job_name):
        self.scratch_path = scratch_path
        self.storage_path = storage_path
        self.model_path = model_path
        self.root_path = root_path
        self.sbatch_file = sbatch_file
        self.job_name = job_name
    

    def run(self, user, params=None):
        # print("[*] params : " + str(params))
        script_path = "/home/fumi2/FUMI2"
        scratch_path_container = script_path + "/scratch_user"
        millis = str(int(round(time.time() * 1000)))
        date = datetime.now()
        formatted_date_for_user_dir = date.strftime("%Y%m%dz%H%M%S")
        formatted_date_for_job = str(params[2]) + "Z" + str(params[3]).zfill(2) 

        
        subprocess.run(['mkdir', '{}/tmp_script_lunch'.format(script_path)])
        subprocess.run(['cp', '{}/lunch_remote_job.sh'.format(script_path), '{}/tmp_script_lunch/lunch_remote_job_{}.sh'.format(script_path, millis)])
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "USER", user)
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "DATE", formatted_date_for_user_dir)
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "ID", millis)
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "LON", params[6])
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "LAT", params[7])
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "TEMPERATURE", params[8])
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "DATe", formatted_date_for_job)
        self.substitute("{}/tmp_script_lunch/lunch_remote_job_{}.sh".format(script_path, millis), "HOURS", params[4])
        subprocess.run(['mkdir', '{}/tmp'.format(script_path,)])
        subprocess.run(['mkdir', '{}/tmp/{}'.format(script_path, user)])

        var_millis = millis
        
        with open('tmp/{}/out_from_job_{}_runcmd_{}.txt'.format(user, user, var_millis), 'w') as f:
            subprocess.Popen(
                './tmp_script_lunch/lunch_remote_job_{}.sh'.format(millis),
                stdout=f,
                stderr=f,
                start_new_session=True
            )

        time.sleep(5)
        
        with open('tmp/{}/out_from_job_{}_runcmd_{}.txt'.format(user, user, var_millis), 'r') as f:
            file_tmp = f.read()
            
        line_match = re.search(r'.*Workflow registration success id = \w+.*', file_tmp)
        if line_match:
            line = line_match.group(0)
            id_match = re.search(r'id = (\w+)', line)
            if id_match:
                id_value = id_match.group(1)
                print(f'[*] ID estratto: {id_value}', flush=True)
                
                subprocess.run(['rm', 'tmp/{}/out_from_job_{}_runcmd_{}.txt'.format(user, user, var_millis)])
                return id_value
        else:
            print('[*] ID non trovato nel file.', flush=True)
            return None
        
        # subprocess.run(['nohup', './lunch_remote_job.sh', '>', 'tmp/out_from_job_{}_runcmd.txt'.format(user), '2>&1', '&'])
        #subprocess.run(['./lunch_remote_job.sh', '>', 'tmp/out_from_job_{}_runcmd.txt'.format(user), '2>&1', '&'], shell=True)

        # print("[*] Out DagOn Request : " + str(dagonManager.get_request()), flush=True)
        
        # user_dir =  self.tmpgen(user,params)
        # if user_dir:
            # return user_dir
            # thread che effettua delle continue richieste al container dagon per capire lo stato
            # t1 = threadinclearg.Thread(target=self.check_outputs, args=(tmp_path, dest_path, user, jobid))
            # t1.start()
            #t2 = threading.Thread(target=self.check_progress, args=(tmp_path, jobid))
            #t2.start()
        # We check if jobid is equal to 0 (job not submitted)
        # or to error codes: -1 date error, -2 download error        
        # if jobid == 0 or jobid == -1 or jobid == -2:
            # In this case, we simply return since we can't do anything else
        #    return jobid
        # With the result given, create a folder into the storage path
        # to store the script output
        #dest_path = self.outgen(user, jobid, tmp_path)
        # We then start the thread waiting for the script output
        # to be completed after creating the output folder, we almost start istantly
        # a thread that will check when the output of the scripts are finished.
        # So we can continue our execution in the code
        #t1 = threading.Thread(target=self.check_outputs, args=(tmp_path, dest_path, user, jobid))
        #t1.start()
        # We also create another thread to keep track of the progress of the script.
        # This will be needed for the progress bar to fill up
        #t2 = threading.Thread(target=self.check_progress, args=(tmp_path, jobid))
        #t2.start()
        # After that, we return the ID of the submitted job to be handled
        # in other modules (such as the DB one)
        #return jobid
    

    # Function that given an id (composed by the millis) will build a directory
    # in which all the middle operations of the root script will be performed.
    def tmpgen(self, user, params=None):

        script_path = "/home/fumi2/FUMI2"
        scratch_path_container = script_path + "/scratch_user"
        # Obtaining the key id of the folder by taking the millis
        millis = str(int(round(time.time() * 1000)))
        # uniqueid = "{}-{}".format(millis, self.job_name) + "/"
        date = datetime.now()
        formatted_date_for_user_dir = date.strftime("%Y%m%dz%H%M%S")
        formatted_date_for_job = str(params[2]) + "Z" + str(params[3]).zfill(2)  
        subprocess.run(['cp', '{}/lunch_remote_job.sh'.format(script_path), '{}/lunch_remote_job_var.sh'.format(script_path)])
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "USER", user)
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "DATE", formatted_date_for_user_dir)
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "ID", millis)
        
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "LON", params[5])
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "LAT", params[6])
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "TEMPERATURE", params[7])
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "DATe", formatted_date_for_job)
        self.substitute("{}/lunch_remote_job.sh".format(script_path), "HOURS", params[4])

        # questo lo devo eseguire in background 
        # subprocess.run("./tmpgen_runjob.sh", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # subprocess.run("./lunch_remote_job.sh")
        # per testare in locale decommentare la riga successiva 
        # return user + "-" + formatted_date_for_user_dir + "-" + millis

        '''
        if os.path.isdir(script_path + "/static/KML/" + user + "-" + formatted_date_for_user_dir + "-" + millis + "-out"):
            # print("[*] [check dir scratch user] : found", flush=True)
            # print("[*] [len file in dir] : " + str(len(os.listdir(script_path + "/static/KML/" + user + "-" + formatted_date_for_user_dir + "-" + millis + "-out/out_job"))))
            # print("[*] [durata sim.] : " + str(int(params[4])))

            if len(os.listdir(script_path + "/static/KML/" + user + "-" + formatted_date_for_user_dir + "-" + millis + "-out/out_job")) == int(params[4]):
                print("[*] [check job out] : correct number of outs ", flush=True)
                return user + "-" + formatted_date_for_user_dir + "-" + millis 
            else:
                print("------ [check job out] : incorrect number of outs", flush=True)
                return False
        else:
            print("----- [check dir scratch user] : not found", flush=True)
            return False
        '''

        # -- test spatial query con un punto 
        result_query_point = postgresql_query_handler.spatial_query_point(14.2681, 40.8518)

        print("[*] point spatial query : ")
        for i in result_query_point:
            print("Common : " + str(i))
        

        # -- test spatial query con un bounding box 
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

        postgresql_query_handler = SpatialQueryManager()

        result_query_box = postgresql_query_handler.spazial_query_box(port_of_naples_bbox)
        print("[*] box spatial query - port of naples: ", flush=True)
        for i in result_query_box:
            print("Common : " + str(i[1]), flush=True)

        print("[----------------------------------------------]")

        result_query_box2 = postgresql_query_handler.spazial_query_box(campania_bbox)
        print("[*] box spatial query - campania :", flush=True)
        for i in result_query_box2:
            print("Common : " + str(i[1]), flush=True)

        # -- test spatial query con un bounding box letto da un file .kml 
        # result_linestring = read_polygon_from_kml('/mydata.kml')
        # print(result_linestring)
        # print(str(type(result_linestring)))

        # query_result = postgresql_query_handler.spazial_query_box(result_linestring[-1])

        # for i in query_result:
        #    print("Common : " + str(i[1]))
        
        
             
        # We first create the path for the enviroinment used to store the middle steps of our
        # script
        # tmp_shortpath = safe_join(self.scratch_path, "{}/tmp".format(self.job_name))
        # tmp_finalpath = safe_join(tmp_shortpath, uniqueid)

        # tmp_shortpath = safe_join(self.scratch_path, "tmp/")
        # tmp_finalpath = safe_join(tmp_shortpath, uniqueid)

        # tmp_shortpath = self.scratch_path + "tmp/"
        # tmp_finalpath = tmp_shortpath + uniqueid
        # After created an unique folder representing this job, we create the path 
        # associated to the template sbatch file
        # print("---- tmp_shortpath : " + str(tmp_shortpath), flush=True)
        # print("-------------- scratch_path : " + str(self.scratch_path), flush=True)
        # print("-------------- job_name : " + str("{}/tmp".format(self.job_name)), flush=True)
        # print("---- tmp_finalpath : " + str(tmp_finalpath), flush=True)
        # print("-------------- tmp_shortpath : " + str(tmp_shortpath))
        # print("-------------- uniqueid : " + str(uniqueid))

        # source_filepath = safe_join(self.root_path, self.sbatch_file)
        # source_filepath = "/dati_prova/template.sbatch"
        # dest_path = safe_join(tmp_finalpath, self.sbatch_file)

        # source_filepath = self.root_path + self.sbatch_file
        # dest_path = tmp_finalpath + self.sbatch_file

        # print("---- source_filepath : " + str(source_filepath), flush=True)
        # print("-------------- root_path : " + str(self.root_path), flush=True)
        # print("-------------- sbatch_file : " + str(self.sbatch_file), flush=True)
        # print("---- dest_path : " + str(dest_path), flush=True)
        # print("---- tmp_final_path : " + str(tmp_finalpath), flush=True)
        # print("-------------- sbatch_file : " + str(self.sbatch_file), flush=True)

        # Creating the data folder string
        # tmp_finalpath_data = safe_join(tmp_finalpath, "data")

        # tmp_finalpath_data = tmp_finalpath + "data"
        # print("---- tmp_finalpath_data : " + str(tmp_finalpath_data), flush=True)

        # After creating the appropriate scratch and template path, we copy the entire
        # content of the model directory inside the freshly created scratch one.
        # We need to run the model separately for each user request and for each user aswell;
        # Thats because each user should independentely be able to run a job avoiding write conflicts.
        # NOTE: we do not create the folder because copytree will make that by itself.
        ##------------------------------------------------------------------------------------
        ## devo implementare una funzione che copia la cartella /model_template sul frontend
        ## nella cartella /scratch/d.caramiello/tmp/id-unico-fumi2/ [ che verrà creata al momento 
        ## copia ]
        ## fa partire uno script che muove la cartella model_template [ in locale sul frontend ] nella 
        ## cartella tmp_finalpath 
        # print("---- model_path : " + self.model_path, flush=True)
        # print("---- tmp_finalpath : " + tmp_finalpath, flush=True)
        # copytree(self.model_path, tmp_finalpath)
        ## ------------------------------------------------------------------------------------

        # print("---- copytree () ", flush=True)
        # print("-------------- model_path : " + str(self.model_path), flush=True)
        # print("-------------- tmp_finalpath : " + str(tmp_finalpath), flush=True)

        # print("---- copyfile () ", flush=True)
        # print("-------------- source_filepath : " + str(source_filepath), flush=True)
        # print("-------------- dest_path : " + str(dest_path), flush=True)
        # We then copy the sbatch template

        ## ------------------------------------------------------------------------------------
        ## fa partire unos script che copia il file template.sbatch nella cartella dest_path
        # print("---- source_filepath : " + source_filepath, flush=True)
        # print("---- dest_path : " + dest_path, flush=True)
        # copyfile(source_filepath, dest_path)
        ## ------------------------------------------------------------------------------------

        # subprocess.run(['cp', '/home/fumi2/FUMI2/pipeline_env/template.sbatch', '/home/fumi2/FUMI2/pipeline_env/template-tmp.sbatch'], check=True)

        # After copying the file, we substitute the templates inside the file
        # self.substitute(dest_path, "TMPPATH", tmp_finalpath)
        
        #self.substitute("/home/fumi2/FUMI2/pipeline_env/template-tmp.sbatch", "TMPPATH", tmp_finalpath)

        # We copy the args to be run in the python script
        # self.substitute(dest_path, "ARGS", "{} {} {} {}".format(params[-1], params[3], params[4], "data/"))
        
        # self.substitute("/home/fumi2/FUMI2/pipeline_env/template-tmp.sbatch", "ARGS", "{} {} {} {}".format(params[-1], params[3], params[4], "data/"))

        # We substitute the date for the output nc file 
        # self.substitute(dest_path, "TMPDATE", params[2])
        
        # self.substitute("/home/fumi2/FUMI2/pipeline_env/template-tmp.sbatch", "TMPDATE", params[2])

        # We substitute the last param (data) with the data/output.nc filename
        
        # params[-1] = "data/" + "wrfout_d03_{}Z00.nc".format(params[2])

        # Then subsitute the necessary params building the command string
        
        # command = self.build(params)
        
        # print(command, flush=True)
        # self.substitute(dest_path, "TMPCMD", command)
        
        # self.substitute("/home/fumi2/FUMI2/pipeline_env/template-tmp.sbatch", "TMPCMD", command)

        # self.substitute("/home/fumi2/FUMI2/script_tmpgen.sh", "unique-tmp-id", uniqueid)

        # subprocess.run("./home/fumi2/FUMI2/script_tmpgen.sh")

        # Then running the command
        #result, jobid = self.execute_cmd(dest_path)


        # If jobid is equal to 0, we couldnt submit the job: we delete the directory 
        # just created 
        # if jobid == 0:
            # rmtree(tmp_finalpath)
        
        # jobid = 0 # to delete, only for test

        # RETURN THE ID OF THE SUBMITTED JOB AND RETURN IT
        # return jobid, tmp_finalpath
        # return jobid
    ## --------------------------------------------------

    # Function that given the user id of the performer of the job, will create
    # an apposite folder where to store the actual result of the script
    def outgen(self, userid, jobid, tmp_path):

        # Generate the path with the given storage root and the folder id create
        # an appropriate folder
        middle_path = safe_join(self.storage_path, self.job_name)
        user_path = safe_join(middle_path, userid)

        # After joining the user with the storage path`, we then create the unique
        # folder that represent the jobid folder. Note that, assure folder
        # will create all the intermediary folders necessary if not existent.
        dest_path = safe_join(user_path, str(jobid))

        # Returning the storage destination path to be used by the thread
        return dest_path

    # Simple function that, given a list of parameter, will build a string containing the 
    # command to be executed
    def build(self, params):
        return " ".join(params)
        
    # Simple function that assure if a given path exists or not
    def assure_folder(self, jobid):

        # If the folder do not exists create one, else just return
        if not os.path.isdir(jobid):
            os.makedirs(safe_join(jobid))

    def substitute(self, filepath, tmp, sub):

        # Opening our text file in read only
        # mode using the open() function
        with open(filepath, 'r') as file:

            # Reading the content of the file
            # using the read() function and storing
            # them in a new variable
            data = file.read()

            # Searching and replacing the text
            # using the replace() function
            data = data.replace(tmp, sub)

        # Opening our text file in write only
        # mode to write the replaced content
        with open(filepath, 'w') as file:

            # Writing the replaced data in our
            # text file
            file.write(data)

    def check_outputs(self, scratch_path, storage_path, user, jobid):

        # Istanciate a db object to perform queries
        db = DBProxy()

        # First we check if an entry in jobs with our jobid is present to avoid 
        # unrespected constraint on the key (the JOBS entry should be created first by 
        # the request manager with his request when submitting a new job)
        job_inserted = False
        while not job_inserted:
            
            # We fetch the column containing the jobid
            result = db.specific_select("JOBS", "JOBID", "JOBID", jobid)

            # If the result exists, we update the job inserted bolean so we can procoeed
            if result is not None:
                job_inserted = True
            else:
                # else sleep a little
                time.sleep(100/1000)

        # First, we start inserting a new tuple into JOBIDENTIFIER composed only 
        # by the JOBID and the PATH, initially being the scratch_path. 
        db.specific_insert("JOBIDENTIFIER", "JOBID, PATH", "{},'{}'".format(jobid, scratch_path))

        # We then create a new date and format it 
        today = date.today()
        d = today.strftime("%d-%m-%Y")

        # Simple thread function that check for the existence of a given file.
        # Since we do not now the computation time needed, we do sleep 0.1msec
        # in a loop until the file has been found; after that, we copy the content
        # of the scratch folder into the output.
        # We also init a timer to check time needed by the script
        start = timer()
        file_created = False
        job_ok_exists = False
        job_error_exists = False
        job_cancelled_exists = False
        while not file_created:

            # Getting states with exists passing as input the path
            job_ok_exists = os.path.exists(safe_join(scratch_path, "JOB_OK"))
            job_error_exists = os.path.exists(safe_join(scratch_path, "JOB_ERROR"))
            job_cancelled_exists = os.path.exists(safe_join(scratch_path, "JOB_CANCELLED"))

            # If the file exists, break the cycle else sleep a little
            if job_ok_exists or job_error_exists or job_cancelled_exists:
                file_created=True 
            else: 
                time.sleep(100/1000)

        # Getting endtime
        end = timer()

        # Check if the error file has been created:
        if job_error_exists or job_cancelled_exists:

            
            # Based on the type of error, we do copy and insert into the db differen things.
            error_prefix = "ERR_" if job_error_exists else "CANC_"
            file_prefix = "JOB_ERROR" if job_error_exists else "JOB_CANCELLED"
            error_type = 2 if job_error_exists else 3

            print("---------- thread error")
            print(error_type)
            print(file_prefix)
            print(error_prefix)
            print("----------")

            # We create a new error outpath
            err_path = storage_path.split('/')
            err_path[4] = "{}".format(error_prefix)+err_path[4]
            err_path = '/'.join(err_path)
            os.makedirs(err_path)

            # And after that, we copy the .out and .err to the out folder alongside the template sbatch
            # For debug purposes (also the JOB_ERROR file, containing the error line)
            copyfile(safe_join(scratch_path, "fumi2.out"), safe_join(err_path, "fumi2.out"))
            copyfile(safe_join(scratch_path, "fumi2.err"), safe_join(err_path, "fumi2.err"))
            copyfile(safe_join(scratch_path, "template.sbatch"), safe_join(err_path, "template.sbatch"))
            copyfile(safe_join(scratch_path, file_prefix), safe_join(err_path, file_prefix))

            # We then remove the scratch path alongside all its content
            #rmtree(scratch_path)

            # LASTLY, after all has been done:
            # If the error file has been created, we need to update the entry to the database corresponding
            # to the job, updating the completed state with 2 (error code). 
            db.update_column("JOBINFO", "COMPLETED", "JOBID", [error_type, jobid])

            # Then we update the jobidentifer entry, omitting the time. To creat an appropriate folder path 
            # for the relative job, we must do something like "ERR_<jobid>". 
            user_job = safe_join(user, "{}".format(error_prefix)+str(jobid))
            db.update_jobidentifier([jobid, d, str(0), user_job])

            # Returning and exiting the thread
            return

        # If no error, we began to copy the output file we need from the folder: .shp, kml, dbf and shx.
        # To achieve the namefile, we perform a simple listdir on the folder filtering
        # the filee we need. 
        extensions = ["shp", "kml", "dbf", "shx"]
        files = []

        # List the files in the WWW folder of the scratch path 
        # #(WWW is the output folder of the script)
        for file in os.listdir(safe_join(scratch_path, "WWW")): 

            # Split the file by the point extracting the extension 
            extension = file.split('.')[1]

            # Check if the extension is valid 
            if extension in extensions:

                # add the file to the file array 
                files.append(file)
            
        # Now we make an output dir: with makedirs we create intermediate path aswell (storage_path)
        out_dir = safe_join(storage_path, "out")
        os.makedirs(out_dir)

        # We first copy the .out and .err to the out folder alongside the template sbatch
        copyfile(safe_join(scratch_path, "fumi2.out"), safe_join(storage_path, "fumi2.out"))
        copyfile(safe_join(scratch_path, "fumi2.err"), safe_join(storage_path, "fumi2.err"))
        copyfile(safe_join(scratch_path, "template.sbatch"), safe_join(storage_path, "template.sbatch"))

        # And then we copy the selected file inside it
        for file in files:
            copyfile(safe_join(safe_join(scratch_path, "WWW"), file), safe_join(out_dir, file))

        # Then we update the entry in the database for that user and that jobid 
        # that the job has been completed
        db.set_complete(jobid)

        # Then we pass the arguments to create a new job identifier tuple:
        # jobid/date/total time in seconds/storage path
        # We create a new path composed by username/jobid/out:
        user_job = safe_join(user, jobid) 
        final_storage = safe_join(user_job, "out")                            
        db.update_jobidentifier([jobid, d, str(int(end - start)), final_storage])

        # We then remove the scratch path alongside all its content
        #rmtree(scratch_path)

    def check_progress(self, scratch_path, jobid): 

        # Declaring variables
        # step is used to understand at which step in the list we currently are
        step = 0

        # steps represent the total possible step in the script, with .kml being the end 
        steps = ["IN TERREL", "IN CTGPROC", "IN MAKEGEO", "IN CALWRF", "IN CALMET", "IN CALPUFF", "IN CALPOST", "IN WWW", ".kml"]

        # We init a parser object
        parser = Parser()
        
        # boolean for stopping the while and for checking errors
        done = False
        error = False
        cancelled = False
        error_line = ""

        # Get today date
        today = date.today()
        d = today.strftime("%d-%m-%Y")

        # We create a progress directory inside the scratch folder 
        progress_dir = safe_join(scratch_path, "progress")
        print(progress_dir)
        os.makedirs(progress_dir)

        # Wait for the file to be created
        while(os.path.exists(safe_join(scratch_path, "fumi2.out")) == False):

            # sleeping 0.1msec wile output isn´t ready yet
            time.sleep(100/1000)

        # Now open the file.
        # With open that file to catch eventual errors
        with open(safe_join(scratch_path, "fumi2.out"), "r") as f:    

            # While the end has not been reached
            while not done:
        
                # Read a line
                line = f.readline()

                # If there is no line (file hasn't been written yet)
                if not line:

                    # When waking up from the sleep while there are no new lines, we want to check
                    # if the job we're currently waiting for has been CANCELLED. 
                    # This means that the job has been cancelled for some reason from the squeue.
                    # We check that using the parser to return the squeue as dictionary, and check 
                    # if our jobid is still in:
                    if str(jobid) not in parser.dictionarize("squeue"):

                        # We open the error file and read the last line 
                        with open(safe_join(scratch_path, "fumi2.err"), "r") as e:
                            
                            # We read the entire file 
                            errorfile = e.readlines()

                            # If the last line contains the keyword for which a job has been cancelled:
                            if errorfile[-1].find("slurmstepd") != -1 and errorfile[-1].find("CANCELLED") != -1:
                                
                                # If here that means the job isn't on anymore, while we're waiting still on 
                                # some step to finish (file hasn't reached the end yet). In addition to that, 
                                # the error file reported that the job has been cancelled, so we set cancelled to true.
                                done = True
                                cancelled = True
                                error_line = errorfile[-1]

                            else: 
                                
                                # Else, the jobid isn't on the queue anymore but the error isnt a cancellation.
                                # So we continue skip to the next iteration and read the next lines; that could 
                                # happen since the jobid can be cancelled before we fetch the output lines of the 
                                # out file.
                                continue
                            
                    else:

                        # We cycle a little and skip iteration
                        time.sleep(100/1000)
                        continue

                else:

                    # The first thing we do, is check if there are any errors in the line. 
                    # That's because the model scripts output an error line whenever it encounters
                    # one. If so, we just break the cycle and exit, assigning true to error.
                    # The errors here are ERROR (error in one of the phase of the script)
                    # and Usage (script called incorrectly).
                    if line.find("ERROR") != -1 or line.find("Usage") != -1:
                        done = True
                        error = True
                        error_line = line


                    # We could add if line contains download finished we change the state to 0

                    # else, the end hasn't been reached and we got no error:, we need to check what's the content.
                    # check what's the content. Basically we want to check at which step we're in: to do so,
                    # we check if in the current line is contained one of the steps in the steps list:
                    # To do so we use the find function on the line, positioned at the current 
                    # step (step variable) that we need to find.
                    elif line.find(steps[step]) != -1:

                        print("At step: {} - {}".format(step, line))

                        # We create a new file named as the step we're in: 
                        # Since we do have 9 different steps in our step list, and we do start at 0, that means 
                        # in the range 0-7 we need to check the first 8 elements and in the 8th step, we need to 
                        # check the last. Since the last step does not contain a space like the rest of them does, 
                        # we need to split the logic.
                        # If we're not at the last step (.kml in the step list does not have spaces to split)
                        filename = ""
                        if step < 8:

                            # Assign to filename the current element at step in the steps list 
                            # and split it by spaces, assigning the second occurrence (i.e: IN CALMET -> CALMET)
                            filename = safe_join(progress_dir, steps[step].split(" ")[1])

                        elif step == 8: 
                            # Else assign a static name 
                            filename = safe_join(progress_dir, "KMLOUT")
                        
                        # Now create a file and write into it the name of the file (TERREL, CTGPROC)
                        # currently analized followed by ok; that means we're at that step
                        with open(filename, 'w') as file:
                            file.write('{} OK'.format(filename))

                        # If the line contains the .kml token that means that an output has been produced.
                        # We set done to true and exit
                        if line.find(".kml") != -1:
                            done = True

                        # If the current step in the line, we update the step variable to +1
                        # (going to the next element of the list)
                        step += 1
                        
        # Before writing the file, we need to check the error file again to find is some allocation
        # Problems has been found
        done = False 
        xrealloc = False
        error_line = ""

        # We open the error file and read the last line 
        with open(safe_join(scratch_path, "fumi2.err"), "r") as e:
            
            while(not done):

                # We read the entire file 
                errorfile = e.readline()
                
                # If the line is the end of file, break
                if len(errorfile) == 0:
                    done = True
                    break

                # If xrealloc happened
                if errorfile.find("xrealloc") != -1:
                    
                    # MEMORY ALLOCATION PROBLEM
                    done = True
                    xrealloc = True
                    error_line = errorfile

        # Now, after the cycle, we want to control two things: 
        # If we're done because the progress is finished or because we did encounter an error:
        # If we got no error, we write a JOB_OK file. If not, we write a JOB_ERROR file, 
        # Writing the error line in it. 
        # If we completed with no error
        if done and not error and not cancelled:
    
            # Create a file within the scratch path
            # and write date + status inside 
            filename = safe_join(scratch_path, "JOB_OK")
            with open(filename, 'w') as file:
                file.write('{}: OK'.format(d))

        # Else: completed with error
        elif done and error: 

            # Create a file within the scratch path
            # and write date + error inside 
            filename = safe_join(scratch_path, "JOB_ERROR")
            with open(filename, 'w') as file:
                file.write('{}: {}'.format(d, error_line))

        elif done and xrealloc: 
            
            # Create a file within the scratch path
            # and write date + error inside 
            filename = safe_join(scratch_path, "JOB_ERROR")
            with open(filename, 'w') as file:
                file.write('{}: {}'.format(d, error_line))

        # Else: canceled for some reason 
        elif done and cancelled: 

            # Create a file within the scratch path
            # and write date + error inside 
            filename = safe_join(scratch_path, "JOB_CANCELLED")
            with open(filename, 'w') as file:
                file.write('{}: {}'.format(d, error_line))

    # Simple function that given a jobid, will cancel it from the queue
    def cancel_job(self, jobid):

        # Cancel it
        subprocess.run(["scancel", jobid])

        # We do also check if the process 

    # Simple function that given a shell command will execute it
    def execute_cmd(self, filepath, stdin=None, stdout=None, stderr=None, close_fds=True):

        ## qui devo far partire lo script .scipt_ssh_webserv.sh


        # We build a list containing as the first argument the command
        # sbatch, and as second the filepath.
        cmdlist = [filepath]
        cmdlist.insert(0, "sbatch")

        # Open a process with the desired command parameters. Note that,
        # by default, the managere does not wait for the job to finish, it just
        # launches it and return the job id created.
        result = ''
        jobid = None

        print("-------- execute_cmd () ", flush=True)
        print("cmdlist : " + str(cmdlist), flush=True)

        try:

            # Getting the output of the command through check output`
            jobid = subprocess.check_output(cmdlist)

            # Extracting the job id from the string
            jobid = str(jobid).split(' ')[-1].split('\\')[0]

            # Result is OK
            result = 'OK'

        except Exception as e:

            jobid = 0;
            result = "NOT OK: {}".format(e)

        # Return a string containing the result of the operation.
        return result, jobid

    def read_polygon_from_kml(name_file):
        namespace = {"ns": nsmap[None]}
        coordinates_list_out = []
        coordinates_list_out2 = []

        with open(name_file) as f:
            root = parser.parse(f).getroot()
            pms = root.xpath(".//ns:Placemark[.//ns:LineString]",   namespaces=namespace)

            for pm in pms:

                string_coordinates = pm.LineString.coordinates

                '''
                print("[*] LineString ------------------------- ")
                print(string_coordinates)
                print("[*] LineString ------------------------- ")
                '''

                coordinates_list = str(string_coordinates).split()
                # Itera attraverso le coppie di coordinate e aggiungi all'array
                for coordinate_pair in coordinates_list:
                    lon, lat = coordinate_pair.split(',')
                    coordinates_list_out.append([float(lon), float(lat)])

                coordinates_list_out2.append(coordinates_list_out)
                # print("Array di coordinate:")
                # print(coordinates_array)
        return coordinates_list_out2