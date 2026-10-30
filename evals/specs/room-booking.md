# Meeting Room Booking — Software Requirements Specification

Version 1.2 · Facilities team · Synthetic spec written for Specwright evals

## 1. Context

The company has 40 meeting rooms across two buildings. Bookings are tracked today in a shared
spreadsheet, which leads to double bookings and rooms held by people who never show up.
This document describes a web application that replaces the spreadsheet. Requirement FR-04
below addresses the no-show problem directly; it is verified by AC-03.

### 1.1 Users and roles

| Role | Description |
|---|---|
| Employee | Any staff member with a company account |
| Facilities manager | Manages rooms and sees usage reports |
| Administrator | Manages user roles |

## 2. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | An employee can search for free rooms by date, time slot, building and minimum capacity. |
| FR-02 | An employee can book a free room for a slot of 15 minutes to 4 hours, in 15-minute steps. |
| FR-03 | The system refuses a booking that overlaps an existing booking of the same room. |
| FR-04 | A booking that is not checked in within 10 minutes of its start is released automatically and the room becomes free again. |
| FR-05 | An employee can cancel or shorten their own booking until it starts. |

- **FR-06** — An employee receives an email confirmation when a booking is created, changed or released, including a calendar (.ics) attachment.
- **FR-07** — A facilities manager can create, edit and deactivate rooms, with name, building, floor, capacity and equipment (screen, video conferencing, whiteboard).
- **FR-08** — A facilities manager can see a monthly usage report per room: hours booked, hours actually used, and the no-show rate. The report can be exported as CSV.

## 3. Security requirements

- **SEC-01** — Users sign in with the company single sign-on (OpenID Connect); there are no local passwords.
- **SEC-02** — Only facilities managers can manage rooms and see reports; only administrators can change user roles.
- **SEC-03** — Every booking change (create, change, cancel, release) is written to an audit log with the user, the time and the previous values, kept for 12 months.

## 4. Technical requirements

- **TECH-01** — The backend exposes a REST API documented with OpenAPI; the web front end uses only this API.
- **TECH-02** — Data is stored in PostgreSQL; the booking overlap rule of FR-03 is also enforced by a database constraint.
- **TECH-03** — The room search of FR-01 answers in under 500 ms for 40 rooms and 10,000 bookings.

## 5. Acceptance criteria

- **AC-01** — Two employees try to book the same room for overlapping slots at the same moment: exactly one booking succeeds, the other gets a clear error. (Covers FR-02, FR-03, TECH-02.)
- **AC-02** — An employee books, shortens, then cancels a booking and receives three emails with valid calendar attachments. (Covers FR-05, FR-06.)
- **AC-03** — A booking with no check-in is released 10 minutes after its start, the room shows as free in search, and the release appears in the audit log. (Covers FR-04, FR-01, SEC-03.)
- **AC-04** — A facilities manager exports the monthly report and the no-show rate matches the released bookings for that month; an employee cannot open the report. (Covers FR-08, SEC-02.)

## 6. Out of scope for this version

- **OOS-01** — A native mobile application.
- **OOS-02** — Booking desks or parking spaces.
- **OOS-03** — Charging internal cost centres for room use.

## 7. Glossary

- **Check-in** — confirming presence in the room, from the room's tablet or from the booking page.
- **No-show rate** — released bookings divided by all bookings in the period.
