### Module Import 
from flask import Flask, render_template, request, url_for, session, make_response, flash, jsonify, redirect
#from werkzeug.security import safe_join, safe_str_cmp, generate_password_hash
from werkzeug.security import safe_join, generate_password_hash
from flask_paginate import Pagination
from flask_mail import Mail, Message
from shutil import copyfile, rmtree
from dotenv import load_dotenv
from datetime import datetime
# from DBManager import DBProxy
from threading import Lock
import secrets
import zipfile
import base64
import uuid
import re 
import os
import hmac
import requests
import random

# Custom Import
from DBManager import DBProxy, DBManager
from SbatchManager import SbatchManager
from NcDumper import NCODump
from ParserManager import Parser
from DagonOnServiceManager import DagonOnServiceManager
# from ComuniManager import ComuniManager


##############
##  INIT   ##
#############

# Load environment variables from .env file
load_dotenv(dotenv_path='/home/fumi2/FUMI2/secrets/secrets.env')

### APP AND OBJECTS
app = Flask(__name__)
sbatchmanager = SbatchManager(os.getenv('SCRATCH_PATH'), 
                              os.getenv('STORAGE_PATH'), 
                              os.getenv('MODEL_TEMPLATE_PATH'), 
                              os.getenv('ROOT_PATH'), 
                              os.getenv('SBATCH_TEMPLATE'), 
                              os.getenv('PROJECT_NAME'))
port = os.getenv('PROJECT_PORT')

queue_lock = Lock()
parser = Parser()
ncdump = NCODump()

### Configuring SMTP data and info to send mails
app.config['MAIL_SERVER']= os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
#app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)
mail = Mail(app)

##############
## HELPERS ##
#############

# Simple function used to redirect an user to the correct page
def redirect_to_dashboard(user):

    # Istanciate a db object to perform queries
    db = DBProxy()

    # If we're logging in, we redirect to adminpane/dashboard based on  
    # The user privilege
    if db.is_admin(user):
        # We redirect to adminpane
        return redirect(url_for('adminpane'))
    else: 
        return redirect(url_for('dashboard'))

# Simple function that validates an user string containing a regular expression
def validate_string(string, pattern="[a-zA-Z0-9._]"):
    """
    This function takes a string and uses a regular expression pattern to validate its format.
    """
    # Define the regular expression pattern for a username
    pattern = rf"^{pattern}+$"
    
    # Use the match() method to check if the username matches the pattern
    if re.match(pattern, string) is not None:
        return True
    else:
        return False

def validate_password(string, pattern="^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$"):
    """
    This function takes a password as a string and uses a regular expression pattern to validate its format.
    """

    # Use the match() method to check if the username matches the pattern
    if re.match(pattern, string) is not None: 
        return True
    else: 
        return False

# Simple function that will generate an unique link for the registration/password form 
# given an username 
def generate_unique_link(username, route):

    # We first generate an unique link and an encoded user
    unique_id = str(uuid.uuid4().hex[:11])
    encoded_name = base64.b64encode(username.encode('utf-8')).decode('utf-8')
    split = base64.b64encode("split".encode('utf-8')).decode('utf-8')

    #TODO: fare il link dinamico con url for
    link = f"{os.getenv('PROJECT_DOMAIN')}/{route}/{encoded_name}{split}{unique_id}"

    # we return the link
    return link

# Simple function that given a search filter and a list to filt, will return a
# list containing only the filtered values 
def filters(search_filter, searchlist):

    # Initiate an empty list
    filter_list = []

    # For each row
    for row in searchlist:
        
        # Substitute None with an empty string 
        row = ['None' if item == None else str(item) for item in row]

        # Flattenize as string 
        query = ' '.join(row).lower()

        # Search key in token: if present, we have a match
        if search_filter in query: filter_list.append(row)

    # return the filtered list 
    return filter_list

# Simple function that returns a job queue based on an username
def get_slurm_queue(user): 

    squeue_list = parser.dictionarize("squeue")
    jobs = {}
    for key in squeue_list: 
        if safe_str_cmp(squeue_list[key]["USER"], user):
            jobs[key] = squeue_list[key]["ST"]
    return jobs

# Simple function that assert if a folder exists before deleting it, to 
# avoid errors
def safe_rmdir(dirname): 

    # We check for exsistence
    if os.path.exists(dirname) and os.path.isdir(dirname):
                        
        # Remove if exists
        rmtree(dirname)
    
# Simple function that copy the content of a KML file from a storage folder to the serve 
# folder in the static one.
def serve_kml(jobid, db):

    # Istanciate a db object to perform queries
    db = DBProxy()

    # Using that id, we'll query the database to retrieve the storage path in 
    # which the KML file is containeed, without specifying the root; only the storage
    # is returned.
    kml_path = db.get_KML_path(jobid)

    # Check if a file do not exists in the static folder: 
    if not os.path.exists(safe_join('static', kml_path)):
        
        # If so, we need to create a file:
        # Since the storage path is different than the static one, we need to serve 
        # the file in the static folder. We simply copy the file into a similar 
        # tree structure
        static_serve_path = safe_join('static', os.path.dirname(kml_path))
        os.makedirs(static_serve_path, exist_ok=True)

        # We then copy the file inside it, ready to be served
        copyfile(safe_join('root', kml_path), safe_join('static', kml_path))
    
    # return the path 
    return kml_path

# Simple function that will check if a given key is in the session dictionary. 
# If it is, it returns lvalue, if not it returns rvalue.
def check_session(key, condition, lvalue, rvalue):

    # If the key is in the session
    if key in session:

        # If additional condition (specified by the user, i.e: lenght of session['jobid'] > 0)
        if condition:   

            # We return the left value
            return lvalue
        
        else: 

            # Else, we return the other
            return rvalue

# Simple function that check a folder containing files to update the progress bar 
# in the dashboard.
def get_progress():

    # Istanciate a db object to perform queries
    db = DBProxy()

    # Before anything, we need to store into a session var the number of files currently 
    # fetched if not present. We check it 
    if "numfiles" not in session: 

        # And if not in session, we assing 0 (starting progress)
        session["numfiles"] = 0

    # First: we check if a scatch directory has been created given the submitted jobid
    # To do so, we check in the session storage.
    # Bascially what we want to do is assign a path from the session if already created, 
    # fetch one if not.
    scratch_path = ""
    
    if session["jobstate_interactive"][0][2] != "":
        scratch_path = session["jobstate_interactive"][0][2]
    else: 
        scratch_path = db.specific_select("JOBIDENTIFIER", "PATH", "JOBID", session["jobstate_interactive"][0][0])
        session["jobstate_interactive"][0][2] = scratch_path

    print("Scratch path is: {}".format(scratch_path))

    # Before proceding, we check if the job has been completed with an error
    state = db.specific_select("JOBINFO", "COMPLETED", "JOBID",session["jobstate_interactive"][0][0])

    # If there is an error (code 2 or 3) we return the 100% to indicate that the job has been 
    # finished.
    print("state is {}".format(state))
    if state == 2 or state == 3:
        return [10 / 10.0 * 100, "", state]

    # If scratch path has been defined
    if scratch_path is not None:

        # Then we check if the progress bar has been created
        if (os.path.exists(safe_join(scratch_path, "progress"))):
            
            # We fetch the names of files in the progress folder
            files = os.listdir(safe_join(scratch_path, "progress"))

            # We fetch the num files in the progress folder
            num_files = min(len(files), 10)

            # Then we store it into the session vars
            session["numfiles"] = num_files

            print("Num files are: {}".format(num_files))

            # If the num files are equal 9 (the maximum creable files in the progress folder) 
            if num_files == 9:

                # We check if the job has been completed 
                completed = db.specific_select("JOBINFO", "COMPLETED", "JOBID", session["jobstate_interactive"][0][0])

                print("Is completed?: {}".format(completed))

                # If the job has been completed 
                if completed == 1: 
                    
                    # We serve the kml file into the static path and retrieve it
                    kml_path = serve_kml(session["jobstate_interactive"][0][0], db)

                    print("KML PATH: {}".format(kml_path))

                    # Increase by one the num_files: we have finished 
                    num_files += 1

                    # We then pass the stored kml path in the return function 
                    return [num_files / 10.0 * 100, kml_path, completed]

    # Else, we simply return the current files with a dummy empty kml file
    return [session["numfiles"] / 10.0 * 100, "", -1]
        

#############
## WEBSITE ##
#############

# @app.route('/test-comuni', methods=['POST', 'GET'])
# def test_comuni():
#     print(str(comuni_manager.SearchDataRange(40.8, 41.5, 13.7, 15.1)), flush=True)

@app.route('/', methods=['POST', 'GET'])
def login():

    # If the user is alrady authenticated, we redirect it to the appropriate 
    # dashboard using the flask_login module functionalities, based on his role.
    if "user" in session:   
        return redirect_to_dashboard(session["user"])


    # If we press the login button 
    if request.method == "POST":

        # Istanciate a db object to perform queries
        db = DBProxy()

        # Get user and password
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if present on the DB and is active
        exists = db.user_exists(username, password)
        is_active = db.user_active(username)

        # If the user does exists, redirect us to the appropriate dashboard
        if exists:
            
            if is_active:

                # We update the session values
                session["user"] = username
                # session["jobinfo_interactive"] = []
                session["jobinfo_queue"] = []
                # session["jobstate_interactive"] = []
                # session["kmlpath_dash"] = ""
                # session["searchval"] = ""
                # session["category"] = ""
                # session["queue_ops_in_act"] = False

                db.update_access(session["user"])
                session["access"] = db.get_last_access(session["user"])

                return redirect_to_dashboard(session["user"])
        
            
            else:
                
                # If the user is not active, we redirect to login flashing the message
                # Else, username or password not correct: flash a message and redirect to login
                flash("Utente non attivo. Richiederne l'attivazione!")
                return redirect(url_for('login'))

        else:
            
            # Else, username or password not correct: flash a message and redirect to login
            flash("Username o Password non corrette.")
            return redirect(url_for('login'))


    # Assign the redirectionn to the template login
    return render_template('login.html')

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    
    # Redirect to login if user not in session
    if "user" not in session:
        return redirect(url_for('login'))
    
    # Istanciate a db object to perform queries
    db = DBProxy()

    # If the user is an admin trying to accessing the other routes pages, redirect him
    # to the adminpane
    if db.is_admin(session["user"]):
        return redirect(url_for('adminpane'))

    # Fetch username and last access
    user = session["user"]

    # Fetch last access knowing the user
    last_access= session["access"]

    # Rendering with those info 
    return render_template("dashboard.html", user=user, last_access=last_access)

# @app.route('/interattivo', methods=['POST', 'GET'])
@app.route('/simulazione-singola', methods=['POST', 'GET'])
def simulazione_singola():

    db = DBProxy()

    if "user" not in session:
        return redirect(url_for('login'))

    if db.is_admin(session["user"]):
        return redirect(url_for('adminpane'))

    # Assign values to jobstate (interactive): if present, we assign that very array, empty if not 
    # session["jobstate_interactive"] = check_session("jobstate_interactive", len(session["jobstate_interactive"])>0, session["jobstate_interactive"], [])

    # INFO STR says info about which job is being executed. Obviously, null
    # at start if no jobid is currently active, the current jobid else.
    # We need to check if the len is major than 0 first because we'll access the first element 
    # causing an error if not.
    # info_str = " "
    # if len(session["jobstate_interactive"]) > 0:
    #    info_str = check_session("jobstate_interactive", True, "ID: {}".format(session["jobstate_interactive"][0][0]), " ")
    
    # The update value is passed inside an hidden input and later checked by a JS function: 
    # If the value is true, we must call the update function to update the progress bar (a job 
    # is being executed) and the KML map if the job has been completed.
    # update = check_session("jobstate_interactive", len(session["jobstate_interactive"])>0, True, False)

    # We do the same for the job info values. If a job has been submitted, we want to assign to the 
    # job_info array his previous values. As before, this can be useful to check if a job has been 
    # submitted, switching page and coming back; we need to get his values again.
    # session["jobinfo_interactive"] = check_session("jobinfo_interactive", len(session["jobinfo_interactive"])>0, session["jobinfo_interactive"], [])

    # Fetch username and last access
    user = session["user"]

    # Reset searchval for other pages (if we change page we must reset the value searched)
    # session["searchval"] = ""

    # Fetch last access knowing the user
    last_access= session["access"]

    hours = [f"0{i}" if i < 10 else f"{i}" for i in range(24)]

    # If the request is post (user submitted options)
    if request.method == "POST":
        # print("[*] RequestManager.py : var request.form = " + str(request.form), flush=True)
        if "generate" in request.form:

            # First thing, we check if a job is already running: since this is the interactive dashboard,
            # We must assert that only a job is active at a time; if the user wants to submit more than one jobs,
            # He should go to the approppriate queue dashboard section.
            # if len(session["jobstate_interactive"]) > 0:
            #    flash("Un'operazione è attualmente in atto. Aspettare che finisca o sottometterne di nuove nella dashboard per le code.") 
            #    return redirect(url_for('interattivo'))
            # else: 
                # If the len of jobstate is 0, that means two things: we're submitting a job
                # for the first time, or a job has been completed and resetted into the progress route.
                # In each case, we reset the jobinfo_interactive array to submit a new one.
                # session["jobinfo_interactive"] = []
           
            area = request.form.get("area")
            if not validate_string(area, "[a-zA-Z]"):
                flash("Area inserita non valida. Unici caratteri consentiti: Lettere [a-z e A-Z]. Riprovare!")
                return redirect(url_for('simulazione-singola'))

            data = request.form.get("data")
            ora = request.form.get("hours")
            durata = request.form.get("durata")
            comune = request.form.get("comune")
            longit = request.form.get("long")
            latit = request.form.get("lat")
            temp = request.form.get("temp")
            codice_GISA = request.form.get("codice_gisa")

            # job_info = ["./EmsSmoke.sh", area, "".join(data.split('-')), str(int(ora)), durata, comune, longit, latit, temp, codice_GISA, data]

            session['durata'] = durata
            session['data'] = "".join(data.split('-'))
            session['ora_inizio'] = str(int(ora))
            session['lon'] = str(longit)
            session['lat'] = str(latit)

            job_info = ["./EmsSmoke.sh", area, "".join(data.split('-')), str(int(ora)), durata, comune, longit, latit, temp, codice_GISA]
            # job_info[0] = user_dir_name
            # job_info[0] = "not yet present"
            job_info[0] = random.randint(1,100)
            job_info.append(str(user))
            db.new_job(job_info)      

            job_id, user_dir_name = sbatchmanager.run(user, job_info)


            '''
            if user_dir_name is False:
                # session['kmlpath_dash'] = ""
                session['user_dir_name'] = ""
                flash("Errore esecuzione job simulazione")
                return redirect(url_for('dashboard'))
            else:
                # session['kmlpath_dash'] = ""
                session['user_dir_name'] = user_dir_name
                job_info[0] = user_dir_name
                job_info.append(str(user))
                db.new_job(job_info)

            '''


            # if kml_path == False:
            #     session["kmlpath_dash"] = ""
            # else: 
            #     session["kmlpath_dash"] = kml_path
            #     size_flag = int(durata)
            #     session["flag_map_kml"] = [0] * size_flag

            # If the returned jobid is 0, that means sbatch could not submit a new job
            # we inform the user and redirect to the page again.
            # Same for nc dumper error
            
            # if jobid == 0:
            #    flash("Non è stato possibile inserire l'operazione in coda. Riprovare!")
            #    return redirect(url_for('interattivo'))
            
            # Check dump info 
            # dumpstate = ncdump.dump(data, str(int(ora)), durata)

            # If dumpstate is -1, we surpassed the meteo prevision limit, flash the message
            # if dumpstate == -1:
            #    flash("Non è stato possibile inserire l'operazione in coda. Non esistono valori meteo per quella data.") 
            #    return redirect(url_for('interattivo'))

            # Create a new job entry in the database for the given user. 
            # Since we do not need the earlier jobinfo structure anymore, we change few things: 
            # - the first element with the jobid (was the name of the script before)
            # - append a last element representing the user (we need to insert info related to the user)
            
            # job_info[0] = jobid
            # job_info.append(user)
            # db.new_job(job_info)


            '''
            # TEST: checking for the submitted id
            print("submitted id {}".format(jobid), flush=True)

            # We update the jobid into the jobstate dash variable: 
            # This var is composed by [jobid, state, scratch_path] variable.
            # Note: scratch_path variable is updated by the get_progress function.
            session["jobstate_interactive"].append([jobid, "IN CORSO", ""])

            # We set the update variable to true, so we can start updating the page checking for
            # progress to update the progress bar
            update = True

            # We reset the kml path if something present (ie: a job already finished and we 
            # want to clear the map)
            session["kmlpath_dash"] = ""

            # We create the execute string (we fetch the jobid from the first element)
            info_str = "ID: {}".format(session["jobstate_interactive"][0][0])

            # Before leaving, we remove the unnecessary elements from jobinfo, and assigning the 
            # entry to the relative session value 
            session["jobinfo_interactive"] = job_info[1:8] 

            # We then append three elements: jobid, current string state and current int state.
            # NOTE: "IN CORSO" = 0, "COMPLETO" = 1, "ERRORE" = 2, "CANCELLATO" = 3
            session["jobinfo_interactive"].append(jobid)
            session["jobinfo_interactive"].append("IN CORSO")
            session["jobinfo_interactive"].append(0)

            print("job value {}".format(session["jobstate_interactive"][0][0]), flush=True)
            print(session["jobinfo_interactive"], flush=True)
        '''
        # Second case: we want to reset the map at the original position
        elif "dresetmap" in request.form:

            # We reset the kml path, simply reloading the page. 
            # We set update to False because we do not want to trigger the update map 
            # function.
            # update = False
            session['user_dir_name'] = ""

        # Third case: the user want to cancel the job
        elif "icancel":
            
            try: 

                # Before trying to eliminate the job, we check if the sbatch manager has finalized
                # the routine for the starting of a new job: to do so, we just check if the jobstate
                # scratch path is different than the "" default init string. If so, the job has been finalized
                # in the sbatch manager functions, and we can safely remove it without breaking anythign
                if not safe_str_cmp(session["jobstate_interactive"][0][2], ""):

                    # We submit the scancel [jobid] command
                    try: 
                        sbatchmanager.cancel_job(session["jobinfo_interactive"][7])
                    except:
                        flash("Errore nella cancellazione dell'operazione. Riprovare!")

                    # We update the state int
                    session["jobinfo_interactive"][9] = 3
                
                else:

                    # We flash a message 
                    flash("Operazione in finalizzazione. Riprovare tra qualche secondo.")
            except:

                pass
    else: 
        print("no post method")
        # If the refreshing isn't triggered by the post button, we face two cases: 
        # The first is simply a page switch, in which we shouldn't to nothing. 
        # The second is that the function get_progress finished successfully a job 
        # and routed to the dashboard function.
        # When the progress function redirect here, we face two cases: we got jobs in the 
        # queue and we dont. We check this 

    
    # interactive.html
    return render_template('interactive.html',
                            user=user, 
                            last_access=last_access, 
                            # update=update, 
                            # info_str=info_str, 
                            # state=session["jobstate_interactive"],
                            # info=session["jobinfo_interactive"], 
                            hours=hours)
                            # kmlpath = session["kmlpath_dash"])
  
# @app.route('/coda', methods=['POST', 'GET'])
@app.route('/simulazioni-multiple', methods=['POST', 'GET'])
def coda():

    # Redirect to login if user not in session
    if "user" not in session:
        return redirect(url_for('login'))

    # Istanciate a db object to perform queries
    db = DBProxy()

    # If the user is an admin trying to accessing the other routes pages, redirect him
    # to the adminpane
    if db.is_admin(session["user"]):
        return redirect(url_for('adminpane'))

    # As the interactive route, we init some session variables to remember what´s happening wheen 
    # switching pages. THE ONLY DIFFERENCE is that in the interactive page we can have an UNIQUE
    # job per time, here we can have multiple running.
    # Assign values to jobstate (queue): if present, we assign that very array, empty if not 

    # The update value is passed inside an hidden input and later checked by a JS function: 
    # If the value is true, we must call the update function to update the progress bar (a job 
    # is being executed) and the KML map if the job has been completed.
    # update = check_session("jobinfo_queue", len(session["jobinfo_queue"])>0, True, False)

    # Fetch username and last access
    user = session["user"]

    # Fetch a local structure of jobinfo queue
    # queue_lock.acquire()
    # jobinfo_queue = session["jobinfo_queue"]
    # queue_lock.release()

    # Reset searchval for other pages (if we change page we must reset the value searched)
    # session["searchval"] = ""

    # Fetch last access knowing the user
    last_access = session["access"]

    # Creating the hour list: 24 hours UTC. (00, 01, 02...23)
    hours = [f"0{i}" if i < 10 else f"{i}" for i in range(24)]

    # If the request is post (user submitted options)
    if request.method == "POST":

        # First case: the button pressed is the generation one, so we need to 
        # fetch values from the textfields 
        if "generate" in request.form:

            # First thing, we check if a job is already running: since this is the interactive dashboard,
            # We must assert that only a job is active at a time; if the user wants to submit more than one jobs,
            # He should go to the approppriate queue dashboard section.
            # We get number of active jobs (jobs which are still active (>0))
            
            # jobs = get_slurm_queue("g.hauber")

            # if len(jobs) >= 10:
            #    flash("Massimo tetto di operazioni raggiunte. Cancellarne qualcuna o aspettare che finiscano per immetterne di nuove!") 
            #    return redirect(url_for('coda'))

            # Getting all the parameters for the script 
            # from the relatives fields
            area = request.form.get("area")

            # Since area is the only alphabetical textfield, we need to check if its valid: 
            if not validate_string(area, "[a-zA-Z]"):
                flash("Area inserita non valida. Unici caratteri consentiti: Lettere [a-z e A-Z]. Riprovare!")
                return redirect(url_for('coda'))

            data = request.form.get("data")
            ora = request.form.get("hours")
            durata = request.form.get("durata")
            longit = request.form.get("long")
            latit = request.form.get("lat")
            temp = request.form.get("temp")
            
            # We first check if start+duration is major than 24 (limit hours)
            # if int(ora)+int(durata) > 24:
            #    flash("Non è stato possibile inserire l'operazione in coda. La durata supera le 24 ore!") 
            #    return redirect(url_for('interattivo'))

            job_info = ["./EmsSmoke.sh", area, "".join(data.split('-')), str(int(ora)), durata, longit, latit, temp, data]

            jobid = sbatchmanager.run(user, job_info)

            db_manager = DBManager()

            ora_int = int(ora)
            ora_module = datetime.strptime(str(ora_int % 24), "%H")
            ora_formattata = ora_module.strftime("%H:%M:%S")
            # db_manager.execute('INSERT INTO SIMULAZIONE (AREA, "DATE", ORAINIZIO, TEMPERATURA, LONGITUDINE, LATITUDINE, DURATA, USERUSERNAME, STATOFINALE) VALUES (''Area di simulazione'', ''2024-03-06'', ''12:00:00'', 25.50, 10.123456, 45.678901, ''2 hours'', ''nome_utente'', TRUE);')
            query = 'INSERT INTO SIMULAZIONE (AREA, "DATE", ORAINIZIO, TEMPERATURA, LONGITUDINE, LATITUDINE, DURATA, USERSIM, STATOFINALE) VALUES (\'{}\', \'{}\', \'{}\', {}, {}, {}, \'{}\', \'{}\', {});'.format(area, data, ora_formattata, temp, longit, latit, durata, user, 'NULL')

            # db_manager.execute(query)
            db_manager.update(query)

            # print("----------- INSERTED NEW JOB: {}".format(jobid))
            # If the returned jobid is 0, that means sbatch could not submit a new job
            # we inform the user and redirect to the page again.
            # Same for nc dumper error
            # if jobid == 0:
            #     flash("Non è stato possibile inserire l'operazione in coda. Riprovare!") 
            #     return redirect(url_for('coda'))
            
            # Check dump info 
            # dumpstate = ncdump.dump(data, str(int(ora)), durata)

            # If dumpstate is -1, we surpassed the meteo prevision limit, flash the message
            # if dumpstate == -1:
            #    flash("Non è stato possibile inserire l'operazione in coda. Non esistono valori meteo per quella data.") 
            #    return redirect(url_for('coda'))

            # Create a new job entry in the database for the given user. 
            # Since we do not need the earlier jobinfo structure anymore, we change few things: 
            # - the first element with the jobid (was the name of the script before)
            # - append a last element representing the user (we need to insert info related to the user)
            job_info[0] = jobid
            job_info.append(user)

            # Try inserting the new job into the databse
            try:
                db.new_job(job_info)

            except:
                # Delete from the queue if unsuccessful
                # sbatchmanager.cancel_job(jobid)
                flash("Non è stato possibile inserire l'operazione in coda. Riprovare!") 
                # return redirect(url_for('coda'))
              

            # TEST: checking for the submitted id
            # print("submitted id {}".format(jobid))

            # We set the update variable to true, so we can start updating the page checking for
            # progress to update the progress bar
            # update = True

            # Before leaving, we remove the unnecessary elements from jobinfo (first), and assigning the 
            # entry to a new submitted job list
            # submitted_job = job_info[1:8]

            # We then append three elements: jobid, current string state and current int state.
            # NOTE: "SOTTOMESSO/IN CORSO" = 0, "COMPLETO" = 1, "ERRORE" = 2, "CANCELLATO" = 3
            # submitted_job.append(jobid)
            # submitted_job.append("SOTTOMESSO")
            # submitted_job.append(0)

            # We append the job to the local structure 
            # jobinfo_queue.append(submitted_job)

            # At last, we update both the state dictionary and the info array in a lock
            # We update the jobid into the jobstate dash variable: 
            # This var is composed by [jobid, state, scratch_path] variable.
            # Note: scratch_path variable is updated by the get_progress function.
            # queue_lock.acquire()

            # session["jobinfo_queue"] = jobinfo_queue
            # queue_lock.release()

            # Set modified to true
            # session.modified = True

            # print("INSERTING NEW JOB DONE --------------------")

            # print(session["jobinfo_queue"]) 
            # print("-------------------------------------------")
        
        # Second case: the user want to cancel the job
        # elif "qcancel" in request.form:
            ''' 
            # We lock the thread for the entire request to avoid multiple elimination request
            # at once, we may lost something
            queue_lock.acquire()
            if not session["queue_ops_in_act"]:
                
                # Operation in act 
                session["queue_ops_in_act"] = True

                # Unlock 
                queue_lock.release()

                # We get the index of the array in which the button has been pressed 
                index = int(request.form['qcancel'])
                print(index)
                
                # We fetch the jobid from the jobinfo array 
                jobid = session["jobinfo_queue"][index][7]

                # Before trying to eliminate the job, we check if the sbatch manager has finalized
                # the routine for the starting of a new job: to do so, we just query the database 
                # given the jobid of the selected job in the selected table row, and we got the 
                # PATH: basically if none, the job hasn't finalized yet 
                path = None
                try:

                    # We try to fetch the path from the given jobid
                    path = db.specific_select("JOBIDENTIFIER", "PATH", "JOBID", jobid)

                except: 
                    
                    # Flash an error and render again
                    flash("Non è stato possibile trovare l'operazione in coda. Riprovare!")
                    return redirect(url_for('coda'))

                # If we returned something
                if path is not None:

                    # We try to submit the scancel [jobid] command
                    try: 
                        sbatchmanager.cancel_job(jobid)
                    except:
                        flash("Errore nella cancellazione dell'operazione. Riprovare!")

                    # We update the session deleting the element
                    del session["jobinfo_queue"][index]
                    session.modified = True
                
                else:

                    # We flash a message 
                    flash("Operazione in finalizzazione. Riprovare tra qualche secondo.")

                # No ops in act 
                queue_lock.acquire()
                session["queue_ops_in_act"] = False
                queue_lock.release()
            
            else: 

                # Unlock 
                queue_lock.release()

                # We flash a message 
                flash("Operazione di eliminazione in finalizzazione. Riprovare tra qualche secondo.")
        '''
        # elif "qresetjob" in request.form:
        #    pass

            # If we reload the job, we do an integrity check to understand if 
            # some job has been lost. We get the queue state by the parser
            # We retry the dictionarized squeue job list 
            # jobs = get_slurm_queue("g.hauber")
            
            # Fetch a local structure of jobinfo queue
            # queue_lock.acquire()
            # jobinfo_queue = session["jobinfo_queue"]
            # queue_lock.release()

            # Now we iterate the jobinfo queue
            # print("RESET JOB")

    
    # Since the user can submit more than a few jobs, we need to pagine the results into
    # responsive pages. How do we do that? -> pagination!
    # Set up pagination -----------
    # We get the first page to show 
    page = int(request.args.get('page', 1))

    # Then we init a per-page elements value
    per_page = 10

    # The offset represent the number of the element currently showed. 
    # For example, given per_page being 10 (10 elements showed per page): 
    # Page 1: 1-1 (0) * 10 -> 0
    # Page 2: 2-1 (1) * 10 -> 10 etc
    offset = (page - 1) * per_page

    # Then we paginate the data: this is just showing a portion of the total data each time 
    # we change pagination page. We use a slicing varying from offset to offset+perpage elements.
    pagination_data = session["jobinfo_queue"][offset: offset + per_page]

    # Since the user can delete job based on his needs, we need to check if the new pagination 
    # data array is empty; that could happen when, for example, on a new page there is only one job:
    # deleting that very job will cause the data for that page to be empty, so we need to go back to 
    # the last page. We also check if we do have more job in queue, so we avoid doing so if thats the case.
    # print("------- len")
    # print (session["jobinfo_queue"])
    # print (len(pagination_data), len(session["jobinfo_queue"]))
    # print(len(pagination_data) == 0 and len(session["jobinfo_queue"]) != 0)
    # print("--------")

    
    if len(pagination_data) == 0 and len(session["jobinfo_queue"]) != 0: 
        
        # We subtract a page then doing the offset calculation again
        page -= 1
        offset = (page - 1) * per_page

        # We do assign the new pagination data belonging to the previous page, only if 
        # the lenght of the jobinfo queue is diff than 0 (still job in queue)
        pagination_data = session["jobinfo_queue"][offset: offset + per_page]

    # print("NEW PAGINATION DATA-------------")
    # print(page, offset, pagination_data)
    # print("-----------------------------")

    # Then we build the pagination element passing all the constructed values
    pagination = Pagination(page=page, per_page=per_page, total=len(session["jobinfo_queue"]), css_framework='bootstrap5')
    
    # Building datainfo to show number of elements per page 
    datainfo = [offset, offset + per_page, len(session["jobinfo_queue"])]
    
    # We render the template with the associated info
    return render_template('queue.html', 
                           user=user, 
                           last_access=last_access, 
                           # update=update, 
                           queue=pagination_data,
                           pagination=pagination, 
                           datainfo=datainfo,
                           hours=hours
                        )

@app.route('/profilo', methods=['POST', 'GET'])
def profilo(alert_category=""):


    # If the user did not authenticate, redirect it to the login page
    if "user" not in session:
        return redirect(url_for('login'))

    # Istanciate a db object to perform queries
    db = DBProxy()

    # If the user is an admin trying to accessing the other routes pages, redirect him
    # to the adminpane
    if db.is_admin(session["user"]):
        return redirect(url_for('adminpane'))

    # Fetch username
    user = session["user"]

    # Reset searchval for other pages (if we change page we must reset the value searched)
    session["searchval"] = ""
    
    # Fetch last access knowing the user
    last_access=db.get_last_access(user)

    # Fetch profile elements
    profile=db.get_profile(user)

    # We init the alert category to the input 
    category = alert_category

    # If we user submit a change 
    if request.method == "POST":

        # We do fetch the element of the text fields changed
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        password = request.form.get("password")
        telephone = request.form.get("telephone")

        # We hash the pass
        hashed_password = generate_password_hash(password)

        # Update the values if different than the empty string
        try:
            db.update_profile(user, firstname, lastname, hashed_password, telephone)
        except Exception as E:
            category = "alert-danger"
            flash("Impostazioni salvate correttamente!")
            return redirect(url_for('profilo', alert_category=category))


        # Flash a confirmation message
        category = "alert-success"
        flash("Impostazioni salvate correttamente!")

        # Set the profile to empty strings if no user input else existing string
        # to let the user reload the page and see the changes
        profile=[firstname if firstname!="" else profile[0], 
                lastname if lastname!="" else profile[1], 
                telephone if telephone!="" else profile[2]]

    return render_template('profilo.html', user=user, last_access=last_access, profile=profile, category=category)

@app.route('/storico', methods=['POST', 'GET'])
def storico():

    # If the user did not authenticate, redirect it to the login page
    if "user" not in session:
        return redirect(url_for('login'))

    # Istanciate a db object to perform queries
    db = DBProxy()

    # If the user is an admin trying to accessing the other routes pages, redirect him
    # to the adminpane
    if db.is_admin(session["user"]):
        return redirect(url_for('adminpane'))
    
    user = session["user"]

    last_access=db.get_last_access(user)

    # Fetch only completed jobs relative to the user
    jobs = db.fetch_jobs(user)

    print("[*] RequestManager.py : var jobs = " + str(jobs), flush=True)

    # Create a dictionary containing the long, lat and jobid
    markers = []

    # Create, for each job, an entry composed by: jobid-lat-long
    for job in jobs:
         markers.append([job[8], job[5], job[4]])

    # KML path: we point an empty kml initially 
    # kml_path = safe_join("KML", "dummy.kml")

    # JOBID selected at start is none. We'll show that in the historical pane map
    # jobid = "Nessuno"

    # Setup an empty searchpage, to reset the page pointer to the first page if the user 
    # does search something
    # search_page = None

    # If a button has been pressed
    if request.method=="POST":  
        
        # The first case is the search button: we need to query again the 
        # jobs specifying a particular element as query key.
        if "hsearchbutton" in request.form:
            
            # Given the search value as filter 
            search_filter = request.form.get("hsearchvalue").lower()
            
            print("[*] RequestManager.py : var search_filter = " + str(search_filter), flush=True)

            # New users are the filtered match 
            jobs = filters(search_filter, jobs)

            print("[*] RequestManager.py : var jobs = " + str(jobs), flush=True)

            # Insert into session a value representing the actual search
            session["searchval"] = search_filter

            search_page = 1

        # The second case is the show button related to a specific KML file associated 
        # with a specific JOBID. on press, we must load that kml file into the map.
        # elif "hshowbutton" in request.form:

            # We get the jobid in which the button has been pressed
            # jobid = int(request.form['hshowbutton'])
            
            # We then serve the file in the static folder if it hasn't yet and return the kml path
            # kml_path = serve_kml(jobid, db)

            # Reset marker array, we don't want to show them while showing a kml file
            # markers = []

        # The third case is related to the user pressing the delete button. If so, we need to extract 
        # The jobid from the request and perform deletion on both database/folders of that specific job.
        # elif "hdeletebutton" in request.form:

            # We get the jobid in which the button has been pressed
            # jobid = int(request.form['hdeletebutton'])

            # We delete the entry relative to: JOBS, JOBINFO and JOBIDENTIFIER
            # db.delete_row("JOBS", "JOBID", jobid)
            # db.delete_row("JOBINFO", "JOBID", jobid)
            # db.delete_row("JOBIDENTIFIER", "JOBID", jobid)

            # We then proceed to remove the directories
            # data_path = safe_join("root/storage/fumi2/{}".format(session["user"]), str(jobid))
            # kml_path = safe_join("static/storage/fumi2/{}".format(session["user"]), str(jobid))

            # Using safe remove
            # safe_rmdir(data_path)
            # safe_rmdir(kml_path)

            # Delete the job from the job array 
            # for i, job in enumerate(jobs):
            #    if job[8] == jobid:
            #         del jobs[i]   


        # The third case is when the user press the reset button on the map. 
        # In that case, we reset the KML layer. 
        # elif "hresetmap" in request.form:
            
            # Reset info
            # jobid="Nessuno"
            # kml_path = safe_join("KML", "dummy.kml")

        # The last case is when the user want to reset the search.
        # elif "hresetjob" in request.form:

            # We just put the search val to empty 
            # session["searchval"] = ""

    # else: 
    #     pass       
        # If here, that means the user submitted a search and now is searching for the 
        # next/prev pages in his search. Use the search val stored in session to resume his 
        # search 
        # if "searchval" in session:
        #    jobs = filters(session["searchval"], jobs)


    # Set up pagination: we use the same approach used into the 'queue' section:
    # page = int(request.args.get('page', 1)) if search_page is None else search_page
    page = int(request.args.get('page', 1))
    print(page)
    per_page = 5
    offset = (page - 1) * per_page
    pagination_data = jobs[offset: offset + per_page]
    pagination = Pagination(page=page, per_page=per_page, total=len(jobs), css_framework='bootstrap5')
    datainfo = [offset, offset + per_page, len(jobs)]

    # Finally, render the template
    return render_template('storico.html', 
                           user=user, 
                           last_access=last_access, 
                           jobs=pagination_data, 
                           pagination=pagination,
                           datainfo=datainfo)
                           # kml_path=kml_path,
                           # jobid=jobid, 
                           # markers=markers)

@app.route('/adminpane', methods=['POST', 'GET'])
def adminpane():

    if "user" not in session:
        return redirect(url_for('login'))
    db = DBProxy()

    if not db.is_admin(session["user"]):
        return render_template('blank.html')

    user = session["user"] 
    last_access=db.get_last_access(user)
    users = db.fetch_users()


    # If a button has been pressed
    if request.method=="POST":  

        # Identify the button: we can have different cases.
        # The first one, is the save button; we need to create an user with those info
        if "savebutton" in request.form: 

            # Fetch the values
            username = request.form.get("username")
            firstname = request.form.get("firstname")
            lastname = request.form.get("lastname")
            email = request.form.get("email")
            struttura = request.form.get("struttura")
            ruolo = request.form.get("ruolo")

            # First thing: check if the username contains not-allowed character
            user_ok = validate_string(username)

            # print(user_ok)
            # If the value is false, that means the string contains special characters.
            # We need to flash an error message and prompt the page again
            if user_ok==False: 

                # We put the category of the error inside the variable and flash the message
                # session["category"] = "alert-danger"
                flash("Errore: caratteri non consentiti nell'username! (ammissibili: a-z A-z 0-9 . e _)")
                
                # we render again the pane passing category as input var
                return redirect(url_for('adminpane'))

            # Insert the user in a try catch block: this because 
            # the insertion may fail if already an user exists with that infos, 
            # also redirecting him to admin pane.
            try:
                db.add_user(username.lower(), firstname, lastname, email, struttura, ruolo)
            except Exception as e:

                # We put the category of the error inside the variable
                # session["category"] = "alert-danger"

                flash("Errore nell'inserimento dell'utente. Riprovare!")       
                return redirect(url_for('adminpane'))

            # We generate an unique link for the registration form given the username 
            link = generate_unique_link(username, "registrazione")
            # Send email with link
            msg = Message('Registrazione al sistema FUMI2', sender = 'regionefumi2@gmail.com', recipients = [email])
            msg.body = f"Benvenuto al sistema FUMI2, {username}!. Visitare il link per completare la registrazione: {link}"

            try:
                mail.send(msg)
            except:
                # Flash and category
                # session["category"] = "alert-danger"
                flash("Errore nell'invio della mail. Rimandarla con l'apposito pulsante per generazione password!")
                return redirect(url_for('adminpane'))
                
            # We then flash a success message.
            # session["category"] = "alert-success"
            flash("Utente {} registrato con successo! Link di registrazione generato.".format(username))
            return redirect(url_for('adminpane'))

        # The second case is the search button: we need to query again the 
        # users specifying a particular element as query key.
        elif "searchbutton" in request.form:
            
            # Given the search value as filter 
            search_filter = request.form.get("searchvalue").lower()

            # Update the list with filtered users
            users = filters(search_filter, users)

            # print(users)

            # Insert into session a value representing the actual search
            # session["searchval"] = search_filter

            # Reset search page 
            search_page = 1


        # The third case is the delete button: When the admin press this, we need to 
        # the corrispondent user.
        elif "deletebutton" in request.form:

            # We wait for the confirmation of the alert box. Basically, what happens 
            # When we click the confirm, is that the request is sent only when OK/BACK
            # is presed. So it's an extension of the POST method.
            confirmed = request.form.get("confirmed")

            # Since the function return a name if confirmed and False otherwise, we 
            # check directly if confirmed is different than false. If so, we do use the 
            # confirmed value to delete the user (the name)
            if confirmed!=False: 
                
                # Delete the users from the db
                db.delete_user(confirmed)

                # Delete the user from the user array 
                for i, user in enumerate(users):
                    #if safe_str_cmp(user[2], confirmed):
                    if hmac.compare_digest(user[2], confirmed):
                        del users[i]     

                # We also need to check if the admin wants to delete data: 
                if request.form.get("datacheck")=="on":

                    # If the checkbox is checked, we delete the storage folder 
                    # and the static containing the kml served files
                    user_data_path = safe_join("root/storage/fumi2", confirmed)
                    user_kml_path = safe_join("static/storage/fumi2", confirmed)
                    safe_rmdir(user_data_path)
                    safe_rmdir(user_kml_path)

                # We flash the success of the elimination for that user
                session["category"] = "alert-success"
                flash("Utente cancellato correttamente: {}".format(confirmed))
                    

        # Fourth case, the password change request is pressed: we need to initi 
        # the procedure for creating a new password with an automatic mail.
        elif "passwordbutton" in request.form:
            
            # We get the user in that row
            username = request.form.get("passwordbutton").lower()

            # We check if that user is active or not: 
            is_active = db.user_active(username)


            # We create three empty vars, will be based on the user state
            link = ""
            title = ""
            body = ""

            # Now, if the user is active
            if is_active:

                # we generate a link to the password reset; also a title and body for the
                # email msg
                link = generate_unique_link(username, "ripristino")
                title = "Ripristino Password FUMI2"
                body = "Ciao {}! Hai richiesto un ripristino della password. Visitare il link per completare la procedura".format(username)
            
            else:

                # Else, the user is not active; we generate a registration link
                link = generate_unique_link(username, "registrazione")
                title = "Registrazione al sistema FUMI2"
                body = "Benvenuto al sistema FUMI2, {}!. Visitare il link per completare la registrazione".format(username)

            # We get the email of the user 
            # email = db.specific_select("USER", "EMAIL", "USERNAME", username)
            email = db.specific_select("\"USER\"", "EMAIL", "USERNAME", username)

            # Send email with ripristination link
            msg = Message(title, sender = 'regionefumi2@gmail.com', recipients = [email])
            msg.body = f"{body}: {link}"

            try:
                mail.send(msg)
            except:
                
                # Flash and category set
                # session["category"] = "alert-danger"
                flash("Errore nell'invio della mail. Rimandarla con l'apposito pulsante per generazione password!")
                
            # Flash success if no error given
            # session["category"] = "alert-success"
            flash("Ripristino password effettuato per {}".format(username))

            # Redirect to adminpane to load users again
            return redirect(url_for('adminpane'))

            
        # Fifth case, we want to deactivate the user
        elif "deactivatebutton" in request.form:

            # We get the user in that row
            username = request.form.get("deactivatebutton").lower()

            # We try to submit a deactivation query 
            try:
                db.update_column("\"USER\"", "ACTIVE", "USERNAME", [0, username])

            except Exception as e:

                # We put the category of the error inside the variable
                # session["category"] = "alert-danger"

                # We flash the message
                flash("Errore nella disattivazione dell'utente {}. Riprovare!".format(username))       

                # Redirect to adminpane
                return redirect(url_for('adminpane'))

            # Flash success if no error given
            # ession["category"] = "alert-success"
            flash("Utente {} disattivato con successo.".format(username))

            # Redirect to adminpane to load users again
            return redirect(url_for('adminpane'))

        # Sixth case, we want to activate the user 
        elif "activatebutton" in request.form: 

            # We get the user in that row
            username = request.form.get("activatebutton").lower()

            # Since an user can be inactive because he just got registered, we need to check
            # a simple thing: does he got a password yet? If so, that means the user is already registered
            # and he got disactivated due to some circumstance. If he doesn't have a password, that means 
            # he need to complete his registation yet; in that case we can't activate him and a new
            # registration form must be sent again.
            has_pass = db.specific_select("\"USER\"", "PASSWORD", "USERNAME", username)

            # If he has a pass
            if has_pass is not None:

                # We proceed to activate the user 
                # We try to submit a deactivation query 
                try:
                    db.update_column("\"USER\"", "ACTIVE", "USERNAME", [1, username])

                except Exception as e:

                    # We put the category of the error inside the variable
                    # session["category"] = "alert-danger"

                    # We flash the message
                    flash("Errore nella disattivazione dell'utente {}. Riprovare!".format(username))       

                    # Redirect to adminpane
                    return redirect(url_for('adminpane'))
            else:
                
                # Else, the user has not been registered yet. We need to inform the admin
                # Setting category     
                # session["category"] = "alert-danger"

                # We flash the message
                flash("Errore: L'utente {} deve ancora completare la registrazione. Prova a generare un'altra registrazione con il pulsante [Password!]".format(username))       

                # Redirect to adminpane
                return redirect(url_for('adminpane'))

            # Flash success if no error given
            # session["category"] = "alert-success"
            flash("Utente {} attivato con successo.".format(username))

            # Redirect to adminpane to load users again
            # return redirect('adminpane.html')
            return render_template('adminpane.html')


        # Last case: we want to reset the user info in the original search
        elif "aresetusers" in request.form:
            pass

            # We reset the search val 
            # session["searchval"] = ""

    else: 
        pass
        
        # If here, that means the user submitted a search and now is searching for the 
        # next/prev pages in his search. Use the search val stored in session to resume his 
        # search 
        #if "searchval" in session:
        #    users = filters(session["searchval"], users)
        #    print(users)
    
    # Set up pagination: We follow the same approach used into the "storico" section.
    # Refer there for more info.
    # page = int(request.args.get('page', 1)) if search_page is None else search_page
    page = int(request.args.get('page', 1))
    per_page = 5
    offset = (page - 1) * per_page
    pagination_data = users[offset: offset + per_page]
    pagination = Pagination(page=page, per_page=per_page, total=len(users), css_framework='bootstrap5')
    datainfo = [offset, offset + per_page, len(users)]
    print("---adminpane - pagination_data : " + str(pagination_data), flush=True)
    print("---adminpane - users : " + str(user), flush=True)



    # Render the adminpane with options
    return render_template('adminpane.html',
                           last_access=last_access,
                           users=pagination_data,
                           pagination=pagination,
                           datainfo=datainfo)
                           # category=session["category"])

@app.route('/registrazione/<unique_id>', methods=['GET', 'POST'])
def registration(unique_id):

    # Simple registration mechanism. This page is uniquely visited when an admin does
    # create a new user into the system, automatically sending him a mail to complete his registration.
    # We got three argument there: Password, telephone number and 
    if request.method == "POST":    

        # Istanciate a db object to perform queries
        db = DBProxy()

        # We first decode the username: following the unique id structure defined in the adminpane 
        # save logic
        split = base64.b64encode("split".encode('utf-8')).decode('utf-8')
        user = unique_id.split(split)[0]
        decoded_name = base64.b64decode(user.encode('utf-8')).decode('utf-8')

        # We fetch those info
        password = request.form.get("password")
        password_again = request.form.get("password-again")
        birthdate = request.form.get("date")
        telephone = request.form.get("telephone")
        
        # We compare the password: if they're not equal, we flash a message
        # and basically reload the page again
        #if not safe_str_cmp(password, password_again):
        if not hmac.compare_digest(password, password_again):
            flash("Le password non corrispondono.")

        else:
            # We check if the password are at least: 8 character long and contains at least:
            # 1 character / 1 number / 1 special char
            if not validate_password(password):

                # If not we flash a message and render again 
                flash("La password deve contenere 8 caratteri ed almeno una lettera, un carattere speciale ed un numero.")
            else:
                # We then update the table 
                #db.update_column("USER", "PASSWORD", "USERNAME", [generate_password_hash(password), decoded_name])
                #db.update_column("USER", "BIRTHDATE", "USERNAME", [birthdate, decoded_name])
                #db.update_column("USER", "TELEPHONE", "USERNAME", [telephone, decoded_name])
                #db.update_column("USER", "ACTIVE", "USERNAME", [1, decoded_name])
                db.update_column("\"USER\"", "\"PASSWORD\"", "USERNAME", [generate_password_hash(password), decoded_name])
                db.update_column("\"USER\"", "BIRTHDATE", "USERNAME", [birthdate, decoded_name])
                db.update_column("\"USER\"", "TELEPHONE", "USERNAME", [telephone, decoded_name])
                db.update_column("\"USER\"", "ACTIVE", "USERNAME", [1, decoded_name])

                # After the registration, we redirect for login
                return redirect(url_for('login'))

    # render the registation form
    return render_template('registrationform.html')

@app.route('/ripristino/<unique_id>', methods=['GET', 'POST'])
def restoration(unique_id):

    # Simple password reset mechanism. This page is uniquely visited when an admin does
    # create a new user into the system, automatically sending him a mail to complete his ripristination.
    # We got two argument there: Password and Password again.jobinfo_queue

    # We fetch the username by decoding his string: logic described in the admipane save section
    split = base64.b64encode("split".encode('utf-8')).decode('utf-8')
    user = unique_id.split(split)[0]
    decoded_name = base64.b64decode(user.encode('utf-8')).decode('utf-8')

    # If the user has pressed a button
    if request.method == "POST":

        # We fetch the pass info
        password = request.form.get("password")
        password_again = request.form.get("password-again")

        # We compare the password: if they're not equal, we flash a message
        # and basically reload the page again
        # if not safe_str_cmp(password, password_again):
        if not hmac.compare_digest(password, password_again):
            flash("Le password non corrispondono.")

        else:

            # We check if the password are at least: 8 character long and contains at least:
            # 1 character / 1 number / 1 special char
            if not validate_password(password):

                # If not we flash a message and render again 
                flash("La password deve contenere 8 caratteri ed almeno una lettera, un carattere speciale ed un numero.")
                
            else:

                # Istanciate a db object to perform queries
                db = DBProxy()
                
                # Else, we then update the table with the password
                # db.update_column("USER", "PASSWORD", "USERNAME", [generate_password_hash(password), decoded_name])
                db.update_column("\"USER\"", "\"PASSWORD\"", "USERNAME", [generate_password_hash(password), decoded_name])

                # We also check if the user isn't active, to set his active state to true 
                is_active = db.user_active(decoded_name)

                # If not we update his state
                if not is_active:
                    db.update_column("\"USER\"", "ACTIVE", "USERNAME", [1, decoded_name])

                # After the registration, we redirect for login
                return redirect(url_for('login'))

    # render the registation form
    return render_template('passwordform.html', user=decoded_name)

######################
## EXTERNAL ROUTES ##
#####################

@app.route('/logout', methods=['POST', 'GET'])
def logout():

    # Simple logout mechanism. We do pop the user from the session stack
    # and redirect to login.
    session.pop("user", None)

    return redirect(url_for('login'))

@app.route('/download', methods=['POST', 'GET'])
def download(): 

    
    # Fourth and last case of the historic, the download button. When this button is pressed,
    # We must organize an output zip file containing all the model output files for that given id.
    # NOTE that, to avoid memory consumption we'll make all the object in memory!
    if request.method == "POST":

        # Istanciate a db object to perform queries
        db = DBProxy()

        # Fetch the jobid
        jobid = int(request.form['hdownloadbutton'])

        # Get the output path based on the jobid 
        OUTPATH = db.get_output_path(jobid, "root")

        # Init an IO object to store object in memory
        fileobj = io.BytesIO()

        # Create a ZipFile Object
        with zipfile.ZipFile(fileobj, 'w') as zip_file:

            # For the element of the output folder: 
            for file in os.listdir(OUTPATH):
                
                # Safe join the file and the filepath 
                file_path = safe_join(OUTPATH, file)

                # Add multiple files to the zip
                zip_file.write(file_path, os.path.basename(file_path))

        # Seek at 0th byte
        fileobj.seek(0)

        # Make a response to send back
        response = make_response(fileobj.read())
        response.headers.set('Content-Type', 'zip')
        response.headers.set('Content-Disposition', 'attachment', filename="{}.zip".format(jobid))
        return response

@app.route('/progress')
def progress():
    
    # Route called by the AJAX function that checks at a given interval files into a given directory  
    # To update the progress bar. To do so, the structure of progress is composed as follow: 
    # [percentage of files, path to kml file, completed state]
    # We call the get progress function to return such structure
    progress = get_progress()
    
    # After we get the progress elements, we need to check for the percentage. 
    # If we reached 100%, we need to pop the first element (and unique at each time) from 
    # the jobdash_state list, so an user can submit a new job if wanted.
    if int(round(progress[0])) == 100:

        # Reset the state array
        session["jobstate_interactive"] = []

        # Update the info state and kml file based on the state fetched
        if progress[2] == 1:

            # If state is 1, then we succeded and completed the job: we put the right info
            # into the cookie session
            session["jobinfo_interactive"][8] = "COMPLETATO"
            session["jobinfo_interactive"][9] = progress[2]
            session["kmlpath_dash"] = progress[1]
        else: 

            # else, we did not succeed. If the info state is different than 3 (canceled)
            # We update the info str, so if the user change pages will find the results
            # back on available. 
            if session["jobinfo_interactive"][9] == 3:
                session["jobinfo_interactive"][8] = "CANCELLATO"
            else:
                session["jobinfo_interactive"][8] = "ERRORE"
    
    # We return the json data
    return jsonify({"progress": progress[0], "kmlpath": progress[1], "state": progress[2]})

@app.route('/queue')
def queue():
    
    # Istanciate a db object to perform queries
    db = DBProxy()

    # This function takes care of updating the states of the job currently in queue, displaying 
    # their state (completed or error) in the apposite table. 
    # This function is called by an AJAX function following the same logic of the progress one. 
    # The difference is that we want to check at each request just the state of a given job. 
    # We init an empty dictionary to return later as a json to the function:
    data = {}

    # Init key values 
    data["qsize"] = 0
    data["states"] = []

    # We acquire session info locking
    queue_lock.acquire()
    data["tsize"] = len(session["jobinfo_queue"])
    queue_lock.release()

    # We retry the dictionarized squeue job list 
    squeue_list = parser.dictionarize("squeue")

    # We extract all the jobs corresponding to the machine user (a.riccio)
    # And their states (R, PD)
    user = "g.hauber"
    jobs = {}
    for key in squeue_list: 
        if safe_str_cmp(squeue_list[key]["USER"], user):
            jobs[key] = squeue_list[key]["ST"]
    
    # Now qsize is the len of the jobs dict
    data["qsize"] = len(jobs)

    # If there are any jobs in the queue left
    if data["qsize"] > 0:

        # We check the entire last updated session jobinfo array to update states 
        for i, job in enumerate(session["jobinfo_queue"]): 

            # Fetch the jobid
            cur_jobid = job[7]

            # We fetch the state for the current jobid
            # State initially is a value not handled in the js ajax func cases
            state = -2

            # We try to fetch state in db
            try:
                state = db.specific_select("JOBINFO", "COMPLETED", "JOBID", cur_jobid)
            except Exception:
                pass

            # Now, if the job is running we need to check his state
            if cur_jobid in jobs:

                # If is in a pending state, set to -1 (waiting for resources) else the state itself
                state = -1 if jobs[cur_jobid]=="PD" else state

            # We append the state to the state array: 
            data["states"].append(state)

            # Then we update the jobinfo info state string, switching states and assign right label
            # Also, if a job is completed/deleted or canceled, we delete it from the session
            #TODO: label not showing properly, but everything seems to work!
            if state == -1:
                session["jobinfo_queue"][i][8] = "IN ATTESA"
            elif state == 0:
                session["jobinfo_queue"][i][8] = "IN CORSO"
            elif state == 1:
                del session["jobinfo_queue"][i]
            elif state == 2:
                del session["jobinfo_queue"][i]
            elif state == 3:
                del session["jobinfo_queue"][i]

            # We set modified 
            session.modified = True
            #print(session["jobinfo_queue"])

    else: 

        # Else, queue is empty: we fetch all the states of the jobinfo array and
        # build the last state array to return and update finally all the remaining jobs
        for jobinfo in session["jobinfo_queue"]:
            data["states"].append(db.specific_select("JOBINFO", "COMPLETED", "JOBID", jobinfo[7]))

        # No jobs left: we reset the structures
        session["jobinfo_queue"] = []
        session.modified = True


    # We return the data array 
    return jsonify(data)

if __name__ == "__main__":
    
    # Secret app key for session cookies (each time we restart the server, a new key is created:
    # doing so, all the cookies will be deleted and the user will need to sign in and create them again)
    app.secret_key = secrets.token_hex()

    # Running app at the specified port
    #app.run(debug=True, port=port)
    # app.run(debug=True, port=port, host='0.0.0.0')
    print("PORT : " + str(port), flush=True) 
    app.run(debug=True, host='0.0.0.0', port=port)
