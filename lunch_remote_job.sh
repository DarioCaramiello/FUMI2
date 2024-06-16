#!/bin/bash

# storage="/storage/ccmmma/prometeo/data/opendap/pippo/smoketracer"
storage="/scratch/d.caramiello/tmp"
dir_smoketracer_frontend="/home/ccmmma/prometeo/apps/smoketracer"

su fumi2 -c "ssh -o StrictHostKeyChecking=no d.caramiello@193.205.230.5 \"export PATH=$PATH:/usr/sbin; mkdir -p $storage/USER/USER-DATE-ID/out; module load slurm; source $dir_smoketracer_frontend/etc/profile; cd $dir_smoketracer_frontend; ./smoketracer LON LAT DATe HOURS TEMPERATURE $storage/USER/USER-DATE-ID; \" " &


