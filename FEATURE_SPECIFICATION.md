# Secure Online Examination System - Feature Specification

## Executive Summary
A web-based examination platform designed for colleges and review centers with comprehensive cybersecurity controls, browser activity monitoring, and academic integrity features.

---

## 1. SYSTEM ARCHITECTURE

### Technology Stack
- **Framework:** Django 6.0 (Python)
- **Database:** SQLite (configurable for production)
- **Frontend:** HTML5, Tailwind CSS, JavaScript
- **Authentication:** Django's built-in auth system

### User Roles
- **Students:** Take exams, view results, browse available exams
- **Instructors:** Create/manage exams, question banks, subject assignments, monitor integrity

---

## 2. CORE FEATURES

### 2.1 Secure Login System
- Role-based authentication (student/instructor)
- Role verification during login (prevents cross-role access)
- Django session management with 30-minute session timeout
- Session expiration on browser close
- CSRF protection on all forms

### 2.2 Subject Management (Instructor)
- Create subjects with name, code, and description
- Edit/delete subjects
- Subject listing with exam and student counts
- Instructor-specific subject filtering

### 2.3 Subject Assignment (Instructor)
- Enroll students in subjects via username
- Assign subjects to students through SubjectAssignment model
- Remove students from subjects
- Track enrolled count per subject

### 2.4 Question Bank System (Instructor)
- Create multiple-choice questions (4 options: A, B, C, D)
- Set correct answer for each question
- Subject-based question organization
- Edit/update existing questions
- Delete questions from bank
- View all questions with subject filtering

### 2.5 Exam Creation (Instructor)
- Create exams with:
  - Title and description
  - Subject association
  - Duration (minutes) with optional enable/disable
  - Total questions count
  - Random question ordering toggle
  - Availability window (start/end datetime)
- Duplicate existing exams
- Toggle exam active/inactive status
- Archive/restore exams

### 2.6 Exam Management (Instructor)
- Add/remove questions from exam
- Bulk add questions from question bank
- View exam statistics and assigned questions
- Manage exam availability and timing

### 2.7 Student Exam Access
- View available exams (based on subject assignments)
- Exam availability window enforcement
- Exam status tracking (Not Started, In Progress, Completed)
- Progress percentage calculation

---

## 3. BROWSER ACTIVITY DETECTION (Anti-Cheating)

### 3.1 Monitored Activities
| Event Type | Penalty | Behavior Pattern |
|------------|---------|-----------------|
| Tab Switch | 4 | Repeated switching in quick succession |
| Copy Attempt | 6 | Attempted clipboard copy (intentional misconduct) |
| Paste Attempt | 6 | Attempted clipboard paste (intentional misconduct) |
| Right Click | 1 | Minor exploratory action |
| Refresh | 10 | Page reload (severe disruption) |
| DevTools | 15 | Browser developer tools detected (deliberate cheating) |
| Escape Key | 4 | Window escape attempt |

### 3.2 Security Controls
- **Deduplication:** Events filtered within 1-second cooldown
- **Authorization:** Server-side verification of student assignment before logging
- **Hidden Detection:** DevTools detection integrated into frontend

### 3.3 Risk Level Calculation (Behaviorally-Based)
| Risk Level | Penalty Range | Behavioral Pattern |
|------------|---------------|----------------|
| LOW | 1-4 | Minor isolated actions (e.g., accidental right-click, single tab switch) |
| MEDIUM | 5-14 | Repeated or mixed suspicious behavior (e.g., multiple tab switches, combined minor actions) |
| HIGH | 15-24 | Clear intentional misconduct (e.g., copy attempts, copy + tab switch combinations) |
| CRITICAL | 25+ | Severe/excessive violations (e.g., devtools + multiple copy attempts, persistent cheating patterns) |

---

## 4. EXAM INTEGRITY REPORTS

### 4.1 Real-time Analytics Dashboard (Instructor)
- Live exam monitoring with active sessions
- Risk level distribution (LOW/MEDIUM/HIGH/CRITICAL counts)
- Per-exam student progress tracking
- Violation breakdown by type
- Elapsed time tracking per student

### 4.2 Integrity Logs
- Timestamped violation records
- Student and exam linkage
- Event type categorization
- Penalty scoring
- Review status tracking (reviewed/pending)
- Clear all logs functionality

### 4.3 Individual Student Log View
- Filter by student/user ID
- Filter by specific exam
- Violation count display
- Associated exam attempt linking

### 4.4 Risk-Based Auto-Submission
- Automatic submission on CRITICAL risk detection
- Alert notification to student

---

## 5. EXAM INTEGRITY FEATURES

### 5.1 Randomized Questions
- Per-exam toggle for question randomization
- Question order stored in session for consistency
- Questions selected from bank based on total_questions limit

### 5.2 Time Management
- Server-side timer calculation
- Client-side timer display with sessionStorage persistence
- Auto-submission when time expires
- Confirmation dialog before timeout submission

### 5.3 Exam Guidelines
- Mandatory guidelines acknowledgment before starting
- Session-based tracking of acknowledgment
- Prevention of retaking completed exams

---

## 6. RESULTS AND GRADING

### 6.1 Student Results
- Score calculation (correct answers count)
- Integrity score (100 - total_penalty, minimum 0)
- Risk level assignment
- Exam attempt tracking with start/end times

### 6.2 Instructor Results
- All student results listing
- Filter by exam
- Violation count per result
- Export to CSV/PDF reports

### 6.3 Result Components
- Raw score and total questions
- Integrity score percentage
- Risk level classification
- Completion timestamp
- Associated violation logs

---

## 7. USER INTERFACES

### 7.1 Student Dashboard
- Subject-organized exam listing
- Exam status indicators (Not Started/In Progress/Completed/Not Available)
- Progress percentage per exam
- Navigation to start available exams

### 7.2 Instructor Dashboard
- Subject overview with enrollment counts
- Recent exam attempts (last 10)
- Total students and questions counts
- Archived exam count

### 7.3 Exam Interface
- Question navigation dots (current/answered states)
- Progress indicator
- Timer display (countdown or unlimited)
- Auto-save on answer selection
- Save status indicator

### 7.4 Profile Management
- Timezone selection
- Role-based statistics display
- Subject/exam/question counts

---

## 8. DATA MODELS

### 8.1 Core Models
- **Profile:** Links Django User to role (student/instructor)
- **Subject:** Subject with instructor, students (M2M), code, description
- **SubjectAssignment:** Explicit student-subject enrollment
- **Question:** MC question with 4 options and correct answer
- **Exam:** Exam configuration with timing, duration, questions
- **ExamAttempt:** Student's exam session tracking
- **StudentAnswer:** Saved answers per question/exam
- **ExamResult:** Final results with score and integrity metrics
- **IntegrityLog:** Violation records with event type and penalty

---

## 9. SECURITY FEATURES

### 9.1 Access Control
- Role-based decorators (`@instructor_required`, `@student_required`)
- Subject ownership verification
- Assignment verification before exam access
- CSRF protection on all POST requests

### 9.2 Session Security
- Session expiration after 30 minutes
- Session expiry on browser close
- Session-based exam question persistence

### 9.3 Data Validation
- Server-side assignment verification
- Duplicate answer prevention with update_or_create
- Input sanitization through Django forms

---

## 10. EXPORT CAPABILITIES

### 10.1 CSV Export
- Student username, exam title, score
- Integrity score and risk level
- Submission date/time in 12-hour format (e.g., 2026-05-20 02:30 PM)
- Export filtered by specific exam (when selected in results page)
- Exports all results when no exam filter applied

### 10.2 PDF Export
- Rendered results template for printing
- Export filtered by specific exam (when selected in results page)
- Exports all results when no exam filter applied

### 10.3 Student Log Export
- PDF export of individual student integrity logs from view_logs page
- Accessible via "Export PDF" button on student violation detail page
- Includes violation details, exam summary, and timestamps

---

## 11. ADMIN FEATURES

### Django Admin Integration
- Full model registration for database management
- User/Profile management
- Exam, Question, Result oversight

---

## 12. CONFIGURATION OPTIONS

### Exam Configuration
- `duration_enabled`: Toggle time limit
- `randomize_questions`: Shuffle question order
- `is_active`: Manual open/close override
- `is_archived`: Soft-delete for exams
- `available_from/available_until`: Time window scheduling

### System Configuration
- Session timeout (30 minutes default)
- Password validation policies inherited from Django

---

## 13. FUTURE ENHANCEMENT OPPORTUNITIES

- Email notifications for violations
- Proctoring integration (webcam/microphone)
- Question pooling with difficulty levels
- Multi-language support
- Mobile-responsive design enhancements
- Two-factor authentication
- Audit trail for admin actions