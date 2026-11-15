-- Source initialization for a new Compose volume, not a dump or runtime credential.
\getenv app_password SIGMA_APP_PASSWORD
CREATE ROLE sigma LOGIN PASSWORD :'app_password';
ALTER DATABASE sigma_m3 OWNER TO sigma;
GRANT ALL ON SCHEMA public TO sigma;
