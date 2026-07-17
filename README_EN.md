# MaktabPlus

A Persian-language Learning Management System built with **Django** for managing courses, lessons, student enrollments, learning progress, quizzes, course chat, notifications, and an AI study assistant.

This project was developed as a final Django course project. Its scope goes beyond basic CRUD pages: it also addresses practical LMS concerns such as **capacity control, protected course content, duplicate enrollment prevention, safe quiz attempts, and separation of business logic**.

> **Project status:** Educational and presentation-ready. The backend architecture has been refactored and documented, but the project does not claim to be fully production-ready or proven for 10,000 concurrent users.

---

## Table of Contents

- [Core Features](#core-features)
- [Project Architecture](#project-architecture)
- [Service and Policy Layers](#service-and-policy-layers)
- [Prevented Bugs and Failure Scenarios](#prevented-bugs-and-failure-scenarios)
- [Data Integrity](#data-integrity)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Roles and Permissions](#roles-and-permissions)
- [Validation and Test Status](#validation-and-test-status)
- [Current Limitations](#current-limitations)
- [Future Roadmap](#future-roadmap)

---

## Core Features

### 1. Accounts and Authentication

- Dedicated student registration form
- Login and logout
- Password change using Django's standard authentication tools
- Student, teacher, administrator, and parent roles
- Public profile with:
  - Avatar and cover image
  - Biography
  - Birth date and location
  - Website and social links
- Teacher profile with specialty and academic degree
- Student profile with student ID and entry year
- Public user profiles
- Account and profile editing
- User directory
- Read and unread notifications
- Personal dashboard with courses, progress, study time, and recent activity

> Email activation and email-based password recovery were removed from the current version. New accounts are activated immediately for now. Phone verification and SMS recovery are planned for a future version but have not been implemented yet.

### 2. Courses and Categories

- Published course catalog
- Hierarchical course categories
- Beginner, intermediate, and advanced levels
- Draft, published, coming-soon, and archived states
- Search by course title, description, teacher, and category
- Filtering by category and level
- Sorting by date, popularity, rating, and price
- Pagination while preserving active filters
- Multiple teachers per course
- Course thumbnail and cover image
- Price, discount percentage, and final-price calculation
- Free and paid courses
- Limited or unlimited capacity
- Enrollment deadline
- Remaining-seat calculation
- Curriculum, instructors, ratings, and related courses
- Unique slugs for readable URLs

### 3. Enrollment

- Safe student enrollment workflow
- Enrollment states:
  - Pending
  - Active
  - Completed
  - Cancelled
- Payment states:
  - Free
  - Pending
  - Paid
  - Refunded
- Safe reactivation of a cancelled enrollment
- Capacity validation inside a database transaction
- Synchronization of enrollment counters and full-capacity state
- Prevention of paid-course access before payment

Free-course enrollments are activated immediately. Until a payment gateway is implemented, paid-course enrollments remain in the `pending` state.

### 4. Lessons and Learning Progress

- Ordered lessons within each course
- Article content, video, and lesson duration
- Free-preview lessons
- Protected lesson attachments
- Last-watched tracking
- Mark-as-complete workflow
- Course progress calculation
- Navigation to the next lesson
- Recent activity on the dashboard
- Lesson comments
- Nested-reply data structure for comments
- Lesson likes

### 5. Course Ratings and Reviews

- One-to-five-star ratings
- Optional written review
- One rating per user per course
- Updating an existing rating instead of creating duplicates
- Course rating average and count
- Rating access restricted to actively enrolled students

### 6. Quizzes and Question Bank

- Reusable question bank
- Topic and difficulty classification
- Supported question types:
  - Single choice
  - Multiple choice
  - True/false
  - Numeric answer
  - Short text answer
- Question images and mathematical content
- Individual points per question
- Numeric tolerance
- Answer explanation and solution
- Quiz association with a course or lesson
- Time limit
- Passing score
- Maximum number of attempts
- Availability start and end dates
- Optional question shuffling
- Optional solution display after completion
- Automatic grading
- Score, percentage, and pass/fail calculation
- Attempt history and result pages

### 7. Course Chat

- Separate chat room for every course
- Access restricted to the course's teachers, administrators, and eligible students
- Latest messages loaded first
- Pagination for older messages
- Adaptive polling to reduce unnecessary requests
- Regular messages and official teacher announcements
- Message deletion by the sender or an authorized course teacher/administrator
- Message length validation
- Rate limiting against spam and double submission
- Batched notification creation for teacher messages

### 8. Notifications and Dashboard

- Notifications with title, message, target link, and creation time
- Read/unread state
- Unread-notification counter
- Enrolled and taught course statistics
- Average progress calculation
- Study-time calculation from completed lessons
- Completed courses and recent activity

### 9. AI Study Assistant

- Questions sent to an OpenAI-compatible API
- Compatible with providers such as OpenRouter and DeepSeek
- Optional course context limited to courses the user can access
- Stored question, answer, status, model, and response time
- Configurable daily quota per user
- Rate limiting against duplicate requests
- External API timeout

### 10. Teacher and Admin Panel

- Management dashboard and statistics
- Course creation, editing, and deletion
- Course publish/unpublish actions
- Quiz creation, editing, and deletion
- Quiz publish/unpublish actions
- Adding and removing quiz questions
- Quiz result and answer inspection
- CSV result export
- Teachers restricted to their own manageable courses and quizzes
- Broader access for administrators

### 11. Frontend

- Persian right-to-left interface
- Responsive mobile and desktop layouts
- Dedicated templates for accounts, courses, lessons, quizzes, chat, and management
- User-facing success and error messages
- Escaped chat text to prevent execution of untrusted HTML

---

## Project Architecture

The project is separated into domain-focused Django applications:

| Application | Main responsibility |
|---|---|
| `accounts` | Users, roles, profiles, authentication, dashboard, and notifications |
| `courses` | Courses, categories, lessons, attachments, comments, ratings, and progress |
| `Enrollment` | Student-course relationship and enrollment/payment state |
| `quiz` | Question bank, quizzes, attempts, answers, and grading |
| `chat` | Course chat and teacher announcements |
| `qa` | AI study assistant and usage quota |
| `panel` | Course, quiz, question, and result management |

### Backend Layers

- **Models:** Data structures and database invariants
- **Forms:** Input validation
- **Policies:** Authorization decisions
- **Services:** Business rules and state-changing use cases
- **Views:** HTTP orchestration and response construction
- **Templates:** Presentation and user interface

This separation keeps views smaller and prevents important rules from being duplicated across unrelated files.

---

## Service and Policy Layers

One of the most important changes in the refactored version was moving business logic out of views and signals.

### Courses

`courses/services.py` is responsible for:

- Student enrollment
- Capacity and deadline validation
- Enrollment-stat synchronization
- Lesson progress updates
- Lesson comment creation
- Course rating creation and updates
- Rating-stat synchronization

`courses/policies.py` is responsible for:

- Detecting whether a user teaches a specific course
- Course-content access decisions
- Course-rating permission

### Quizzes

`quiz/services.py` is responsible for:

- Attempt-limit validation
- Creating or retrieving an open attempt
- Recording submitted answers
- Finalizing an attempt inside a transaction
- Closing expired attempts

`quiz/policies.py` is responsible for:

- Administrator access
- Access for the teacher of the related course
- Access for enrolled students
- Quiz availability-window rules

### Chat

`chat/services.py` handles message creation, rate limiting, and dependent notifications.

`chat/policies.py` handles chat-room access and message-deletion permission.

### Why This Matters

- Business rules can be tested independently from HTTP.
- Views mainly perform orchestration.
- Hidden signal side effects are reduced.
- Enrollment, rating, and quiz rules each have one source of truth.
- Adding an API or another interface later becomes easier.

---

## Prevented Bugs and Failure Scenarios

| Potential issue | Implemented protection | User-facing result |
|---|---|---|
| Duplicate enrollment | Unique constraint on student and course | A student has only one enrollment record per course |
| Over-capacity enrollment under concurrent requests | `transaction.atomic()` and `select_for_update()` | The last available seat cannot be assigned twice |
| Enrollment after the deadline | Deadline validation inside the service | Expired enrollment requests are rejected |
| Paid content opened without payment | Paid enrollment remains `pending` | Paid content is not unlocked for free |
| Cancelled enrollments counted as active | Cancelled records excluded from active capacity | Remaining seats stay accurate |
| Direct lesson access by guessing a URL | Server-side course-access policy | Knowing the URL does not bypass authorization |
| Unauthorized attachment download | Course permission checked before file response | Private files are not exposed |
| Rating without valid enrollment | Rating policy | Only eligible students can rate a course |
| Multiple ratings from one user | Unique constraint and `update_or_create` | A user cannot manipulate the average with duplicates |
| Teacher accessing another teacher's quiz | Same-course teacher check | Course boundaries are preserved |
| Two open quiz attempts | Conditional unique constraint | A student cannot have conflicting active attempts |
| Duplicate quiz submission | Row lock using `select_for_update()` | Scores and answers are not recorded twice |
| Concurrent quiz submissions | Transactional finalization | Attempt results remain atomic and consistent |
| Invalid numeric answer | Safe conversion with `try/except` | User input does not cause a server error |
| Partially correct multiple-choice answer | Exact set comparison | Incomplete answers are not graded as correct |
| Unrelated user entering course chat | Enrollment/teacher access policy | Course chat remains private |
| Deleting another user's message | Ownership or management permission | Messages cannot be removed without authorization |
| Chat spam and double click | Atomic rate limit | Rapid repeated submissions are blocked |
| Stored XSS through chat text | Browser-side escaping with `textContent` | Message HTML and JavaScript are not executed |
| Old messages shown instead of newest messages | Latest-message initial query | Users see the current conversation first |
| N+1 teacher lookup for chat messages | Teacher IDs loaded once | Repeated database queries are reduced |
| Open redirect after login | Validation of the `next` parameter | Users are not redirected to untrusted domains |
| Percentage or score outside valid range | Database check constraints | Invalid values cannot be persisted |
| Duplicate course or lesson URL | Unique slug rules | URLs remain unambiguous |
| Repeated AI use by double click | Rate limit and daily quota | External API usage stays controlled |

---

## Data Integrity

Important rules are enforced at the database level rather than only in forms or views.

### Important Constraints

- One enrollment per student and course
- Unique lesson order within each course
- Unique lesson slug within each course
- One progress record per user and lesson
- One course rating per user and course
- Only one open attempt per student and quiz
- Discount percentage between zero and one hundred
- Non-negative course price
- Progress percentage between zero and one hundred
- Course rating between one and five
- Quiz passing score between zero and one hundred
- Non-negative numeric tolerance

### Important Indexes

- Unread notifications per user
- Course enrollment state
- User lesson progress
- Quiz attempt state
- Daily AI usage

New migrations normalize older invalid or duplicate data before enabling stricter constraints, reducing the risk of migration failure on an existing database.

---

## Project Structure

```text
SchoolManagementSystem/
├── EduPlatform/                 # Main settings, root URLs, and AI settings
├── accounts/                    # Users, profiles, authentication, dashboard, notifications
├── courses/
│   ├── models.py                # Courses, lessons, progress, comments, and ratings
│   ├── services.py              # Course-domain business logic
│   └── policies.py              # Course access rules
├── Enrollment/                  # Enrollment and payment-state model
├── quiz/
│   ├── models.py                # Questions, quizzes, attempts, and answers
│   ├── services.py              # Attempt lifecycle and grading
│   └── policies.py              # Quiz access rules
├── chat/
│   ├── services.py              # Message creation and notifications
│   └── policies.py              # Chat access and message deletion
├── qa/                          # AI assistant and usage quota
├── panel/                       # Teacher and admin management panel
├── templates/                   # Shared templates
├── static/                      # CSS, JavaScript, and images
├── media/                       # Development uploads
├── manage.py
└── README.md
```

---

## Installation

### Requirements

- Python 3.12 or newer
- PostgreSQL 14 or newer
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/mohammadreza829/django_SchoolManagementSystem.git
cd django_SchoolManagementSystem
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

If the project contains `requirements.txt`:

```bash
pip install -r requirements.txt
```

Otherwise, install the core dependencies:

```bash
pip install django "psycopg[binary]" pillow requests python-dotenv
```

### 4. Create the PostgreSQL Database

```sql
CREATE DATABASE eduplatform;
CREATE USER eduplatform_admin WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE eduplatform TO eduplatform_admin;
```

Configure the database connection for your local environment. Do not commit a real database password to Git.

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-this-for-your-machine
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

AI_API_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=your-api-key
AI_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
AI_DAILY_LIMIT=10
```

> Add `.env` to `.gitignore`. Never commit a real API key, database password, or Django secret key.

### 6. Apply Migrations

```bash
python manage.py migrate
```

### 7. Create an Administrator

```bash
python manage.py createsuperuser
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `DJANGO_DEBUG` | Enables or disables debug mode | `True` |
| `DJANGO_SECRET_KEY` | Django cryptographic secret | A long random value |
| `DJANGO_ALLOWED_HOSTS` | Allowed host names | `127.0.0.1,localhost` |
| `AI_API_BASE_URL` | OpenAI-compatible API endpoint | `https://openrouter.ai/api/v1` |
| `AI_API_KEY` | AI provider API key | Secret |
| `AI_MODEL` | Provider model identifier | Selected model ID |
| `AI_DAILY_LIMIT` | Daily question quota per user | `10` |

This version does not depend on SMTP settings because email activation and email-based password recovery were removed.

---

## Roles and Permissions

| Role | Main permissions |
|---|---|
| Student | Enroll, access eligible content, track progress, take quizzes, use chat, and rate courses |
| Teacher | Manage owned courses and quizzes, inspect results, and manage chat for those courses |
| Administrator | Broad management access across courses, quizzes, users, and results |
| Parent | Present in the user model; dedicated parent workflows are planned for a future version |

Permissions are not enforced only by hiding buttons in templates. Views, services, and policies perform server-side authorization checks.

---

## Validation and Test Status

The following checks were completed on the refactored version:

- Successful Python `compileall`
- AST audit for module docstrings
- Docstring audit for backend classes, functions, and methods
- Static review of authorization paths and business rules
- Verification that email routes, templates, and settings were removed
- Verification of constraint and index migrations
- ZIP integrity test

### Testing Limitation

A complete `django check`, real migration run, and integration-test execution were not possible in the review environment. Runtime behavior must therefore be verified after dependencies are installed and PostgreSQL is available on the target system.

Recommended commands:

```bash
python manage.py check
python manage.py migrate --plan
python manage.py test
```

---

## Current Limitations

This is a clean and defensible educational project, not yet a complete production product.

- No real payment gateway is connected.
- Paid-course enrollment remains pending until payment support is added.
- Phone verification and SMS are not implemented yet.
- SMS-based account recovery is not implemented yet.
- Unit and integration test coverage should be expanded.
- The submitted chat version uses polling and would need WebSockets for very high scale.
- Large production uploads should move to object storage and a CDN.
- Official high-stakes quizzes should snapshot questions and points when an attempt starts.
- Real capacity must be measured through load testing; 10,000 concurrent users is not a current project claim.

---

## Future Roadmap

- [ ] Integrate a payment gateway such as Zarinpal
- [ ] Add phone verification and SMS-based recovery
- [ ] Expand unit, integration, and permission tests
- [ ] Snapshot quiz questions and points when attempts start
- [ ] Replace chat polling with WebSockets after learning Redis and Channels
- [ ] Move production media to object storage and a CDN
- [ ] Add Docker and production configuration at a later stage
- [ ] Improve teacher analytics and reporting
- [ ] Add dedicated parent workflows
- [ ] Add English localization

---

## Presentation Notes

Useful technical topics to explain during a project presentation:

1. Why enrollment runs inside a transaction.
2. How `select_for_update` prevents concurrent over-capacity enrollment.
3. Why database constraints are still required when forms validate input.
4. The responsibility difference between a view, service, and policy.
5. How the database allows only one open quiz attempt.
6. How a row lock protects against duplicate quiz submission.
7. Why paid enrollment stays pending without a payment gateway.
8. How teachers are restricted to their own courses and quizzes.
9. How rate limiting and text escaping protect course chat.
10. Why production tools such as Redis and Docker are postponed until a later learning stage.

---

## Summary

MaktabPlus is a multi-module LMS project that addresses more than UI and CRUD operations. It also focuses on data correctness, object-level authorization, concurrent requests, maintainable architecture, and realistic user workflows.

The main architectural improvement in the current version is the separation of **business logic into services** and **authorization rules into policies**. Database constraints and transactional operations also prevent duplicate enrollment, incorrect capacity, invalid ratings, and conflicting quiz attempts.

The project is currently ready for educational presentation and technical feedback. Its future path toward payment support, SMS, automated testing, and production infrastructure is documented clearly without presenting unfinished features as completed work.
