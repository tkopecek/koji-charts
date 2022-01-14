podman run -d  --privileged \
    --name koji-db-charts \
    -e MYSQL_ROOT_PASSWORD=my-secret-pw \
    -v $DB_DIR:/var/lib/mysql \
    -p 3306:3306 \
    mariadb
