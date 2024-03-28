#!/usr/bin/expect

set password "amsterdam2017"
set timeout 18000

set home_container "/home/fumi2/FUMI2"
set home_webserv "/home/d.caramiello"
set scratch_frontend "/scratch/d.caramiello/tmp"
set scratch_frontend_user "$scratch_frontend/usr_fumi_app"
set scratch_container_user "$home_container/scratch_user"
set smokertracer_path "/home/ccmmma/prometeo/apps/smoketracer"


set user_key USER-DATE-ID
set lon LON
set lat LAT
# ex 20230303Z00 -- yyyymmggZhh -- param for job
set date DATe 
set hours HOURS
set temperature TEMPERATURE 
set dst_dir DSTDIR



# per testare : 
# cartella tmp dell'user creata nello /scratch/d.caramiello/tmp/user_fumi2
# cartella out job lanciato user : /scratch/d.caramiello/tmp/user_fumi2/key_user_unique/out_job
# per produzione
# /scratch/ccmmma/tmp
# /storage/ .... 

spawn ssh -i /home/fumi2/.ssh/id_rsa d.caramiello@193.205.230.6
expect {
    "Are you sure you want to continue connecting" {
        send "yes\r"
        exp_continue
    }
    "Enter passphrase for key " {
        send "$password\r"
        exp_continue
    }
    "$ " {
        send "ssh frontend\r"
        send "cd $scratch_frontend_user\r"
        send "mkdir $user_key\r"
        send "cd $user_key\r"
        send "mkdir out_job\r"
        send "cd $smokertracer_path\r"
        send "module load slurm\r"
        send "source $smokertracer_path/etc/profile\r"
        send "./smoketracer $lon $lat $date $hours $temperature $scratch_frontend_user/$user_key/out_job\r"

        expect {
            "Workflow 'smoketracer' completed" {
                send_user "Il comando 'smoketracer' è stato completato con successo\n"
            }
            timeout {
                send_user "Timeout: Il comando 'smoketracer' non è stato completato entro il tempo massimo\n"
            }
            eof {
                send_user "Connessione chiusa inaspettatamente\n"
            }
        }
    }
}

# elimino nel container il file personalizzato per creare dir user e lanciare job con paramtri dell'user 
exec rm $home_container/tmpgen_runjob.sh
# creo il file di default 
exec mv $home_container/tmpgen_runjob_var.sh $home_container/tmpgen_runjob.sh

# copio la cartella dell'utente con i risultati da frontend a webserv 
spawn ssh -i /home/fumi2/.ssh/id_rsa d.caramiello@193.205.230.6
expect {
    "Are you sure you want to continue connecting" {
        send "yes\r"
        exp_continue
    }
    "Enter passphrase for key " {
        send "$password\r"
        exp_continue
    }
    "$ " {
        send "scp -r d.caramiello@frontend:$scratch_frontend_user/$user_key $home_webserv\r"
    }
}

exec mkdir $home_container/static/KML/$user_key-out

# copio la cartella dell'utente con i risultati da webserv a container 

spawn scp -r -i /home/fumi2/.ssh/id_rsa d.caramiello@193.205.230.6:$home_webserv/$user_key/out_job $home_container/static/KML/$user_key-out
expect {
    "Are you sure you want to continue connecting" {
        send "yes\r"
        exp_continue
    }
    "Enter passphrase for key " {
        send "$password\r"
        exp_continue
    }
}

# exec mv $scratch_container_user/$user_key/out_job/$date.kml $home_container/static/KML/$user_key-out
# exec mv $scratch_container_user/$user_key/out_job/\*.kml $home_container/static/KML/$user_key-out
# exec echo ls $scratch_container_user/$user_key/out_job/ > $home_container/outls.txt
# expect eof 
# exec find $scratch_container_user/$user_key/out_job/ -type f -name "*.kml" -exec mv {} $home_container/static/KML/$user_key-out \;
# exec rm -r $scratch_container_user/$user_key

# elimino cartella dell'utente da webserv
spawn ssh -i /home/fumi2/.ssh/id_rsa d.caramiello@193.205.230.6 rm -r $home_webserv/$user_key
expect {
    "Are you sure you want to continue connecting" {
        send "yes\r"
        exp_continue
    }
    "Enter passphrase for key " {
        send "$password\r"
        exp_continue
    }
}