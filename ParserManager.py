import json
import numpy as np
from subprocess import getoutput
from enum import IntEnum

# Enum util for code cleaning purpose
class JOBINFO(IntEnum):
    JOBID = 0
    PARTITION = 1
    NAME = 2
    USER = 3
    ST = 4
    TIME = 5
    NODE = 6
    NODELIST = 7

# Util class that will perform various parsing operation
class Parser():

    def jsonify(self, cmd, sorting_param=JOBINFO.JOBID):

        # Processing the dictionary from the pipeline
        paramdict = self.__parsing_pipeline(cmd, sorting_param)

        # Parsing from dictionary to json and returning the object
        json_object = json.dumps(paramdict, indent=4)
        return json_object

    def vectorize(self, cmd, sorting_param=JOBINFO.JOBID):

        # Processing the dictionary from the pipeline
        paramdict = self.__parsing_pipeline(cmd, sorting_param)

        # Building the jobvector. This will be a list of pair, in which:
        # jobvector[n] represent an entire pair composed by (k,v) and to access
        # the relative info we do jobvector[0][0] to access the sorting_param directly,
        # and jobvector[0][1] to access the dictionary containing the information
        # about the sorting parameter. The pair is preferred to a dictionary because
        # it is easily iterable when we have a dictionary as a value for our key in the pair.
        jobvector = []
        for k, v in paramdict.items():
            jobvector.append((k, v))

        return jobvector

    def dictionarize(self, cmd, sorting_param=JOBINFO.JOBID):

        # Return the dictionary from a cmd command
        return self.__parsing_pipeline(cmd, sorting_param)

    def __parsing_pipeline(self, cmd, sorting_param):

        # Obtain the vector containing all the parsed tokens from the command
        joblist = self.__to_vector(cmd)

        # Obtain the dictionary parsed by the sorting parameter
        paramdict = self.__to_dict(joblist, sorting_param)

        # Return the built dict
        return paramdict

    def __to_vector(self, cmd):

        # Obtain the command output from the system using subprocess
        output = getoutput(cmd)

        # Split the obtained string by the new line, obtaining a number of element equal
        # to the job active in the system + one more element, representing the info of the
        # system (jobid, partition etc)
        outlist = output.split('\n')

        # Now for each element, we split the string by the space and remove the useless
        # filler to create a row of element of our job info matrix
        joblist = []
        for i in range(len(outlist)):
            joblist.extend([list(filter(('').__ne__, outlist[i].split(' ')))])

        # We then convert our list to a dictionary of user with jobs and their info
        joblist = np.array(joblist)

        # return the vector
        return joblist

    def __to_dict(self, joblist, sorting_param):

        # Empty dictionary
        userdict = {}

        # For the job in the list and for each job its element (jobid, partition, user etc)
        for job in joblist[1:]:
            for i in range(len(job)):

                # If i is not equal to the sorting parameter (ie: 0 is the position in
                # which slurm position the JOBID)
                if i != sorting_param:
                    try:

                        # Try to convert the key to int if possible (i.e: case in which
                        # the sorting param is a numeric one, such as jobid, node etc)
                        key = job[sorting_param]

                        # We do try to update an user job info, so if do not exists
                        # we catch the exception and create a new user with their
                        # associate dictionary.
                        userdict[key][joblist[0,i]] = job[i]

                    except:

                        # If here, that means we had to create a new user. Then
                        # we insert the job info.
                        userdict[key] = {}
                        userdict[key][joblist[0,i]] = job[i]


        # return the created dict
        return userdict

