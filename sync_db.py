import os
import subprocess
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Define paths
PG_BIN_DIR = r"D:\Program Files\PostgreSQL\18\bin"
PG_DUMP_PATH = os.path.join(PG_BIN_DIR, "pg_dump.exe")
PSQL_PATH = os.path.join(PG_BIN_DIR, "psql.exe")

def read_env(env_path=".env"):
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip('"').strip("'")
    return env_vars

def write_env(env_vars, env_path=".env"):
    with open(env_path, "w", encoding="utf-8") as f:
        for key, val in env_vars.items():
            f.write(f'{key}="{val}"\n')

def main():
    print("=== DONG BO CLOUD DATABASE (AIVEN) VE LOCAL DATABASE ===")
    
    # 1. Read .env file
    env = read_env()
    aiven_url = env.get("DATABASE_URL")
    schema_name = env.get("SCHEMA_NAME", "demo")
    
    if not aiven_url:
        print("Loi: Khong tim thay DATABASE_URL trong file .env!")
        sys.exit(1)
        
    print(f"Cloud DB URL: {aiven_url}")
    print(f"Schema: {schema_name}")
    
    # 2. Ask local DB info
    local_host = input("Nhap Local DB Host [localhost]: ").strip() or "localhost"
    local_port = input("Nhap Local DB Port [5432]: ").strip() or "5432"
    local_user = input("Nhap Local DB User [postgres]: ").strip() or "postgres"
    local_pass = input("Nhap Local DB Password: ").strip()
    local_db = input("Nhap Local DB Name [itss_japanese]: ").strip() or "itss_japanese"
    
    # 3. Test local connection & Create DB if not exists
    print("\n[1/4] Dang ket noi toi PostgreSQL local de kiem tra...")
    try:
        conn = psycopg2.connect(
            host=local_host,
            port=local_port,
            user=local_user,
            password=local_pass,
            database="postgres"  # connect to default db first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (local_db,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"-> Co so du lieu '{local_db}' chua ton tai. Dang khoi tao...")
            cursor.execute(f'CREATE DATABASE "{local_db}"')
            print(f"-> Da tao database '{local_db}' thanh cong.")
        else:
            print(f"-> Co so du lieu '{local_db}' da ton tai.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Loi: Khong the ket noi hoac khoi tao DB local: {e}")
        sys.exit(1)

    # 4. Dump data from Aiven
    print("\n[2/4] Dang sao luu (dump) du lieu tu Aiven Cloud...")
    dump_file = "aiven_dump.sql"
    
    try:
        # Aiven dump cmd
        cmd_dump = [
            PG_DUMP_PATH,
            f"--dbname={aiven_url}",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--format=plain",
            f"--file={dump_file}"
        ]
        
        # Run process
        result = subprocess.run(cmd_dump, capture_output=True, text=True, check=True)
        print("-> Da trich xuat du lieu thanh cong.")
    except subprocess.CalledProcessError as e:
        print(f"Loi khi chay pg_dump: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"Loi he thong khi chay pg_dump: {e}")
        sys.exit(1)

    # 5. Restore data to local DB
    print("\n[3/4] Dang nhap (restore) du lieu vao Local Database...")
    local_url = f"postgresql://{local_user}:{local_pass}@{local_host}:{local_port}/{local_db}"
    
    # Set local password for psql tool
    env_vars = os.environ.copy()
    env_vars["PGPASSWORD"] = local_pass
    
    try:
        # Before restoring, we should ensure the schema exists, since pg_dump with --clean might drop it or not create it.
        conn = psycopg2.connect(
            host=local_host,
            port=local_port,
            user=local_user,
            password=local_pass,
            database=local_db
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        cursor.close()
        conn.close()

        # Run psql
        cmd_restore = [
            PSQL_PATH,
            f"--dbname={local_url}",
            f"--file={dump_file}"
        ]
        
        result = subprocess.run(cmd_restore, env=env_vars, capture_output=True, text=True, check=True)
        print("-> Dang nhap du lieu vao database local thanh cong.")
    except subprocess.CalledProcessError as e:
        # Print warning if any but keep going (since psql might complain about dropping non-existent elements first time)
        print(f"Luu y khi psql restore:\n{e.stderr}")
    except Exception as e:
        print(f"Loi he thong khi chay psql restore: {e}")
        sys.exit(1)
        
    # Clean temporary dump file
    if os.path.exists(dump_file):
        os.remove(dump_file)

    # 6. Update .env file
    print("\n[4/4] Dang cap nhat file .env de ket noi database local...")
    env["DATABASE_URL"] = local_url
    write_env(env)
    print("-> Da cap nhat file .env thanh cong.")
    
    print("\n=== HOAN TAT! ===")
    print("Bay gio ban da chuyen sang su dung database local.")
    print("Ban co the chay lai du an voi: python app.py")

if __name__ == "__main__":
    main()
