#!/bin/bash

scratch_frontend="/scratch/d.caramiello/tmp"
dir_smoketracer_frontend="/home/ccmmma/prometeo/apps/smoketracer"

su fumi2 -c "ssh -o StrictHostKeyChecking=no d.caramiello@193.205.230.5 \"export PATH=$PATH:/usr/sbin; mkdir -p $scratch_frontend/USER/USER-DATE-ID/out; module load slurm; source $dir_smoketracer_frontend/etc/profile; cd $dir_smoketracer_frontend; ./smoketracer LON LAT DATe HOURS TEMPERATURE $scratch_frontend/USER/USER-DATE-ID; \" "
