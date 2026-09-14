# Security Platform Worklog

Date: 2026-09-15

Domains:
- security.tawreedflow.com
- security.shajjadkhan.com

Server:
- Host: tserver@10.12.14.16
- Project path: /home/tserver/security_dept
- Framework: Django

Working rule:
- Test on tserver before production deployment.
- Do not deploy to production until checks/tests pass.
- Keep this file updated with inspected, changed, tested, and deployed work.

## Product Direction

This is a SaaS platform for property security departments.

Primary hierarchy:
- SaaS owner / master admin: sells and manages the service across client properties.
- Cluster security director: client-side superior user who can manage multiple properties.
- Admin / supervisor: manages assigned property operations, or multiple properties only when granted cluster access.
- Staff / officer: simple operational user for gate entries, visitor entry, material passes, and follow-up.

Key workflows:
- Property and cluster management.
- Red card material movement: item leaves permanently and does not return.
- Green card material movement: item must return on schedule, with overdue follow-up.
- Visitor entry: replace paper/manual entry with searchable, follow-up-able records.
- Gates, departments, staff, lost-and-found, audit records, billing, Arabic/English UI.

## 2026-09-15 Baseline

Inspected tserver project and confirmed existing modules:
- `core`: properties, gates, custom users, subscriptions, dashboards, admin views, translations.
- `gatepass`: red/green cards, return tracking, items, WhatsApp reminder links.
- `visitors`: visitor pass, host department, checkout and overstay tracking.
- `lostfound`: lost-and-found custody records.
- `templates`: dashboard, SaaS admin hub, gatepass/visitor/lostfound pages.

Baseline validation before code changes:
- `./venv/bin/python manage.py check`: passed, no issues.
- `./venv/bin/python manage.py test`: initially ran 0 tests.

## 2026-09-15 Access-Control Fix

Changed:
- Non-owner unassigned users now see no properties instead of falling back to all active properties.
- Dashboard, gates, visitor, gatepass, lost-and-found, search, and audit views now scope data to the user's accessible properties.
- Property switching now requires access to the requested property.
- SaaS billing collection, suspension/reactivation, and monthly invoice generation are restricted to SaaS owner / superuser.
- Directors and cluster managers can manage only their accessible property scope.
- User creation/editing constrains assigned properties, gates, and cluster properties to the manager's accessible properties.
- Template role checks in `base.html` now use server-provided booleans instead of string membership checks.
- Visitor list now handles visitors without a host department.
- New audit entries for visitors, gate passes, and lost-and-found include property/gate links for scoped audit visibility.
- Added Django tests for property isolation and SaaS billing boundary.

Validation after changes:
- `./venv/bin/python manage.py check`: passed.
- `./venv/bin/python manage.py test core`: 4 tests passed.
- `./venv/bin/python manage.py test`: 4 tests passed.

Pre-change backup on tserver:
- `/tmp/security_dept_pre_access_fix.tgz`

