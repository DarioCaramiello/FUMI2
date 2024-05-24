#!/bin/bash

home_container="/home/fumi2/FUMI2"
home_webserv="/home/d.caramiello"
scratch_frontend="/scratch/d.caramiello/tmp"
scratch_frontend_user="$scratch_frontend/usr_fumi_app"
scratch_container_user="$home_container/scratch_user"

# user_key=USER-DATE-ID
# lon=LON
# lat=LAT
# ex 20230303Z00 -- yyyymmggZhh -- param for job
# date=DATe 
# hours=HOURS
# temperature=TEMPERATURE 
# dst_dir=DSTDIR


su fumi2 -c "ssh -o StrictHostKeyChecking=no d.caramiello@frontend \"export PATH=$PATH:/usr/sbin; mkdir -p $scratch_frontend_user/USER/USER-DATE-ID/out; module load slurm; source /home/ccmmma/prometeo/apps/smoketracer/etc/profile; cd /home/ccmmma/prometeo/apps/smoketracer; ./smoketracer LON LAT DATe HOURS TEMPERATURE /scratch/d.caramiello/tmp/USER/USER-DATE-ID/out_job; \" "
# su fumi2 -c "ssh -o StrictHostKeyChecking=no d.caramiello@193.205.230.5 \"mkdir -p $scratch_frontend_user/USER/USER-DATE-ID/out; module load slurm; source /home/ccmmma/prometeo/apps/smoketracer/etc/profile; cd /home/ccmmma/prometeo/apps/smoketracer; ./smoketracer LON LAT DATe HOURS TEMPERATURE /scratch/d.caramiello/tmp/USER/USER-DATE-ID/out_job; \" "
# su fumi2 -c "ssh -o StrictHostKeyChecking=no d.caramiello@193.205.230.5 \"mkdir $scratch_frontend_user/$user_key; module load slurm; source /home/ccmmma/prometeo/apps/smoketracer/etc/profile; cd /home/ccmmma/prometeo/apps/smoketracer; ./smoketracer LON LAT DATe HOURS TEMPERATURE /scratch/d.caramiello/tmp/USER-DATE-ID/out_job &; \" &"
