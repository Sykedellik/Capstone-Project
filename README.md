# Secure Online Examination System
## BSIS Capstone Project - Cybersecurity Specialization

[![Django](https://img.shields.io/badge/Django-6.0.3-blue)](https://djangoproject.com)
[![Python](https://img.shields.io/badge/Python-3.x-yellow)](https://python.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.x-teal)](https://tailwindcss.com)

**Automated proctored exam platform with integrity scoring.**

## ✨ **Features**
- 🔐 Secure role-based authentication (Student/Instructor)
- 📚 Subject assignment + dynamic question banks
- 🎲 Randomized questions per student
- 👮‍♂️ **Browser proctoring** (tab/copy/devtools detection)
- 📊 Integrity scoring + risk classification (LOW/HIGH/CRITICAL)
- 📈 Instructor analytics + CSV/PDF reports
- 📱 Fully responsive Tailwind UI

## 🚀 **Quick Start**
```bash
cd d:/Capstone
pip install -r requirements.txt  # Or manual: django pytz
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
**Demo:** http://127.0.0.1:8000/

**Register** → **Student/Instructor** → **Test full flow**

## 📁 **Structure**
```
Capstone/
├── exam_system/     # Core app (models/views/templates)
├── docs/            # Academic documentation
├── db.sqlite3       # Data (21 migrations)
└── manage.py
```

## 🔒 **Cybersecurity Highlights**
```
Integrity Algorithm:
score = 100 - Σ(penalties)
Risk: LOW(≥80) | MEDIUM(≥50) | HIGH(≥25) | CRITICAL(<25)
Events: tab_switch(5), copy(8), devtools(15), ...
```

## 📖 **Documentation**
- [Full Specs](docs/capstone_secure_exam_system.md) - 2,500+ words
- [TODO/Progress](TODO.md)

## 🎓 **Academic Context**
**BSIS Capstone** - Automates manual proctoring with **cybersecurity-driven integrity monitoring**.

**Professor Objectives:** All 5 met ✅

## 🤝 **License**
MIT - Free for educational/institutional use.

