# CosmiCenter — Put it online on Ubuntu (quick guide)

**Goal:** your site running on an Ubuntu server, with HTTPS, automatic start, and nightly backups.
**What you do:** about 5 commands. **What the script does:** everything else.

> You do **not** need to install anything by hand. The script installs Python, PostgreSQL, Nginx and the HTTPS certificate for you.

---

## What you need before starting

| Item | Details |
|---|---|
| An Ubuntu server | **22.04 or 24.04**, at least 1 CPU, 2 GB RAM, 20 GB disk. Any provider works (OVH, Hetzner, DigitalOcean, a VM in your company...). |
| SSH access | A user that can use `sudo`. |
| A domain name *(recommended)* | Example `support.mycompany.com`, with its **A record pointing to the server's IP**. Without a domain the site works over plain HTTP using the IP address. |
| Your project | It is on GitHub, or you can copy it with `scp`. |

---

## Step 0 — Get an Ubuntu Server and connect to it

**Option A — Rent a server (easiest, recommended).**
Choose *Ubuntu 24.04 LTS* (or 22.04 LTS) when creating it at your provider (Hetzner, OVH, DigitalOcean...). It is installed for you; you receive an **IP address** and a login (user + password, or an SSH key).

**Option B — Install it yourself on a spare computer.**
1. Download *Ubuntu Server 24.04 LTS* from ubuntu.com and write it to a USB stick (tool: *Rufus*).
2. Boot the computer from the USB stick and follow the installer: keep the defaults, **tick "Install OpenSSH server"**, create your user, and skip the optional extra packages.
3. After the reboot, note the computer's IP address: log in on its screen and run `hostname -I`.
4. Give that IP a fixed address in your router (so it never changes).

**Connect from your Windows PC.** Open **PowerShell** and type:

```powershell
ssh your-user@SERVER_IP
```

Answer `yes` the first time and type your password. You are now typing commands *on the server*. Type `exit` to disconnect.

Everything below happens in that window unless a step says "on your PC".

---

## Step 1 — (Only if you want to keep your current data) Export from your Windows PC

Skip this step to start with an empty site.

Open **PowerShell** in your project folder:

```powershell
# 1) Database  (replace USER and DBNAME with the values from your .env DATABASE_URL)
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U USER -d DBNAME --no-owner --no-acl -f cosmicenter.sql

# 2) Uploaded files (ticket attachments, photos, chat files)
tar -czf uploads.tar.gz static/uploads instance/chat_files
```

Also copy the **`SECRET_KEY=` line** from your current `.env` (only needed if you stored AnyDesk/TeamViewer passwords).

---

## Step 2 — Get the project onto the server

Connect to the server, then pick **one** option:

```bash
ssh your-user@SERVER_IP

# Option A: from GitHub
git clone https://github.com/YOUR-ACCOUNT/YOUR-REPO.git cosmicenter-src

# Option B: from your PC (run this on your PC, not on the server)
#   scp -r C:\Users\hassen.abdeli\Documents\GitHub\CosmittoHUB your-user@SERVER_IP:~/cosmicenter-src
```

If you did Step 1, upload the two files too (run on your PC):

```powershell
scp cosmicenter.sql uploads.tar.gz your-user@SERVER_IP:~/
```

---

## Step 3 — Run the installer (the "one click")

```bash
cd ~/cosmicenter-src
sudo bash deploy/install.sh
```

It asks 5 short questions (press **Enter** to skip any):

1. **Domain name** → `support.mycompany.com` (empty = use the IP over HTTP)
2. **Your e-mail** → used for the free HTTPS certificate
3. **Database file** → `/home/your-user/cosmicenter.sql` (empty = fresh database)
4. **Old SECRET_KEY** → paste it if you answered 3 (empty = new key)
5. **Uploads archive** → `/home/your-user/uploads.tar.gz` (empty = none)

Then wait 3–6 minutes. It prints **✔ TERMINÉ** when finished.

> On an Ubuntu **Desktop** you can also right-click `deploy/install.sh` → *Run as a Program*, but a server has no desktop, so the command above is the normal way.

---

## Step 4 — First login

- Open `https://your-domain` (or `http://SERVER_IP`).
- **If you restored your database:** log in with your usual accounts.
- **If you started with an empty database:** the admin password was generated for you:
  ```bash
  sudo cat /root/cosmicenter-first-login.txt
  ```
  Log in as `admin@example.com`, **change the password immediately**, then delete the file: `sudo rm /root/cosmicenter-first-login.txt`.
- Go to **Administration → Paramètres Système**, enter your SMTP e-mail settings, then click **Envoyer un e-mail de test**.

> Restoring your own database is the better choice: your roles and permissions then match exactly what you use today.

---

## Daily life

| I want to... | Command (on the server) |
|---|---|
| **Update the site** after you changed the code | `cd ~/cosmicenter-src && git pull && sudo bash deploy/install.sh` (no questions asked, your data is never touched) |
| See if it is running | `sudo systemctl status cosmicenter` |
| Restart it | `sudo systemctl restart cosmicenter` |
| Read the app messages | `sudo journalctl -u cosmicenter -n 100 --no-pager` (or **Logs Système** inside the site) |
| Make a backup now | `sudo cosmicenter-backup` |
| Find backups | `/var/backups/cosmicenter/` (made **every night at 02:30**, 14 days kept) |
| Change settings (`SECRET_KEY`, e-mail...) | `sudo nano /opt/cosmicenter/.env` then `sudo systemctl restart cosmicenter` |

**Download a backup to your PC** (run on your PC): `scp your-user@SERVER_IP:/var/backups/cosmicenter/db-*.sql.gz .` — keep copies off the server too.

**Restore a backup:** `gunzip -c db-DATE.sql.gz | sudo -u postgres psql cosmicenter` after `sudo systemctl stop cosmicenter`, then start it again.

---

## If something goes wrong

| Problem | What to do |
|---|---|
| `bash: $'\r': command not found` | The file has Windows line endings: `sed -i 's/\r$//' deploy/*.sh` then run again. |
| Installer stops with a red message | Read it, fix it, and **run the same command again** — it is safe to re-run. |
| "Certificate could not be obtained" | The domain does not point to the server yet. Wait for DNS, then: `sudo certbot --nginx -d your-domain`. The site works over HTTP meanwhile. |
| The site shows **502 Bad Gateway** | The app is down: `sudo journalctl -u cosmicenter -n 50 --no-pager`. |
| E-mails are not sent | Use **Envoyer un e-mail de test**. Gmail / Microsoft 365 need an *app password* and SMTP authentication enabled. |
| Cannot upload large files | The limit is 50 MB (already set in Nginx). |
| Locked out after 7 wrong passwords | Normal: wait 30 minutes, or an admin clicks **Réactiver** on your account. |

---

## What the installer set up (for your information)

- App in `/opt/cosmicenter`, running as a dedicated non-admin user, started by **systemd**, restarted automatically if it crashes or the server reboots.
- **PostgreSQL** database `cosmicenter` with a random password (stored only in `/opt/cosmicenter/.env`, readable by the app only).
- **Nginx** in front (HTTPS, 50 MB uploads). The app itself listens only on `127.0.0.1:8080`, never on the internet.
- **Firewall (UFW):** only SSH, 80 and 443 are open. The database is not reachable from outside.
- **HTTPS** via Let's Encrypt, renewed automatically.
- **Backups** every night (database + uploaded files).
- Not copied to the server on purpose: your Excel/CSV staff files and `seed_db.py` (it wipes the whole database).

## Security checklist before announcing the site

- [ ] You changed the first admin password.
- [ ] No account still uses a default or demo password.
- [ ] SSH uses a key (not just a password): `man ssh-copy-id`.
- [ ] You downloaded one backup to your PC and tested that it opens.
