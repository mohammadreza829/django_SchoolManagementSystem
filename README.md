# MaktabPlus (مکتب‌پلاس)

MaktabPlus is an online learning platform (LMS) I built with Django, aimed at Persian-speaking students and teachers. Students can browse and enroll in courses, watch lessons, take quizzes, chat with classmates in course rooms, and ask an AI assistant for help when they get stuck. Teachers and admins manage everything — courses, lessons, quizzes, grades — from a dedicated panel.

It's the biggest project I've built so far, and I used it as an excuse to take the tricky parts seriously rather than fake them: enrollment that stays correct under concurrent requests, real email verification, password recovery, access checks on every layer, and configuration driven entirely by environment variables.

> **Stack:** Python 3.12+ · Django 6 · PostgreSQL · Tailwind CSS · Alpine.js · an OpenAI-compatible API for the assistant

## What's inside

### Accounts & auth
- Sign-up with **email verification** — an account stays inactive until the activation link is clicked
- Login with **open-redirect protection** (the `next` parameter is validated before redirecting)
- A full **password reset** flow with styled Persian emails
- Password change, profile editing, avatars, and notifications
- Roles: student / teacher / admin
- A small quality-of-life touch: when there's no SMTP server configured in development, activation and reset links show up right in the UI so you're never stuck

### Courses & lessons
- A course catalog with categories, levels, search, and filters — and pagination that keeps your filters when you change pages
- Course detail pages with the curriculum, instructors, ratings & reviews, and related courses
- Free-preview lessons, with the rest gated behind enrollment
- Video lessons with attachments, comments, and per-lesson progress ("mark as complete")
- Discount pricing, capacity limits, and enrollment deadlines
- A view counter that uses atomic `F()` expressions so concurrent views don't clobber each other

### Enrollment (the part I'm most proud of)
This is where I spent the most time getting things right. Enrollment runs inside `transaction.atomic()` with `select_for_update()`, backed by a database-level unique constraint on `(student, course)`. The result is that you can't end up with duplicate enrollments or an over-capacity course even if two requests come in at the exact same moment. Enrollments move between active / completed / cancelled, and a cancelled one can be safely reactivated. The endpoint is POST-only and CSRF-protected.

### Ratings & reviews
Only students who are actually enrolled can rate a course (1–5 stars plus an optional review), one rating each. Ratings use update-or-create, and the course average is recalculated on every change.

### Quizzes
Teachers author quizzes with questions and choices; students attempt them, get scored, and can look back at their results history.

### Course chat
Each course has its own chat room, open only to actively enrolled students. Updates come in through efficient incremental polling (`?after=`), there's rate limiting to keep spam down, and authors (and staff) can delete messages.

### AI study assistant
A built-in Q&A assistant that works with any **OpenAI-compatible API** (OpenRouter, DeepSeek, and others). Answers are rendered as markdown, and there's a per-user **daily quota** so API costs stay predictable. The assistant button floats on every page.

### Management panel
A dashboard with the key stats, course/lesson/quiz management for teachers and admins, a results & grades overview, and a user list for staff.

### Frontend
A fully **RTL** Persian UI built with Tailwind CSS, Alpine.js, and Lucide icons — glassmorphism cards, reveal animations, a responsive layout with a mobile menu, and proper Persian number and price formatting.

## Security notes

A quick summary of the things I deliberately guarded against:

| Concern | How it's handled |
|---|---|
| Duplicate / over-capacity enrollment | `transaction.atomic()` + `select_for_update()` + a DB unique constraint |
| Open redirect after login | `url_has_allowed_host_and_scheme()` validation |
| Fake email sign-ups | Email verification — the account is inactive until activated |
| Unauthorized lesson access | Server-side enrollment checks on every lesson view |
| Chat abuse | Enrollment-gated rooms + rate limiting |
| CSRF | Django's CSRF middleware + POST-only mutating endpoints |
| Secrets in code | Everything sensitive is read from environment variables |
| AI cost abuse | A per-user daily quota |

## Project layout

```
school/
├── EduPlatform/     # settings, root URLs, AI configuration
├── accounts/        # auth, profiles, activation, password reset, notifications
├── courses/         # courses, lessons, categories, ratings, comments
├── Enrollment/      # the enrollment model & its business rules
├── quiz/            # quizzes, questions, attempts, scoring
├── chat/            # per-course chat rooms (polling-based)
├── qa/              # the AI study assistant (quota-limited)
├── panel/           # teacher/admin management panel
├── templates/       # base layout & shared templates
├── static/          # nova.css, nova.js, images
└── media/           # user uploads
```

## Getting it running

You'll need **Python 3.12+** and **PostgreSQL 14+**.

```bash
git clone https://github.com/mohammadreza829/django_SchoolManagementSystem.git
cd django_SchoolManagementSystem
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate

pip install django "psycopg[binary]" pillow requests python-dotenv
```

Create the database:

```sql
CREATE DATABASE eduplatform;
CREATE USER eduplatform_admin WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE eduplatform TO eduplatform_admin;
```

Create a `.env` file in the project root:

```env
# --- Django ---
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-me-in-production
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# --- AI assistant (OpenAI-compatible) ---
AI_API_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=your-api-key
AI_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
AI_DAILY_LIMIT=10

# --- Email (optional — leave it out to print emails to the console in dev) ---
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=you@example.com
# EMAIL_HOST_PASSWORD=app-password
# DEFAULT_FROM_EMAIL=MaktabPlus <no-reply@example.com>
```

Then migrate and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 and you're in.

### Want it pre-filled with data?

There's a `seed_demo.py` script that populates the whole platform with realistic Persian demo data — users (admin/teacher/student), categories, courses, lessons, enrollments, quizzes and attempts, chat messages, and notifications. Run it from the folder that has `manage.py`:

```bash
python seed_demo.py            # add data
python seed_demo.py --fresh    # wipe the demo data first, then rebuild it
```

It's safe to re-run, and every demo user's password is `demo12345`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Debug mode — set `False` in production |
| `DJANGO_SECRET_KEY` | dev key | **Must** be set in production |
| `DJANGO_ALLOWED_HOSTS` | `*` (dev) | Comma-separated allowed hosts |
| `AI_API_BASE_URL` | provider URL | Any OpenAI-compatible base URL |
| `AI_API_KEY` | — | API key for the AI provider |
| `AI_MODEL` | model id | Which model to call |
| `AI_DAILY_LIMIT` | `10` | Max AI questions per user per day |
| `EMAIL_BACKEND` | console backend | Switch to the SMTP backend in production |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | — | SMTP connection settings |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | SMTP credentials |
| `DEFAULT_FROM_EMAIL` | dev sender | The "from" address on outgoing mail |

## Things I'd like to add next

- [ ] An online payment gateway (Zarinpal) for paid courses
- [ ] PWA support
- [ ] Real-time notifications over WebSockets
- [ ] More detailed analytics for teachers
- [ ] English localization

## License

Released under the MIT License — see [LICENSE](LICENSE) for the details.
