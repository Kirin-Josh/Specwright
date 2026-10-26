import type { Plan, Requirement, ReviewIssue } from "./types";

// A small fake spec so the UI can be built before the API is ready.

export const mockRequirements: Requirement[] = [
  {
    req_id: "EF-01",
    text: "Users sign in with email and password.",
    type: "functional",
    section: "Authentication",
  },
  {
    req_id: "EF-02",
    text: "Admins can create, edit and archive rooms.",
    type: "functional",
    section: "Rooms",
  },
  {
    req_id: "EF-03",
    text: "Members can book a room for a time slot.",
    type: "functional",
    section: "Bookings",
  },
  {
    req_id: "EF-04",
    text: "A booking cannot overlap another booking.",
    type: "functional",
    section: "Bookings",
  },
  {
    req_id: "EF-05",
    text: "Members receive an email confirmation.",
    type: "functional",
    section: "Notifications",
  },
  {
    req_id: "ES-01",
    text: "Lock an account after 5 failed sign-in attempts.",
    type: "security",
    section: "Security",
  },
  {
    req_id: "ET-01",
    text: "API responses under 300 ms at p95.",
    type: "technical",
    section: "Performance",
  },
  {
    req_id: "CA-01",
    text: "A member can book and cancel end to end.",
    type: "acceptance",
    section: "Acceptance",
  },
];

export const mockPlan: Plan = {
  milestones: [
    {
      id: "M1",
      name: "Foundation & auth",
      goal: "Users can sign in securely.",
    },
    {
      id: "M2",
      name: "Rooms & bookings",
      goal: "Members can book rooms without conflicts.",
    },
    {
      id: "M3",
      name: "Polish & acceptance",
      goal: "Notifications, performance and sign-off.",
    },
  ],
  tasks: [
    {
      id: "T-001",
      milestone_id: "M1",
      title: "Auth API: sign-in and session",
      description: "Email/password sign-in, session cookie, /me endpoint.",
      label: "BE",
      estimate: 3,
      priority: 1,
      requirement_ids: ["EF-01"],
      depends_on: [],
    },
    {
      id: "T-002",
      milestone_id: "M1",
      title: "Sign-in page",
      description: "Form, validation, error states, redirect after sign-in.",
      label: "FE",
      estimate: 2,
      priority: 1,
      requirement_ids: ["EF-01"],
      depends_on: ["T-001"],
    },
    {
      id: "T-003",
      milestone_id: "M1",
      title: "Account lockout after failed attempts",
      description: "Count failures per account; lock after 5; admin unlock.",
      label: "BE",
      estimate: 2,
      priority: 2,
      requirement_ids: ["ES-01"],
      depends_on: ["T-001"],
    },
    {
      id: "T-004",
      milestone_id: "M2",
      title: "Rooms CRUD API",
      description: "Create, edit, archive rooms. Admin only.",
      label: "BE",
      estimate: 3,
      priority: 2,
      requirement_ids: ["EF-02"],
      depends_on: ["T-001"],
    },
    {
      id: "T-005",
      milestone_id: "M2",
      title: "Bookings API with overlap check",
      description:
        "Create/cancel bookings; reject overlapping slots in a transaction.",
      label: "BE",
      estimate: 5,
      priority: 1,
      requirement_ids: ["EF-03", "EF-04"],
      depends_on: ["T-004"],
    },
    {
      id: "T-006",
      milestone_id: "M2",
      title: "Booking calendar screen",
      description: "Pick a room and slot, show conflicts, confirm.",
      label: "FE",
      estimate: 5,
      priority: 2,
      requirement_ids: ["EF-03"],
      depends_on: ["T-005"],
    },
    {
      id: "T-007",
      milestone_id: "M3",
      title: "Booking confirmation email",
      description: "Send email on create and cancel.",
      label: "BE",
      estimate: 2,
      priority: 3,
      requirement_ids: ["EF-05"],
      depends_on: ["T-005"],
    },
    {
      id: "T-008",
      milestone_id: "M3",
      title: "E2E: book and cancel",
      description: "Playwright test covering the full booking flow.",
      label: "QA",
      estimate: 3,
      priority: 2,
      requirement_ids: ["CA-01"],
      depends_on: ["T-006"],
    },
  ],
};

// ET-01 is deliberately left uncovered so the coverage view has something to show.
export const mockIssues: ReviewIssue[] = [
  {
    kind: "uncovered",
    detail: "ET-01 has no task",
    task_ids: [],
    requirement_ids: ["ET-01"],
  },
];
