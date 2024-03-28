#!/bin/bash

home_container="/home/fumi2/FUMI2"
home_webserv="/home/d.caramiello"
scratch_frontend="/scratch/d.caramiello/tmp"
scratch_frontend_user="$scratch_frontend/usr_fumi_app"
scratch_container_user="$home_container/scratch_user"
smokertracer_path="/home/ccmmma/prometeo/apps/smoketracer"

user_key=USER-DATE-ID
lon=LON
lat=LAT
# ex 20230303Z00 -- yyyymmggZhh -- param for job
date=DATe 
hours=HOURS
temperature=TEMPERATURE 
dst_dir=DSTDIR


su fumi2 
ssh d.caramiello@193.205.230.5 "mkdir $scratch_frontend_user/$user_key; mkdir $scratch_frontend_user/$user_key/$user_key;"

# module load slurm; source $smoketracer_path/etc/profile; cd $smoketracer_path; ./smoketracer $lon $lat $date $hours $temperature $scratch_frontend_user/$user_key/out_job;" 

