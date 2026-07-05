<div align="center">

# 🎓 MaktabPlus (مکتب‌پلاس)

### A full-featured online learning & school management platform built with Django

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Alpine.js](https://img.shields.io/badge/Alpine.js-3.x-8BC0D0?logo=alpinedotjs&logoColor=black)](https://alpinejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*Courses, lessons, quizzes, live course chat, an AI study assistant, and a management panel — all in one place, with a fully RTL Persian UI.*

</div>

---

## ✨ Overview

**MaktabPlus** is an online course platform (LMS) designed for Persian-speaking students and teachers. Students can browse and enroll in courses, watch lessons, take quizzes, chat with classmates in course-specific rooms, and ask an AI assistant for study help. Teachers and admins manage courses, lessons, quizzes, and grades from a dedicated panel.

The project is built with production-grade concerns in mind: race-condition-safe enrollment, email verification, password recovery, access control on every layer, and environment-driven configuration.

## 🚀 Features

### 👤 Accounts & Authentication
- Student sign-up with **email verification** (accounts stay inactive until the activation link is clicked)
- Login with **open-redirect protection** (`next` parameter is validated)
- **Password reset** flow (forgot password) with styled Persian emails
- Password change, profile editing, avatars, and notifications
- Role-based access: student / teacher / admin
- Developer-friendly: when no SMTP server is configured, activation & reset links are shown right in the UI (DEBUG mode only)

### 📚 Courses & Lessons
- Course catalog with categories, levels, search, filters, and **pagination that preserves active filters**
- Rich course detail page: curriculum, instructors, ratings & reviews, related courses
- Free-preview lessons + enrollment-gated content
- Video lessons with attachments, comments, and progress tracking (mark as complete)
- Discount pricing, capacity limits, and enrollment deadlines
- View counter implemented with atomic `F()` expressions

### 🎟️ Enrollment (Race-Condition Safe)
- **Atomic enrollment** using `transaction.atomic()` + `select_for_update()` — no duplicate enrollments, no over-capacity sign-ups even under concurrent requests
- Unique constraint on (student, course) at the database level
- Enrollment states: active / completed / cancelled — cancelled enrollments can be re-activated safely
- POST-only enrollment endpoint (CSRF-protected)

### ⭐ Ratings & Reviews
- Only **enrolled** students can rate a course (1–5 stars + optional review)
- One rating per student (update-or-create), course average recalculated on every change
- Clear success/error feedback for every outcome

### 📝 Quizzes
- Teacher-authored quizzes with questions and choices
- Student attempts with scoring and results history

### 💬 Course Chat
- Per-course chat rooms, restricted to actively enrolled students
- Near-real-time updates via efficient polling (`?after=` incremental fetch)
- Rate limiting on message sending to prevent spam
- Message deletion for authors and staff

### 🤖 AI Study Assistant
- Built-in Q&A assistant powered by any **OpenAI-compatible API** (OpenRouter, DeepSeek, etc.)
- Beautiful markdown-rendered answers
- Per-user **daily usage quota** to control API costs
- Floating assistant button available across the site

### 🛠️ Management Panel
- Dashboard with key stats
- Course, quiz, and lesson management for teachers/admins
- Results & grades overview
- User listing for staff

### 🎨 Frontend
- Modern, fully **RTL** Persian UI with a consistent light theme
- Tailwind CSS + Alpine.js + Lucide icons
- Glassmorphism cards, smooth reveal animations, skeleton-safe interactions
- Responsive: desktop navigation + mobile menu
- Persian number formatting and 3-digit price separators

## 🔒 Security Highlights

| Concern | Mitigation |
|---|---|
| Duplicate / over-capacity enrollment | `transaction.atomic()` + `select_for_update()` + DB unique constraint |
| Open redirect after login | `url_has_allowed_host_and_scheme()` validation |
| Fake email sign-ups | Email verification — account inactive until activated |
| Unauthorized lesson access | Server-side enrollment checks on every lesson view |
| Chat abuse | Enrollment-gated rooms + rate limiting |
| CSRF | Django CSRF middleware + POST-only mutating endpoints |
| Secrets in code | All secrets & config read from environment variables |
| AI cost abuse | Per-user daily quota |

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, Django 6.0 |
| Database | PostgreSQL |
| Frontend | Django Templates, Tailwind CSS, Alpine.js, Lucide Icons |
| AI | OpenAI-compatible chat completions API (OpenRouter / DeepSeek / ...) |
| Auth | Django auth + email activation + password reset |

## 📁 Project Structure

```
school/
├── EduPlatform/        # Project settings, root URLs, AI settings
├── accounts/           # Auth, profiles, activation, password reset, notifications
├── courses/            # Courses, lessons, categories, ratings, comments
├── Enrollment/         # Enrollment model & business rules
├── quiz/               # Quizzes, questions, attempts, scoring
├── chat/               # Per-course chat rooms (polling-based)
├── qa/                 # AI study assistant (quota-limited)
├── panel/              # Teacher/admin management panel
├── templates/          # Base layout & shared templates
├── static/             # CSS (nova.css), JS (nova.js), images
└── media/              # User uploads (avatars, thumbnails, attachments)
```

## ⚙️ Getting Started

### Prerequisites

- Python **3.12+**
- PostgreSQL **14+**
- `pip` and `venv`

### 1. Clone & set up the environment

```bash
git clone <your-repo-url>
cd school
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install django psycopg[binary] pillow requests python-dotenv
```

### 2. Create the PostgreSQL database

```sql
CREATE DATABASE eduplatform;
CREATE USER eduplatform_admin WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE eduplatform TO eduplatform_admin;
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# --- Django ---
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-me-in-production
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# --- AI Assistant (OpenAI-compatible) ---
AI_API_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=your-api-key
AI_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
AI_DAILY_LIMIT=10

# --- Email (optional — omit to print emails to the console in dev) ---
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=you@example.com
# EMAIL_HOST_PASSWORD=app-password
# DEFAULT_FROM_EMAIL=MaktabPlus <no-reply@example.com>
```

> 💡 **No SMTP server? No problem.** In development (`DJANGO_DEBUG=True` with the default console email backend), activation and password-reset links are displayed directly in the UI.

### 4. Migrate & run

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000** 🎉

## 🔧 Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Debug mode — set `False` in production |
| `DJANGO_SECRET_KEY` | dev key | Secret key — **must** be set in production |
| `DJANGO_ALLOWED_HOSTS` | `*` (dev) | Comma-separated allowed hosts |
| `AI_API_BASE_URL` | DeepSeek URL | Any OpenAI-compatible base URL |
| `AI_API_KEY` | — | API key for the AI provider |
| `AI_MODEL` | `deepseek-chat` | Model identifier |
| `AI_DAILY_LIMIT` | `10` | Max AI questions per user per day |
| `EMAIL_BACKEND` | console backend | Use SMTP backend in production |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | — | SMTP connection settings |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | SMTP credentials |
| `DEFAULT_FROM_EMAIL` | `maktabplus <no-reply@maktabplus.local>` | Sender address |

## 🗺️ Roadmap

- [ ] 💳 Online payment gateway integration (Zarinpal) for paid courses
- [ ] 📱 Progressive Web App (PWA) support
- [ ] 🔔 Real-time notifications (WebSocket)
- [ ] 📊 Advanced analytics for teachers
- [ ] 🌍 English localization

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push and open a Pull Request

## 📄 License

This project is released under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by mohammadreza fasli**

**If you find this project useful, please give it a star!⭐**

</div>
