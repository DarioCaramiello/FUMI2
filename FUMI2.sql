BEGIN TRANSACTION;


CREATE TABLE "USER" (
    USERNAME TEXT PRIMARY KEY NOT NULL,
    "PASSWORD" TEXT, 
    FIRSTNAME TEXT NOT NULL, 
    LASTNAME TEXT NOT NULL, 
    EMAIL TEXT NOT NULL,
    TELEPHONE TEXT,
    BIRTHDATE TEXT,
    LASTACCESS TEXT,
    STRUTTURA TEXT,
    RUOLOTEC TEXT,
    "ROLE" INT,
    ACTIVE INT
);

CREATE TABLE SIMULAZIONE (
    NUMEROSIM SERIAL PRIMARY KEY,
    AREA TEXT,
    "DATE" DATE,
    ORAINIZIO TIME,
    TEMPERATURA NUMERIC(5,2),
    LONGITUDINE NUMERIC(9,6),
    LATITUDINE NUMERIC(8,6),
    DURATA INTERVAL,
    STATOFINALE BOOLEAN,
    USERSIM TEXT REFERENCES "USER"(USERNAME)
);


CREATE TABLE JOBS (
    -- JOBID INT PRIMARY KEY NOT NULL,
    JOBID TEXT PRIMARY KEY NOT NULL,
    USERNAME TEXT NOT NULL, 
    FOREIGN KEY (USERNAME) REFERENCES "USER" (USERNAME) ON DELETE CASCADE
);


CREATE TABLE JOBIDENTIFIER (
    JOBID TEXT PRIMARY KEY NOT NULL,
    "DATE" DATE,
    "TIME" TEXT,
    "PATH" TEXT,
    FOREIGN KEY (JOBID) REFERENCES JOBS (JOBID) ON DELETE CASCADE
);

/*
CREATE TABLE JOBINFO (
    JOBID TEXT PRIMARY KEY NOT NULL,
    AREA TEXT NOT NULL,
    "DATE" DATE NOT NULL,
    "TIME" TEXT NOT NULL,
    DURATION NUMERIC()
)


CREATE TABLE JOBIDENTIFIER (
    -- JOBID INT PRIMARY KEY NOT NULL,
    JOBID TEXT PRIMARY KEY NOT NULL,
    "DATE" TEXT,
    "TIME" TEXT,
    "PATH" TEXT,
    FOREIGN KEY (JOBID) REFERENCES JOBS (JOBID) ON DELETE CASCADE
);


CREATE TABLE JOBINFO (
    -- JOBID INT PRIMARY KEY NOT NULL,
    JOBID TEXT PRIMARY KEY NOT NULL,
    AREA TEXT NOT NULL, 
    "DATE" TEXT NOT NULL, 
    "TIME" TEXT NOT NULL, 
    DURATION TEXT NOT NULL, 
    LONG TEXT NOT NULL, 
    LAT TEXT NOT NULL, 
    TEMPERATURE TEXT NOT NULL, 
    METEODATA TEXT NOT NULL,
    COMPLETED INT NOT NULL,
    FOREIGN KEY (JOBID) REFERENCES JOBS (JOBID) ON DELETE CASCADE
);
*/


INSERT INTO "USER" (USERNAME, "PASSWORD", FIRSTNAME, LASTNAME, EMAIL, TELEPHONE, BIRTHDATE, LASTACCESS, "ROLE", ACTIVE) VALUES ('admin', 'pbkdf2:sha256:260000$9TWmqDomDHCZO8B3$19cef8898494e2b04e9b970aadb037bd09ffa30680cf6291223a8466d02c8367', 'Dario', 'Caramiello', 'dario@example.com', '123456789', '1990-01-01', '2022-01-01', 1, 1);

INSERT INTO "USER" (USERNAME, "PASSWORD", FIRSTNAME, LASTNAME, EMAIL, TELEPHONE, BIRTHDATE, LASTACCESS, "ROLE", ACTIVE) VALUES ('user', 'pbkdf2:sha256:260000$9TWmqDomDHCZO8B3$19cef8898494e2b04e9b970aadb037bd09ffa30680cf6291223a8466d02c8367', 'user', 'user', 'user-mail', '123456789', '1990-01-01', '2022-01-01', 0, 1);

CREATE EXTENSION postgis;

COMMIT;
