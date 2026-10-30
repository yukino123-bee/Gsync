# GroupSync

A group-project workspace for schools. Students get a shared task board, milestones, files, notes and an
automatic contribution log. Teachers get a dashboard of every group's progress, can comment on milestones, and
see private peer evaluations.

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, SQLite (PostgreSQL-ready), APScheduler
- **Mobile:** Expo SDK 58, React Native, TypeScript, Expo Router (built on React Navigation), Zustand, Axios

```
groupsync/
  backend/   FastAPI app, migrations, seed script, tests
  (the Expo app lives in the repository root, next to groupsync/)
```

## 1. Backend

```bash
cd groupsync/backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then set SECRET_KEY (command is in the file)
python seed.py                       # creates the database (runs migrations) and demo data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` is required so a real phone on your Wi-Fi can reach the server.
Interactive API docs: <http://localhost:8000/docs>. Health check: <http://localhost:8000/health>.

If you don't want demo data, run `alembic upgrade head` instead of `python seed.py`.
`python seed.py --reset` recreates the demo data.

### Demo accounts (password for all: `password123`)

| Role | Email |
| --- | --- |
| Teacher | `teacher@groupsync.dev` |
| Students 1-7 | `student1@groupsync.dev` ... `student7@groupsync.dev` |

### How groups work (Classroom-style)

Students create a group and get a **Group ID** like `GS-4K7P2Q`. Classmates join with it, and the teacher adds the
group to their dashboard with the same ID (after a preview). A group has one teacher at a time; the teacher can
remove it from the dashboard, rename it, or archive it. The creator or the teacher can regenerate or disable the ID.
Projects/rubrics are optional: a teacher can attach one of their projects to a group.

Demo Group IDs created by `seed.py`:

| Group ID | Group | State |
| --- | --- | --- |
| `GS-4K7P2Q` | Ocean Team (students 1-3) | on the teacher's dashboard, **On track** |
| `GS-R9TM3X` | Forest Team (students 4-6) | on the dashboard, **Needs attention** (one student did all the work, overdue tasks) |
| `GS-M8N6P3` | Mountain Team (students 5-6) | on the dashboard, **Inactive** (8 days quiet) |
| `GS-W5HN8D` | Desert Team (student 7) | not linked: use it to try **Add Group** as the teacher |
| `GS-A2B3C4` | Archived Team | archived, adding/joining is blocked |
| `GS-D5E6F7` | Locked Team | joining disabled, adding/joining is blocked |

The deadline job runs 30 seconds after startup and then hourly, so notifications appear shortly after you start the server.

### Tests

```bash
cd groupsync/backend && source .venv/bin/activate
python -m pytest
```

Covers authentication, role/ownership permissions, peer-evaluation privacy, file validation, task status changes,
and the background deadline job.

### Configuration (`.env`)

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | JWT signing key. **Must** be changed outside development. |
| `DATABASE_URL` | `sqlite:///./groupsync.db` (default) or `postgresql+psycopg2://user:pass@host/db` |
| `CORS_ORIGINS` | Comma-separated origins, or `*` |
| `UPLOAD_DIR`, `MAX_UPLOAD_MB` | Local file storage location and size limit (10 MB) |
| `SCHEDULER_ENABLED` | Set `false` to disable the hourly deadline job (e.g. when running several workers) |
| `LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_SECONDS` | Failed-login rate limit (5 per 15 minutes per IP + email) |

Switching to PostgreSQL only needs `DATABASE_URL` and `alembic upgrade head`.
File storage sits behind the `Storage` interface in `app/services/storage.py`; add an S3 implementation there.

## 2. Mobile app

Requires Node 22.13+ and the **Expo Go** app on your phone (SDK 58).

```bash
cd ~/Gcolab
npm install
npx expo start
```

Scan the QR code with Expo Go (Android) or the Camera app (iOS).

### Testing on a real phone with Expo Go

1. Your computer and phone must be on the **same Wi-Fi network**.
2. Start the backend with `--host 0.0.0.0` (see above).
3. Start the app with `npx expo start`. The app finds the API automatically at
   `http://<your computer's LAN IP>:8000`, using the same address Expo Go uses to reach Metro.
4. Sign in with a demo account.

If the app shows "Can't reach the server":

- Allow incoming connections on ports **8000** (API) and **8081** (Metro) in your computer's firewall.
- Open `http://<your-computer-ip>:8000/health` in the phone's browser. If that fails, it is a network or firewall issue.
- Set the address explicitly: copy `mobile/.env.example` to `mobile/.env`, set `EXPO_PUBLIC_API_URL`, and restart with `npx expo start --clear`.
- `npx expo start --tunnel` only tunnels Metro, not the API. If you must use a tunnel, expose port 8000 separately (for example with ngrok) and put that URL in `EXPO_PUBLIC_API_URL`.
- Android emulators reach the host at `10.0.2.2`, which the app uses as a fallback.

The Profile tab shows which server address the app is using.

### Running in a web browser

```bash
cd groupsync/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # API
cd ~/Gcolab && npm run web                                                  # opens http://localhost:8081
```

The web build talks to the API on the page's own hostname, port 8000 (override with `EXPO_PUBLIC_API_URL`).
To deploy, run `npm run build:web` and host the `dist/` folder on any static host (single-page app: send unknown
paths to `index.html`). Set `EXPO_PUBLIC_API_URL` to your public API URL before building, and set the backend's
`CORS_ORIGINS` to the site's origin. In the browser, confirmations use `window.confirm`, dates use the native
date input, files download through the browser, and push notifications are skipped (in-app notifications still work).

### Push notifications

- In-app notifications (the Notifications tab and its unread badge) work everywhere, including Expo Go.
- **Remote push is not available in Expo Go on Android** (removed by Expo in SDK 53). iOS Expo Go and simulators/web are
  also limited. The app detects this and skips push registration without errors.
- For real push, use a development build: `npx expo install expo-dev-client`, then `eas build --profile development`
  (run `eas init` first so the project gets an EAS `projectId`). The backend sends pushes through the Expo push API
  using each user's saved token.

## 3. How it works

- **Roles:** enforced on every endpoint. Group data is visible only to its members and the teacher who owns the project (403 otherwise).
  Teachers are read-only inside group workspaces; students cannot see other groups or any peer evaluations.
- **Contribution log:** every task, file, note, milestone and status change writes an `activity_log` row in the same transaction.
- **Peer evaluation:** opens when the group's final milestone (the one due last) is submitted. Each member rates every other member 1-5 once. Only the owning teacher can read ratings.
- **File versions:** uploading a file with the same name in a group creates a new version; older versions stay available under "History".
- **Notifications job:** hourly, creates "due soon" (within 24 h), "overdue" (assignee, plus a group summary for members), and
  "inactive group" (3 days with no activity: members and teacher) notifications, at most one per task/group and type per UTC day, then pushes them.

## Notes on choices that differ from the original brief

- **Navigation uses Expo Router** (the project's standard for SDK 58), which is built on React Navigation's stack and tab navigators. Routes in `mobile/src/app` replace `App.tsx`, `navigation/` and `screens/`.
- **`notifications` has two extra nullable columns, `group_id` and `reference_id`**, used for per-task/day de-duplication and to open the right group when a notification is tapped.
- **Admin accounts cannot self-register.** There is only a minimal API (`/api/v1/admin/users`) for admins, and no admin UI.
- **Links** are stored as notes; URLs in notes are tappable.
- **Login rate limiting is in memory**, so it is per server process.

## Troubleshooting

- `ValueError: password cannot be longer than 72 bytes` / bcrypt errors: keep `bcrypt==4.0.1` as pinned in `requirements.txt`.
- 401 right after login on the phone: the phone's clock is badly wrong (tokens look expired). Enable automatic time.
- Reset everything: stop the server, delete `backend/groupsync.db` and `backend/uploads/*`, then run `python seed.py`.
