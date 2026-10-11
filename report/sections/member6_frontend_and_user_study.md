# Member 6: Frontend Interface and User Study

## 6.1 Interface Design

### 6.1.1 Design goals

CrisisLens is a triage tool, not a social media feed. The interface must let a user (a) submit a crisis report in plain language, (b) understand what the model predicted and how confident it is, (c) correct the category if the model was wrong, and (d) search historical and community reports for context. Every design decision was guided by two constraints: the user is not a machine learning expert, and the tool must never be mistaken for an emergency service.

### 6.1.2 Technology choice

The frontend is built with NiceGUI, a Python framework that serves a reactive web interface from a single process. This choice keeps the entire stack in Python (matching the backend and models), avoids a JavaScript build toolchain, and lets the frontend share the same Pydantic-style schemas as the backend. NiceGUI renders Quasar (Vue.js) components server-side, so the frontend works in any modern browser without client-side JavaScript bundling.

### 6.1.3 Architecture

The frontend follows a pages-services-components structure:

| Layer | Path | Responsibility |
| --- | --- | --- |
| Pages | `app/frontend/pages/` | One file per route: home, submit, boards, board, search, review, report_detail, about |
| Services | `app/frontend/services/` | API client (real backend or mock fallback), geocoding |
| Components | `app/frontend/components/` | Reusable UI elements: cards, badges, location picker, form controls |
| Constants | `app/frontend/constants/` | 10-label display names, descriptions, icons, colours |
| Layout | `app/frontend/layout.py` | Shared header, navigation, safety notice, footer |
| Theme | `app/frontend/theme.py` | CSS token system, colour palette, Google Fonts (Inter) |

The service layer (`services/api.py`) is the only place pages talk to the backend. When `CRISISLENS_API_URL` is set, it calls the real REST API; otherwise it falls back to an in-memory mock backend for demo mode. This means the frontend works standalone for development and demonstration without requiring the model stack.

### 6.1.4 Label contract

The frontend enforces the 10-label contract strictly. If the backend returns an unknown label, the API service raises a `BackendError` rather than silently displaying it. Three dedicated tests (`test_frontend_labels.py`) verify this behaviour: known labels pass through unchanged, unknown labels are rejected, and related items with unknown labels are not relabelled.

Each label has a display name (e.g., "Urgent Needs" for `requests_or_urgent_needs`), a description, a Material icon, and a colour pair (background + foreground) meeting WCAG 4.5:1 contrast ratio. These are defined in `constants/labels.py` and used consistently across all pages.

## 6.2 User Flows

### 6.2.1 Report submission (three-step flow)

The submit page (`/submit`) guides the user through three steps:

1. **Describe.** A textarea for the crisis message (max 2,000 characters) and an optional location picker with map pin. A privacy notice reminds the user not to include personal information.
2. **Review category.** Clicking "Review report" sends the text to `POST /api/analyse`. The suggested category is shown with its confidence percentage. If the model is unsure (`needs_review=true`), a prominent alert asks the user to check the category. A dropdown lists all 10 categories, ordered by model probability, so the user can change the suggestion before publishing.
3. **Publish.** Clicking "Publish report" saves the report via `POST /api/reports` and redirects to the board page, where a success alert confirms the submission.

If the user edits the text after reviewing, the review step resets with a notice to re-run analysis. This prevents stale predictions from being published against changed text.

### 6.2.2 Board browsing

The boards page (`/boards`) shows all 10 categories as cards. Each board page (`/boards/{label}`) displays community reports (from SQLite) and related historical references (from the retrieval index). Community reports are paginated and filterable by status. A newly published report is highlighted at the top of its board.

### 6.2.3 Search

The search page (`/search`) combines keyword search and filtered browsing. Users can search by text query, filter by category, status, and source (community reports, historical dataset, or all). When a text query is provided, results come from Member 5's retrieval index (semantic + TF-IDF). Without a query, community reports are listed from SQLite with pagination.

### 6.2.4 Review queue

The review page (`/review`) lists reports where the model's confidence fell below the review threshold (tau=0.8866). Each item shows the full report text, the suggested category, and a dropdown to confirm or change it. Confirming a report sets its status to `resolved`. The queue automatically advances when the last item on a page is reviewed.

### 6.2.5 Report detail

Each report has a detail page (`/reports/{id}`) showing the full text, predicted label, board label (which may differ after correction), confidence, status, location, and related reports from the retrieval index.

## 6.3 Safety and Accessibility

### 6.3.1 Safety notices

The interface includes layered safety messaging:

- A persistent strip under the header on every page: "Not an emergency service. In danger, call your local emergency number first."
- The submit page has a larger safety box with specific numbers (000 in Australia, 112 internationally).
- A footer on every page: "Student prototype. Reports are not verified."
- Demo mode shows a banner: "Demo mode: reports and the classifier are simulated, and everything resets when the app restarts."

### 6.3.2 Status language

Status terminology was chosen to describe the category check, not the truthfulness of the report:

| Status | Display text | Meaning |
| --- | --- | --- |
| unverified | No category review needed | Model was confident; no human check required |
| needs_review | Category needs review | Model was unsure; flagged for human checking |
| resolved | Category reviewed | A person confirmed or corrected the category |

The submit page explicitly states: "Confirming records that a person checked the sorting. It does not mean the report has been verified as true."

### 6.3.3 Accessibility

- Skip-to-content link on every page (`<a class="crisis-skip-link" href="#crisis-main">`)
- `aria-current="page"` on active navigation links
- `role="note"` and `role="status"` on notice banners
- Mobile-responsive layout with a hamburger menu for small screens
- Page language set to English via script
- Inter font loaded from Google Fonts with `display=swap` for fast rendering

## 6.4 Demo and Mock Mode

When `CRISISLENS_API_URL` is not set, the frontend runs in demo mode using an in-memory mock backend (`services/mock_backend.py`). This provides:

- A mock classifier that returns plausible predictions with randomised confidence
- A mock retriever that returns synthetic related reports
- In-memory report storage that resets on restart
- A visible "Demo mode" banner so users know the data is simulated

A seed script (`scripts/seed_demo_reports.py`) populates the real backend with 9 representative demo reports across different categories, useful for demonstrations and screenshots.

## 6.5 User Study

*The user study is planned but has not yet been conducted. The protocol is documented here for completeness.*

### 6.5.1 Protocol

- Recruit 3 to 5 participants from different English-speaking backgrounds
- Tasks: submit a report, interpret the confidence display, correct a category, find related messages using search
- Measures: task completion rate, time on task, board choice accuracy, confidence comprehension, number and type of corrections made
- Results will be saved (anonymised) to `report/user_study/`
- At least one visible interface revision will be made from findings

### 6.5.2 Test scenarios

Participants will be given realistic disaster messages to submit, including:

- A clear-cut report: "Several families near the school need clean drinking water after the flood" (expected: Urgent Needs)
- An ambiguous report: "Volunteers are collecting blankets and water bottles at the community centre" (could be Rescue & Donations or Urgent Needs)
- A non-humanitarian message: "Sending prayers and thoughts to everyone affected" (expected: Sympathy & Support)
- A real-world scenario based on the October 2026 magnitude 4.8 earthquake near Leongatha, Victoria (felt in Melbourne's eastern suburbs): "Building shaking felt in south-east Melbourne, minor cracks in walls, power flickering on and off in Gippsland area"
