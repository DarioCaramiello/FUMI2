import requests


class DagonOnServiceManager():
    
    url_status = None
    workflow = None
    tot_jobs = None

    def __init__(self, url_stauts, workflow, tot_jobs):
        self.url_status = url_stauts
        self.workflow = workflow
        self.tot_jobs = tot_jobs

    def get_request(self):
        response = requests.get(self.url_status)
        status_workflow = {}
        if response.status_code == 200:
            data = response.json()
            for i in range(self.tot_jobs):
                status_workflow[self.workflow[i]] = data[0]['tasks'][self.workflow[i]]['status']
            return status_workflow      
        else:
            return False
