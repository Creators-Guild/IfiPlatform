# Docker servers (Claude plan)

Last updated: 2026-10-13

Working plan for running the site with Docker on the servers: the Halloween mock site
first, the real site later. Delete this file when phase 2 is deployed.

---

## 1. Why we are doing this

Today, getting the website onto a new server is a long manual job.
`docs/operations/server_setup.md` has about 12 steps: install Python, install PostgreSQL,
install Nginx, get an HTTPS certificate, copy config files into the right places, and so on.
Every step is a chance to make a mistake, and the next person who looks after the site
has to learn all of it.

**The goal:** set up a new server in about 5 steps:

1. Install Docker.
2. Download the code (`git clone`).
3. Fill in one settings file (`.env`).
4. Point the domain name at the server.
5. Run one script.

We'll use this new setup in two places, in this order:

| When | What | Data |
|---|---|---|
| **Now, before Oct 19** | A **Halloween mock site** for the commit event, on its own new server | Fake data from `seed_dev_data` |
| **After the event** | The **real site** (ifiplattform.no) moves over to the same setup | Real data, restored from a backup |

We do the mock site first because it's safe to experiment on. If something breaks, no real
users are affected. Once it has run well for a while, we trust it enough for the real site.

---

## 2. Docker basics (just what you need for this plan)

You already use Docker for local development (`docker-compose.yml` + `Dockerfile.dev`),
so some of this will look familiar.

### Image
An **image** is a frozen package that holds everything a program needs to run: the
operating system files, Python, the installed packages and our code. Think of it as a
recipe that has already been cooked and put in the freezer. You build it once, and it's
identical on every computer.

### Dockerfile
A **Dockerfile** is the *recipe* for building an image, a list of steps such as "start from
Python 3.12", "install the packages in requirements.txt", "copy our code in".

### Container
A **container** is a *running copy* of an image, like heating up the frozen meal. You can
stop it, delete it and start a fresh one from the same image at any time. **Anything a
container writes inside itself is lost when the container is deleted.** That's why we need
volumes.

### Volume
A **volume** is a storage folder that Docker keeps *outside* the container, so it survives
when containers are deleted and recreated. We'll put the database files, uploaded images
(`media`) and HTTPS certificates in volumes.

### Docker Compose
Our site is several programs working together: the database, Django and a web server.
**Docker Compose** lets us describe all of them in one file (a `compose` YAML file). Then
one command, `docker compose up`, starts them all and connects them on a private network.
Inside that network, containers can reach each other by name. For example, Django reaches
the database at the address `db`.

### Is Docker heavy?
On a Linux server, no. A container is not a separate computer. It's a normal program
running on the server, fenced off so it only sees its own files and network, so it runs at
basically full speed. The extra cost is the Docker background program (~50–100 MB of
memory) and some disk space for images. Docker *feels* heavy on Windows/Mac because Docker
Desktop runs a hidden Linux virtual machine there. Servers don't need that.

### The `.env` file
A plain text file with settings and secrets (passwords, secret keys) in the form
`NAME=value`. It's never committed to git. Each server has its own. Docker Compose reads it
and passes the values into the containers.

---

## 3. The big picture: what changes on the server

### Today (no Docker)

```
Visitor ──HTTPS──▶ Nginx (installed on server)
                     │  ├─ /static/  → files in a folder
                     │  └─ /media/   → files in a folder
                     ▼
                  Gunicorn (started by systemd) runs Django
                     ▼
                  PostgreSQL (installed on server)

Certbot (installed on server) renews the HTTPS certificate
```

Each of those programs is installed and configured by hand.

### New (Docker)

```
Visitor ──HTTPS──▶ [caddy container]
                     │  ├─ /static/  → "static" volume
                     │  └─ /media/   → "media" volume
                     ▼
                  [web container]  Gunicorn runs Django
                     ▼
                  [db container]   PostgreSQL → "pgdata" volume
```

The only thing installed on the server is **Docker**. Everything else comes from images
and is described in one compose file in the repo.

### Old part → new part

| Today | New | Notes |
|---|---|---|
| PostgreSQL installed with `apt` | `db` container (official `postgres:16` image) | Same version as today and as local dev |
| Python venv + `pip install` | Built into the `web` image by the `Dockerfile` | |
| Gunicorn started by `gunicorn.service` (systemd) | `web` container runs Gunicorn | Docker restarts it if it crashes or the server reboots |
| Nginx serving the site | `caddy` container | See section 4 |
| Certbot for HTTPS certificates | Caddy does it by itself | No setup at all |
| `ifiplatform/.env` | `.env` in the repo root | Same kind of file, a few extra lines |
| `deploy/deploy.sh` | `deploy/docker/deploy.sh` | Same idea, Docker commands instead |

---

## 4. What we decided, and why

- **The mock site gets its own server (VM)**, so it can never slow down or break the real
  site. The real server only has 1 CPU and 4 GB of memory.
- **Caddy instead of Nginx.** Caddy is a web server like Nginx, but it gets and renews
  HTTPS certificates automatically. Nobody has to run Certbot, and its config file is about
  10 lines. That removes the hardest part of today's setup.
- **fail2ban: full protection on both servers, built once now.** fail2ban blocks IP
  addresses that misbehave. We keep the SSH rule as it is, and we rebuild the "bot
  searching for /wp-admin" rule so it reads Caddy's log instead of Nginx's. The mock
  server gets exactly the setup the real site will use, so phase 2 has nothing to redo.
  See 5.10 for how, and for the two Docker traps it has to avoid.
- **The server setup itself is a script too** (`setup_server.sh`, 5.11). Docker, fail2ban,
  folders and log settings are installed by one command instead of steps copied from a doc.
- **The mock site is public, but hidden from Google.** The data is fake, so there's nothing
  to protect, and event participants can share the link freely. Caddy adds the
  `X-Robots-Tag: noindex` header, which tells search engines not to list it.
- **We start with the mock site** (see section 1).

---

## 5. Phase 1: Add the Docker files to this repo

**Target: done within about 2 days.** This is the main work. Here's every file, what it is
and why we need it.

### 5.1 `requirements.txt`: add Gunicorn
**What:** add one line, `gunicorn==<version>`.
**Why:** Gunicorn is the program that runs Django on a server. Right now it was installed
by hand on the prod server and isn't listed anywhere, so the Docker image wouldn't include
it. We'll use the same version as the prod server (found with `venv/bin/pip show gunicorn`
on the server), so nothing changes for the real site. This also fixes a known issue
already listed in `server_setup.md`.

### 5.2 `Dockerfile`: the recipe for the server image
**What:** a new file in the repo root. `Dockerfile.dev`, the one used for local
development, stays as it is.
**Steps in the recipe:**
1. Start from `python:3.12-slim`, a small Linux with Python 3.12 (same as today).
2. Copy `requirements.txt` in and `pip install` it.
3. Copy the `ifiplatform/` folder (our Django code) into `/app` in the image.
4. Create a normal user called `app` and run as that user. Running as the all-powerful
   `root` user is a security risk.
5. Create empty `staticfiles/`, `media/` and `django_cache/` folders owned by `app`, so
   Django is allowed to write into them.
6. Say what to run when a container starts: the entrypoint script (5.3), then Gunicorn with
   the same settings as today (3 workers, 30-minute timeout).

**How it differs from `Dockerfile.dev`:** the dev version *shares* your code folder into
the container, so edits show up live. The server version *copies* the code into the image,
so the server runs exactly the version that was built.

### 5.3 `deploy/docker/entrypoint.sh`: what runs first when `web` starts
**What:** a tiny script that runs every time the `web` container starts:
1. `python manage.py collectstatic`, which gathers all CSS, JS and images into the
   `static` volume so Caddy can serve them.
2. Then start Gunicorn.

**Why not run migrations here too?** On the real site we want to take a database backup
*before* migrating, because some of our migrations can't be undone. The deploy script
(5.7) handles that order, so we keep migrations there.

### 5.4 `compose.prod.yml`: the description of the whole stack
**What:** a new compose file in the repo root. It's separate from `docker-compose.yml`,
which stays the local dev setup and isn't touched.
**It describes 3 containers ("services"):**

**`db`**: the database.
- Uses the official `postgres:16` image.
- Gets its database name, user and password from `.env`.
- Stores its data in the `pgdata` volume, so the data survives restarts and rebuilds.
- Has a "healthcheck", so other containers can wait until the database is ready
  (copied from the dev compose file).

**`web`**: Django + Gunicorn.
- Built from our `Dockerfile` (5.2).
- Reads all settings from `.env`.
- Uses the `media` volume (uploaded images), the `static` volume (CSS/JS) and the `cache`
  volume.
- Published as `127.0.0.1:8000`. `127.0.0.1` means "only from this server itself", so it's
  **not reachable from the internet**. Only Caddy, running on the same server, can reach it.
- Waits for `db` to be healthy before starting.

**`caddy`**: the front door.
- Uses the official `caddy` image.
- The only container open to the internet, on ports 80 (HTTP) and 443 (HTTPS).
- Uses `network_mode: host`: Caddy uses the server's own network directly instead of
  Docker's private network. It's the cleanest fix for the two traps in 5.10 (real visitor
  IPs in the log, and bans that actually block). Because of this, Caddy reaches Django at
  `127.0.0.1:8000` instead of by the name `web`.
- Writes its access log to `/var/log/caddy/` **on the server** (a "bind mount": a normal
  server folder shared into the container), so fail2ban can read it.
- Can *read* (not change) the `static` and `media` volumes, so it can serve those files
  quickly without bothering Django.
- Stores its HTTPS certificates in the `caddy_data` volume, so it doesn't ask for new
  certificates on every restart (Let's Encrypt limits how often you can ask).

All three get `restart: unless-stopped`, so Docker starts them again after a crash or a
server reboot. That replaces what systemd does for Gunicorn today.

All three also get a **log size limit** (`max-size: 10m`, `max-file: 3`). By default Docker
keeps everything a container prints, forever. On a 20 GB disk that eventually fills up
and takes the site down. The limit keeps the newest ~30 MB per container.

### 5.5 `deploy/docker/Caddyfile`: Caddy's settings
**What it says, in plain words:**
- "Serve the website at the domain in `SITE_DOMAIN`, and get an HTTPS certificate for it."
- "Requests starting with `/static/` or `/media/`: answer with the file from the volume."
- "Everything else: pass it on to Django (`127.0.0.1:8000`)."
- "Write an access log (one line per request, JSON format) to
  `/var/log/caddy/access.log`. Start a new file at 10 MB and delete files older than 14
  days." Visitor IP addresses count as personal data, so we don't keep them forever.
- "Allow uploads up to 20 MB." Today Nginx silently limits uploads to 1 MB, a known issue
  in `server_setup.md`, so this fixes it.
- "Compress responses" (gzip), so pages load faster.
- "Add the `X-Robots-Tag` header from the `ROBOTS_TAG` setting." The mock site sets it to
  `noindex, nofollow` (hide from Google). The real site leaves it at the default, `all`
  (normal).

### 5.6 `deploy/docker/.env.example`: template for the settings file
**What:** a template you copy to `.env` in the repo root on the server, then fill in.
`.env` is already ignored by git, so secrets never get committed.
**It contains:**
- The same Django settings as today's `ifiplatform/.env.example` (secret key, DEBUG,
  database password, allowed hosts, email…).
- `COMPOSE_FILE=compose.prod.yml`. This tells Docker Compose to use the server compose
  file, so on the server you can type `docker compose logs` instead of
  `docker compose -f compose.prod.yml logs`.
- `SITE_DOMAIN`: the address the site is served at (used by Caddy).
- `ROBOTS_TAG`: see 5.5.
- `SEED_DEMO_DATA`: `True` on the mock site, so the deploy script fills the site with fake
  content.
- `DEPLOY_BRANCH`: which git branch the server runs (normally `main`).
- A clearly marked block with "values for the mock site": `DEBUG=False`,
  `SEED_DEMO_DATA=True`, and email, DeepL and Umami left empty, because the mock site
  doesn't need them.

### 5.7 `deploy/docker/deploy.sh`: the one script you run
Used both for the **first setup** and for **every update afterwards**. Step by step:

| # | Command (simplified) | What it does |
|---|---|---|
| 1 | `git fetch` + `git reset --hard origin/<branch>` | Gets the newest code |
| 2 | `docker compose build` | Builds a new `web` image from the new code |
| 3 | `docker compose up -d db` | Starts the database (if not already running) |
| 4 | `docker compose run --rm web python manage.py migrate` | Updates the database tables. `run --rm` means "start a temporary container, run this one command, then delete it" |
| 5 | *(only if `SEED_DEMO_DATA=True`)* `... seed_dev_data` | Fills in fake content. It skips anything that already exists, so it's safe on every deploy |
| 6 | `docker compose up -d` | Starts or replaces all containers with the new versions. `-d` means "run in the background" |
| 7 | `docker compose exec web python manage.py clear_cache` | Clears Django's cache, same as today's deploy. `exec` runs a command inside an already running container |
| 8 | `docker image prune -f` | Deletes old unused images so the disk doesn't fill up |

Two things from today's deploy are left for phase 2 (the real site): the backup before
migrating, and the 10-minute "the site is about to restart" banner for visitors.

### 5.8 One technical trap we must avoid

*(With Caddy on the host network, Gunicorn sees Caddy's requests arriving through Docker's
port forwarding, not from a socket file, so this trap still applies.)*

**The problem:** the real site forces HTTPS (`SECURE_SSL_REDIRECT` in `settings.py`).
Django decides "is this request HTTPS?" by trusting a note that the front door adds to
each request (`X-Forwarded-Proto: https`). Gunicorn only trusts that note from addresses
it knows. Today Nginx talks to Gunicorn through a local socket file, which Gunicorn always
trusts. In Docker, Caddy talks to Gunicorn over the internal network from an address
Gunicorn doesn't know, so Gunicorn ignores the note. Django then thinks the request is
plain HTTP and redirects to HTTPS, which comes back as "HTTP" again, and that repeats
forever. The browser shows "too many redirects".

**The fix:** set `FORWARDED_ALLOW_IPS=*` on the `web` container ("trust the note from
anyone"). This is safe because `web` is only published on `127.0.0.1`, so only Caddy can
reach it. No change to `settings.py` is needed.

### 5.10 fail2ban: blocking bots, rebuilt for Caddy

**What the bot rule does:** bots on the internet try addresses of software we don't run
(`/wp-admin`, `/phpmyadmin`, `/.env`…). fail2ban reads the web server's log, and when one
IP address asks for 2 such addresses and gets "404 Not found", it blocks that IP for an
hour. Today this rule reads Nginx's log. Now it will read Caddy's.

**Trap 1: every visitor could show up with the same IP address.** When Docker forwards
outside traffic into a container on its private network, it sometimes replaces the
visitor's real IP with its own internal one. This happens for IPv6 visitors in particular,
and our server has IPv6. The log would then say every request came from Docker. fail2ban
would either ban nobody, or ban "Docker", which means everybody.
→ **Fixed by** Caddy using the host network (5.4). It receives connections directly and
always sees the real IP.

**Trap 2: bans that don't block anything.** fail2ban blocks an IP by adding a rule to the
server's firewall. Docker adds its own firewall rules for containers on its private
network, and those run *before* fail2ban's rules. The ban would look active in
`fail2ban-client status` but the bot would still get through. This is a classic, silent
Docker mistake.
→ **Also fixed by** the host network: traffic to Caddy goes through the server's normal
firewall path, where fail2ban's rules apply. No special firewall setup is needed.

**The files (in the repo, copied onto the server by `setup_server.sh`):**
- `deploy/docker/fail2ban/jail.local`: the rules that are switched on:
  - `sshd`: same as today.
  - `caddy-botsearch`: reads `/var/log/caddy/access.log`, maxretry 2, ban 1 hour (same as
    today's nginx rule).
  - `ignoreip`: never ban the server itself (`127.0.0.1`, `::1`).
  - Today's `nginx-http-auth` rule is not carried over. It watches for wrong passwords on
    Nginx password-protected pages, and we have none, so it does nothing today either.
- `deploy/docker/fail2ban/filter.d/caddy-botsearch.conf`: tells fail2ban how to read
  Caddy's JSON log lines. It finds the visitor IP (`client_ip`), the address asked for
  (`uri`) and the result (`status: 404`). The list of bot addresses is copied from
  fail2ban's built-in nginx filter, so we block the same things as today.
- `deploy/docker/fail2ban/test_access.log`: a few example log lines (some bots, some
  normal visitors), so anyone can check the filter with `fail2ban-regex` without waiting
  for real bots.

**Not covered, same as today:** someone guessing passwords on the Wagtail login page.
Django answers a wrong password with a normal page (status 200), so the log can't tell it
apart from a normal visit. If we want that protection later, it belongs in Django (for
example the `django-axes` package), not in fail2ban. That would be a separate task.

### 5.11 `deploy/docker/setup_server.sh`: preparing a fresh server
**What:** a script you run once on a brand-new Ubuntu server (with `sudo`). It replaces
most of the manual steps in `docker_server.md`, so the next person can't miss one:
1. Installs Docker (`docker.io`, `docker-compose-v2`) and fail2ban with `apt`.
2. Lets the `ubuntu` user run Docker without `sudo` (adds it to the `docker` group).
3. Creates `/var/log/caddy/`.
4. Copies the fail2ban files from 5.10 into `/etc/fail2ban/` and restarts fail2ban.
5. Adds a 2 GB swap file if the server has none: extra emergency memory on disk, so a
   build can't crash the server even if memory runs short.
6. Sets the automatic security-updates time to 04:00, same as today's server
   (`server_setup.md` step 2).

It's safe to run again: each step checks whether it's already done. Running it a second
time on an existing server also brings the fail2ban rules up to date.

### 5.9 Docs for people (in `docs/`, each with a `Last updated:` date)
- **New `docs/operations/docker_server.md`**: the guide for the next person:
  - What the setup is (a short version of sections 2–3 of this plan).
  - **Setting up a new server**, step by step: create the VM in NREC (open only ports 22,
    80 and 443) → `git clone` → `sudo bash deploy/docker/setup_server.sh` → log out and
    back in (so the Docker group applies) → copy and fill in `.env` → add the DNS record →
    `bash deploy/docker/deploy.sh` → create an admin user with
    `docker compose exec web python manage.py createsuperuser`.
  - **fail2ban:** how to see who is banned (`sudo fail2ban-client status caddy-botsearch`),
    how to unban someone, and how to test the filter with `fail2ban-regex`.
  - **Everyday commands:** see logs (`docker compose logs -f web`), open a Django shell,
    restart, check what's running (`docker compose ps`).
- **`docs/architecture/docker_setup.md`**: it currently says "Production doesn't use
  Docker". Change it to point to the new doc, and say the real site is still on the old
  setup until phase 2.
- **`docs/operations/server_setup.md`**: its note "Docker could replace…" now points to the
  new doc.

---

## 6. Phase 1b: Put the Halloween mock site online

**Right after phase 1.** The Halloween repo is a *copy* of this repo with no shared git
history, so we can't "merge" the new files into it. We copy them by hand.

1. **Copy these files** from this repo into the Halloween repo: `Dockerfile`,
   `compose.prod.yml`, the whole `deploy/docker/` folder (including `setup_server.sh` and
   the `fail2ban/` files), the new `gunicorn` line in `requirements.txt`, and
   `.dockerignore`.
2. **Create a new server** in NREC: **`m1.medium`** (1 vCPU, 4 GB RAM, 20 GB disk), the
   same size as the real site's server. Why:
   - It's a rehearsal. In phase 2 the real site runs this exact Docker setup on an
     `m1.medium`, so if the mock site runs well, we know it fits.
   - Memory: database (~200 MB) + 3 Django workers (~600 MB) + Caddy (~30 MB) + building a
     new image during a deploy (several hundred MB extra while the site keeps running).
     That fits in 2 GB, but only just. During the event, merges trigger deploys often.
   - Disk: each build makes a ~1 GB image. The deploy script deletes old ones, but 20 GB
     gives margin.

   *Fallback if the NREC quota is tight:* `m1.small` works for fake data. The swap file
   that `setup_server.sh` adds keeps builds from running out of memory.

   Also use Ubuntu 24.04 like the real server, and the security group with only ports 22,
   80 and 443 open.
3. **Add a DNS record** for a subdomain, e.g. `halloween.ifiplattform.no`, pointing at the
   new server's IP address. Caddy needs this before it can get a certificate.
4. **Follow `docker_server.md`** using the "mock site" values in `.env`.
5. **Create an admin login** with `createsuperuser`. The seed's usual `admin/admin` user is
   deliberately *not* created when `DEBUG` is off, because that password is public in our
   repo and anyone could log in on a public site.
6. **Optional, but great for the event:** a GitHub Actions workflow in the Halloween repo
   that runs `deploy/docker/deploy.sh` on the server every time something is merged into
   `main`. Participants then see their fixes go live within minutes. It works like today's
   `.github/workflows/deploy.yml`, but with the Halloween repo's own secrets (server IP,
   SSH key).

---

## 7. Phase 2: Move the real site over (after Oct 19, separate task)

Not part of this task. It's listed so we don't build anything in phase 1 that gets in the
way.

- **Scheduled jobs.** Today systemd timers run DeepL translation (every minute), nightly
  translation cleanup, the Peoply event sync and the daily backup. These must run in the
  Docker setup too, either as an extra "scheduler" container or as timers on the server
  that run `docker compose exec web python manage.py ...`. The mock site won't run them.
- **Backups.** Rewrite `backup_db.sh` to take the database dump from the `db` container and
  copy the `media` volume to `/mnt/backups`. The deploy script runs it before migrating.
- **Redirect** `ifiplattform.no` → `www.ifiplattform.no` in the Caddyfile.
- **fail2ban needs no work.** The mock server already runs the full setup (5.10).
- **Deploy extras:** the visitor countdown banner and the DeepL glossary sync.
- **The move itself:** take a final backup on the old server → load it into the new
  `db` container and copy media into the `media` volume → switch DNS → shut down the old
  server → update `prod_server.md`, `server_setup.md` and `backups_and_recovery.md`.

---

## 8. How we check that it works

**On your own computer first** (Docker Desktop is enough):
1. Copy `.env.example` to `.env` and set `SITE_DOMAIN=localhost` and `SEED_DEMO_DATA=True`.
   For `localhost`, Caddy makes its own test certificate instead of asking Let's Encrypt.
2. Run the deploy script without the git step.
3. Check:
   - `https://localhost` opens (accept the browser warning about the test certificate) with
     no "too many redirects" error, so the trap in 5.8 is fixed.
   - Pages have their styling, so `/static/` works.
   - Images show, so `/media/` works.
   - Uploading an image bigger than 1 MB in the Wagtail admin works.
   - The `X-Robots-Tag` header is present: `curl -kI https://localhost`.
   - Secrets can't be downloaded: `curl -kI https://localhost/.env` gives 404.
4. Run the deploy script **a second time**. It should finish without errors, and nothing
   is duplicated.
5. Run `docker compose restart`. Everything comes back, and the data is still there.

**fail2ban filter, before any server exists** (needs fail2ban installed, or run it in a
throwaway Ubuntu container):
- `fail2ban-regex deploy/docker/fail2ban/test_access.log deploy/docker/fail2ban/filter.d/caddy-botsearch.conf`
  should match the bot lines and *only* those, with the right IP addresses.

**Then on the mock server:**
- Real IPs in the log: visit the site from your phone on mobile data (often IPv6) and from
  a laptop on Wi-Fi. `sudo tail /var/log/caddy/access.log` should show your real
  addresses, not a `172.x.x.x` Docker address (trap 1).
- Bans really block (trap 2): from a phone on mobile data (not the network you SSH from!),
  open `https://<mock-domain>/wp-login.php` and `/phpmyadmin`. Then:
  - `sudo fail2ban-client status caddy-botsearch` lists the phone's IP.
  - The site no longer loads on the phone.
  - Unban it with `sudo fail2ban-client set caddy-botsearch unbanip <ip>`, and the site
    loads again.
- The SSH rule is active: `sudo fail2ban-client status` lists `sshd` and `caddy-botsearch`.
- Running `setup_server.sh` a second time finishes without errors and changes nothing.
- The site opens on the subdomain with a real, valid HTTPS certificate (padlock, no
  warning).
- Reboot the server. The site comes back up by itself.
- If the auto-deploy workflow was added: merge a small change into the Halloween repo's
  `main` and watch it appear on the site.

**Tests:** no Django code changes, so the test suite doesn't need to run, and CI is
unchanged.
