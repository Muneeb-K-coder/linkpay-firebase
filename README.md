# LinkPay 2.0 — starter project

Fresh Django backend + Firebase Authentication frontend. This is a starter scaffold, not a production-ready earning network.

## 1. Windows PowerShell setup

```powershell
cd "$HOME\Desktop"
mkdir LinkPay_2_0
# Extract this ZIP into LinkPay_2_0, then:
cd "$HOME\Desktop\LinkPay_2_0"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations links
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the frontend and http://127.0.0.1:8000/django-admin/ for Django admin.

If PowerShell blocks activation, run this once in the current terminal:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
Then activate the environment again.

## 2. Firebase setup

1. Open Firebase Console and create a new project.
2. In Authentication → Sign-in method, enable Email/Password.
3. In Project settings → General → Your apps, register a Web app.
4. Copy its `apiKey`, `authDomain`, `projectId`, and `appId` into `templates/dashboard.html` under `firebaseConfig`.
5. In Project settings → Service accounts, generate a private service-account JSON key. Save it to `secrets/firebase-service-account.json` and keep it out of Git/public hosting.
6. The `.env` setting `FIREBASE_SERVICE_ACCOUNT` points to this file. Restart Django after setting it.

Do not share the service-account JSON or commit it to GitHub. Firebase Web config is not a service-account secret, but protect your app with Firebase Auth and backend token verification.

## 3. Current scope and important limitations

- Firebase signup/login and Firebase ID-token verification are wired into the frontend/API.
- User-owned short links, redirect click counting, and dashboard totals are implemented.
- Earnings and referrals are intentionally zero; no ad network is integrated.
- Withdrawals are intentionally disabled until verified revenue, balance ledger, fraud checks, and payout policies are implemented. Do not show or promise fake earnings.
- The simple admin API expects a Firebase custom claim `admin: true`. A Django superuser alone does not automatically receive this claim. Set custom claims only from a trusted server/admin script using Firebase Admin SDK.
- Add rate limits, abuse prevention, URL reputation checks, HTTPS, secure production settings, PostgreSQL, tests, and a proper balance ledger before launch.
