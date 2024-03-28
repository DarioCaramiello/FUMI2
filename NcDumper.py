import requests
import datetime
import wget
import sys
import os

# dove prendere i dati da locale /storage/ccmmma/prometeo/data/opendap/wrf5/d03/history [webserv] [frontend ] [ condiviso storage]

class NCODump():
    
    def __init__(self):
        self.__apiurl = "https://api.meteo.uniparthenope.it/products/wrf5/com63049/avail?date="
        self.__server_address = "193.205.230.6"

    # Simple function that transform an integer based on its value
    def transform_integer(self, num):
        num = int(num)
        if num < 10:
            return "0" + str(num)
        else:
            return str(num)

    
    def add_hour_to_date(self, date_str, hour):
        
        # Parse the input date string and hour
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d %H')
        hour_delta = datetime.timedelta(hours=hour)

        # Add the hour to the date
        new_date = date + hour_delta
        
        # Check if the new hour exceeds 23 hours
        if new_date.hour > 23:
            
            # Increment the day by 1
            new_date += datetime.timedelta(days=1)
            
            # Check if the new day exceeds the total days in the month
            if new_date.day > (datetime.date(new_date.year, new_date.month+1, 1) - datetime.timedelta(days=1)).day:

                # Increment the month by 1 and set the day to 1
                new_date = new_date.replace(day=1, month=new_date.month+1)
                
                # Check if the new month exceeds 12
                if new_date.month > 12:
                
                    # Increment the year by 1 and set the month to 1
                    new_date = new_date.replace(month=1, year=new_date.year+1)

        return new_date.strftime('%Y-%m-%d %H')
    

    def dump(self, date, start, duration, output_directory=None):
        
        # Init variables:
        # Date in list format [Y, M, D]
        datesplit = date.split('-')

        # Date in string format YMD without formatter
        datejoin = "".join(date.split('-'))

        # Current hour is the midnight
        current_hour = self.transform_integer("00")

        # Date str is the initial date starting at midnight: I.e: 2023-04-23 00
        date_str = date + " " + "00"

        # Limit exceed is used to control if we're going out of date boundary 
        limit_exceed = False

        # Url list store the wget urls 
        url_list = []

        # We determine the range in which the file needs to be downloaded.
        # I.e: if the start hour is 15 and the duration is 3, we need to go from 15 to 18.
        # BUT, we also need to download the files starting from the midnight of that very day:
        # So we download data from 0 to 18. 
        # The only limit case we need to handle is if the start is 23 and the duration is 1:
        # in this case, the span is just the 00-23 (24 hours totally).
        # Otherwhise, the span is given by start + duration (i.e: start = 15, duration = 3: 
        # Span is 15+3->18.
        span = int(start) + int(duration)

        # For the start+duration span 
        for i in range(0, span):

            # If i is equal to 24 (case which start is 23 and duration is 1) we break
            # since there is no 24 in the api 
            if i == 24: 
                break 

            # We fetch the request 
            search_date = datejoin + "Z{}".format(current_hour)
            local_url = self.__apiurl + search_date
            
            # We get the request avail
            print("Hour: {} ------------------------".format(current_hour)) 
            print(local_url)
            r = requests.get(local_url).json()
            print(r)
            print("-----------------------------")

            # Check if the request is empty. If so, we exceeded the limit since the result 
            # is not available yet. 
            if (len(r["avail"]) == 0):
                limit_exceed = True
                break

            # If not, we get domain elements
            domain = r["avail"][0]["domain"]
            prod = r["avail"][0]["prod"]

            path_data = "{}/{}/history/{}/{}/{}/{}_{}_{}Z{}00.nc".format(prod,
                                                                          domain,
                                                                          datesplit[0],
                                                                          datesplit[1],
                                                                          datesplit[2],
                                                                          prod,
                                                                          domain,
                                                                          datejoin,
                                                                          current_hour
                                                                          )

            print("------- file_data : " + path_data, flush=True)

            # Then proceed to build the server link to fetch the file from
            wget_url = "http://{}/files/{}/{}/history/{}/{}/{}/{}_{}_{}Z{}00.nc".format(
                self.__server_address,
                prod,
                domain,
                datesplit[0],
                datesplit[1],
                datesplit[2],
                prod,
                domain,
                datejoin,
                current_hour
            )

            # We append the url to the list
            url_list.append(wget_url)

            print("---- wget_url : " + wget_url, flush=True)

            # We now do some check on the date, to switch day/month/year if needed
            # print(date_str, flush=True)
            date_str = self.add_hour_to_date(date_str, 1)

            # We now extract from date_str (Y-M-D H) the datesplit (YMD) format and assign it
            datejoin = "".join(date_str.split("-")).split(" ")[0]

            # And the list of Y,M,D for next iteration. We also split the hour from the last element
            datesplit = date_str.split('-')
            datesplit[2] = datesplit[2].split(' ')[0]

            # We assign the increased curhour using the info fetched from the func add hour to date
            current_hour = "".join(date_str.split("-")).split(" ")[1]

        # If we exceeded the date limit, we do return -1 to inform that the date interval is incorrect
        if limit_exceed:
            return -1
        
        # We do check output directory: if its none, we just wanted to check if all the files are available
        # for the download (constraint check) so we return 1 as success
        if output_directory is None: 
            return 1
        
        # OUTPUT info for outfile in sbatch
        print("LIMIT OK")

        # Now, for each link of the url list we download the file into a folder
        download_error = False
        for url in url_list:

            try:
                file = wget.download(url, out=output_directory)
                # OUTPUT info for outfile in sbatch
                print("{} DOWNLOADED".format(file))
            except:
                download_error = True
                break

        # If an error has been encountered during the download of the files, return 0 code
        if download_error:
            # OUTPUT info for outfile in sbatch
            print("ERROR IN DOWNLOAD")
            return -2
        
        # OUTPUT info for outfile in sbatch
        print("DOWNLOAD OK")
        
        # Write a file into the directory 
        filename = "DUMPOK"

        # Create the full filepath
        filepath = os.path.join(output_directory, filename)

        # Create the file
        with open(filepath, 'w') as f:
            pass  # do nothing

        # If all files has been downloaded correctly, we concat them in a single file 
        return 1
        