cd companies_act_2013
..\.venv\Scripts\python.exe app.py  


cd companies_act_2013\governance_db; C:\Users\kalid\OneDrive\Documents\RAG\.venv\Scripts\python.exe setup.py



aryavarmma@Aryaditi2005:~$ docker run --name pg-db \
  --network pg-net \
  -e POSTGRES_USER=arya \
  -e POSTGRES_PASSWORD=secret123 \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  -d postgres:16
506c4d15705dc72bdc9bb9d9baa0dc5a064f893f2f7cb8635f67f5111a9c6751
aryavarmma@Aryaditi2005:~$ docker run --name pgadmin \
  --network pg-net \
  -e PGADMIN_DEFAULT_EMAIL=arya@gmail.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin123 \
  -p 5050:80 \
  -d dpage/pgadmin4
d4dc786fae71e52d3cfbdcb250fa196c665718a0ff9f9b7f4690dbc933ded206
aryavarmma@Aryaditi2005:~$ docker ps
CONTAINER ID   IMAGE            COMMAND                  CREATED         STATUS         PORTS                                         NAMES
d4dc786fae71   dpage/pgadmin4   "/entrypoint.sh"         4 seconds ago   Up 3 seconds   0.0.0.0:5050->80/tcp, [::]:5050->80/tcp       pgadmin
506c4d15705d   postgres:16      "docker-entrypoint.s…"   7 seconds ago   Up 6 seconds   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp   pg-db
aryavarmma@Aryaditi2005:~$