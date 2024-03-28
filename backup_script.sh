#!/bin/bash

DB_NAME="citizix_db"
BACKUP_DIR="/FUMI2/backup_db_postgres/backup"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/$DB_NAME\_backup_$DATE.sql"

if [ -e "$BACKUP_FILE" ]; then
  echo "Il file di backup esiste già. Scegliere un altro percorso o nome di file."
else
  pg_dump -U citizix_user -h localhost -d $DB_NAME -F c -b -v -f $BACKUP_FILE
  echo "Backup completato con successo."
fi


