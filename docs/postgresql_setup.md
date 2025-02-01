# PostgreSQL and User Management Setup Guide

This guide covers setting up PostgreSQL on an Ubuntu server and managing users through the CLI.

## Prerequisites

1. Install Python dependencies and development tools:
```bash
sudo apt update
sudo apt install python3-pip python3-dev libpq-dev build-essential
```

2. Upgrade pip to the latest version:
```bash
pip install --upgrade pip
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

## PostgreSQL Installation and Setup

1. Update the package list and install PostgreSQL:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

2. Verify the installation:
```bash
sudo systemctl status postgresql
```

3. PostgreSQL creates a default user 'postgres'. Switch to this user:
```bash
sudo -i -u postgres
```

## Database Setup

1. Create a new database user (while logged in as postgres user):
```bash
createuser --interactive --pwprompt
```
Enter the following when prompted:
- Name of role to add: pokeapi
- Password for new role: [enter a secure password]
- Shall the new role be a superuser? No
- Shall the new role be allowed to create databases? Yes
- Shall the new role be allowed to create more new roles? No

2. Create the database:
```bash
createdb pokeapi
```

3. Exit the postgres user:
```bash
exit
```

## Configure PostgreSQL Access

1. Edit the PostgreSQL client authentication configuration:
```bash
sudo nano /etc/postgresql/[version]/main/pg_hba.conf
```
Add this line under IPv4 local connections (replace [your-ip] with your server's IP):
```
host    pokeapi         pokeapi         [your-ip]/32         md5
```

2. Edit PostgreSQL configuration to allow remote connections:
```bash
sudo nano /etc/postgresql/[version]/main/postgresql.conf
```
Update the listen_addresses line:
```
listen_addresses = '*'
```

3. Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## Environment Setup

1. Update the .env file on your server with the correct database URL:
```bash
DATABASE_URL=postgresql://pokeapi:[password]@localhost/pokeapi
```
Replace [password] with the password you set for the pokeapi user.

2. Generate a secure SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

3. Add the generated key to your .env file:
```bash
SECRET_KEY="your-generated-key"
```

## Database Migrations

1. Initialize the database migrations:
```bash
flask db init
```

2. Create the initial migration:
```bash
flask db migrate -m "Initial migration"
```

3. Apply the migrations:
```bash
flask db upgrade
```

## User Management CLI Commands

The application provides a command-line interface for managing users. Make the management script executable:
```bash
chmod +x manage.py
```

### Available Commands

1. Create a new user:
```bash
./manage.py create-user [--admin]
```
Options:
- `--admin`: Flag to create an admin user
You will be prompted for:
- Username
- Email
- Password (hidden input with confirmation)

2. List all users:
```bash
./manage.py list-users
```
Shows a table with:
- Username
- Email
- Admin status
- Creation date

3. Update an existing user:
```bash
./manage.py update-user USERNAME [OPTIONS]
```
Options:
- `--email`: New email address
- `--password`: New password
- `--admin`: Set admin status (True/False)

4. Delete a user:
```bash
./manage.py delete-user USERNAME
```

### Examples

1. Create an admin user:
```bash
./manage.py create-user --admin
```

2. Update user's email:
```bash
./manage.py update-user admin --email new@example.com
```

3. Change user's password:
```bash
./manage.py update-user admin --password
```

4. Make a user an admin:
```bash
./manage.py update-user username --admin True
```

## Security Best Practices

1. Firewall Configuration:
```bash
sudo ufw allow from [your-ip] to any port 5432
```

2. Regular Backups:
```bash
# Create a backup
pg_dump pokeapi > backup.sql

# Restore from backup if needed
psql pokeapi < backup.sql
```

3. Monitor PostgreSQL logs:
```bash
sudo tail -f /var/log/postgresql/postgresql-[version]-main.log
```

## Production Considerations

1. Set up SSL for PostgreSQL:
```bash
# Generate SSL certificate
sudo openssl req -new -x509 -days 365 -nodes -text -out /etc/postgresql/[version]/main/server.crt \
  -keyout /etc/postgresql/[version]/main/server.key -subj "/CN=dbhost"
sudo chmod 600 /etc/postgresql/[version]/main/server.key
sudo chown postgres:postgres /etc/postgresql/[version]/main/server.{crt,key}
```

2. Enable SSL in postgresql.conf:
```
ssl = on
ssl_cert_file = '/etc/postgresql/[version]/main/server.crt'
ssl_key_file = '/etc/postgresql/[version]/main/server.key'
```

3. Update DATABASE_URL to use SSL:
```bash
DATABASE_URL=postgresql://pokeapi:[password]@localhost/pokeapi?sslmode=require
```

## Maintenance Tasks

1. Regular updates:
```bash
sudo apt update
sudo apt upgrade postgresql postgresql-contrib
```

2. Database maintenance:
```bash
# Vacuum the database
sudo -u postgres psql -d pokeapi -c "VACUUM ANALYZE;"
```

3. Monitor disk space:
```bash
df -h /var/lib/postgresql
```

## Troubleshooting

1. Connection issues:
```bash
# Test PostgreSQL connection
psql -U pokeapi -h localhost pokeapi

# Check PostgreSQL status
sudo systemctl status postgresql

# View recent logs
sudo tail -f /var/log/postgresql/postgresql-[version]-main.log
```

2. Permission issues:
```bash
# Check user permissions
sudo -u postgres psql -c '\du'

# Reset user password if needed
sudo -u postgres psql -c "ALTER USER pokeapi WITH PASSWORD 'new_password';"
```

3. Database migration issues:
```bash
# Check migration status
flask db current

# Reset migrations
flask db stamp head
```

Remember to replace placeholders like [version], [your-ip], and [password] with your actual values. 