# Member 6: Frontend Interface and Usability

## 6.1 Interface Design

### 6.1.1 Design goals

CrisisLens is meant to help people sort crisis information, not to replace an emergency service or a social media feed. The interface has to let a person (a) describe a situation in everyday language, (b) see what the model predicted and how sure it is, (c) correct the category when the model is wrong, and (d) look through community reports and past disasters for context. Two constraints guided the design. The people using it are not machine learning experts, and the tool should not be mistaken for an emergency service.

Two terms are used throughout this section. A *category* is one of the ten HumAID labels. A *board* is the page that collects the community reports of one category.

### 6.1.2 Technology choice

The frontend is built with NiceGUI, a Python framework that serves a reactive web interface from a single process. This choice keeps the entire stack in Python, matching the backend and models. The frontend defines its own data classes (`schemas/api.py`) that follow the shared API contract. NiceGUI describes the pages in Python on the server; in the browser, each element is shown as a Vue component, and Quasar supplies the Material Design components (NiceGUI, n.d.). No separate JavaScript build toolchain was needed in this project.

### 6.1.3 Architecture

The frontend follows a pages-services-components structure:

| Layer | Path | Responsibility |
| --- | --- | --- |
| Pages | `app/frontend/pages/` | One file per route: home, submit, boards, board, search, review, report_detail, about |
| Services | `app/frontend/services/` | API client, in-memory demo backend, place search (geocoding) |
| Components | `app/frontend/components/` | Reusable UI elements: cards, badges, location picker, form controls |
| Constants | `app/frontend/constants/` | Display names, descriptions, icons and colours of the ten labels |
| Layout | `app/frontend/layout.py` | Shared header, navigation, safety notice, footer |
| Theme | `app/frontend/theme.py` | CSS token system, colour palette, Google Fonts (Inter) |

The service layer (`services/api.py`) handles the communication between the pages and the backend. When `CRISISLENS_API_URL` is set, it calls the real REST API; otherwise it uses an in-memory demo backend. The choice is made once at start-up. If the real backend cannot be reached, the pages show an error and do not switch to demo data, which keeps simulated data from being mistaken for real data. The frontend can therefore be developed and demonstrated without the model stack.

### 6.1.4 Label contract

The frontend accepts only the ten shared labels. When the backend returns any other label, the API service raises a `BackendError`; it neither displays the label nor maps it to another category, and the page shows an error message instead. A silent fallback would have hidden a mismatch between the model and the interface, so failing visibly was judged safer. Three dedicated tests (`test_frontend_labels.py`) verify this behaviour: known labels pass through unchanged, unknown labels are rejected, and related items with unknown labels are not relabelled.

Each label also has a display name (for example "Urgent Needs" for `requests_or_urgent_needs`), a short description, an icon and a colour pair. The colours were chosen with the WCAG AA minimum contrast ratio of 4.5:1 for normal text in mind (W3C, 2024). All of these are defined once in `constants/labels.py`, so a category looks the same on every page.

## 6.2 User Flows

### 6.2.1 Report submission (three-step flow)

Reporting is split into three steps on the submit page (`/submit`), so that a model suggestion is not published without the person having seen it.

1. **Describe.** The person writes the message in a text box (up to 2,000 characters) and may add a location. A place can be searched for, the device location can be used, or a point can be tapped on the map. The location is included in the report only after the person presses "Confirm location". A reminder asks them to leave out names, phone numbers and home addresses.
2. **Review category.** "Review report" sends the text to `POST /api/analyse`. The suggested category appears with its confidence as a percentage. If the model is unsure (`needs_review=true`), a highlighted alert asks the person to check the category. A drop-down lists all ten categories, ordered by model probability, so the suggestion can be changed before publishing. Reports similar to the draft are shown beneath it.
3. **Publish.** "Publish report" saves the report through `POST /api/reports` and opens the board of its category, where a message confirms that the report was published.

Editing the text after the review resets the review step and asks for a new analysis. Without this, a prediction made for the old text could be published with the new one.

### 6.2.2 Board browsing

All ten categories are listed as cards on `/boards`. Opening one leads to its board (`/boards/{label}`), which combines two kinds of content. The community reports come from SQLite, five to a page, and can be filtered by status. Below them, a few historical references from the retrieval index give context from earlier disasters and are marked as not current. A report that was just published is highlighted on its board.

### 6.2.3 Search

Search (`/search`) supports keyword queries and plain browsing, with filters for category, status and source (community reports, the historical dataset, or both). Keyword queries and historical results come from the search endpoint, while browsing community reports without a query uses the report-list endpoint, with pagination. Community and historical results are visibly distinguished. Details such as category, time, status and location are shown when the API provides them, and the frontend asks the report detail for any that a community result lacks. Repeated copies of a historical message are grouped into one result with a "+N similar" note where the retrieval results support it.

### 6.2.4 Review queue

Reports that the backend marks as needing review (`needs_review=true`, because the model's confidence fell below its review threshold) are collected in a queue at `/review`. Each entry shows the full text, the model's suggestion and a drop-down for confirming or changing the category; confirming sets the status to `resolved`. The queue returns to the previous page after its last entry on a page has been reviewed. The page states that anyone can review in this prototype, and that a real deployment would limit the task to trained moderators.

### 6.2.5 Report detail

Every saved community report has its own detail page (`/reports/{id}`). It shows the full text, the category and status, the model's original suggestion with its confidence, and related reports from the retrieval index. The suggestion is kept even when a person later changes the category. When a location was given, a map shows it as a circle of about 800 m instead of a pin, with links to open the same area in OpenStreetMap or Google Maps. A form on the same page lets anyone suggest a different category; it opens by default for reports that still need review.

### 6.2.6 Home and About pages

The home page (`/`) offers a search box with example searches, the six main categories (the rest can be expanded) and the three latest community reports. An About page (`/about`) explains how CrisisLens works, what its categories can and cannot tell the reader, where the information comes from and how location data is handled.

### 6.2.7 Small design details

Several smaller choices were made to save the reader effort:

- The search page accepts the query and the filters from the address, so the example searches on the home page open straight on their results.
- On the search page the search box and filters stay under the header while the results scroll, so a filter can be changed without scrolling back up.
- Pressing Enter starts a search, and a long result list is split into pages.
- Each page has its own browser title, such as "Urgent Needs · CrisisLens", which helps when several tabs are open and when a screen reader announces the page.
- When a list is empty, the message says why and offers a next step, for example "Report a crisis" on an empty home page or "Search all sources" when a community-only search finds nothing.
- A report page links back to its board, and the submit page offers "Back to editing" at the review step.
- Each category keeps one colour and one icon on every page, and the home page shows only the six main categories at first to avoid a crowded start.

## 6.3 Safety and Accessibility

### 6.3.1 Safety notices

The same reminder is repeated at several levels, so that a reader who misses one message is likely to see another:

- A strip under the header on every page except the submit page: "Not an emergency service. In danger, call your local emergency number first."
- The submit page has a larger safety box with specific numbers (000 in Australia, 112 in many other countries).
- A footer on every page: "Student prototype. Reports are not verified."
- Demo mode shows a banner: "Demo mode: reports and the classifier are simulated, and everything resets when the app restarts."

### 6.3.2 Status language

Status terminology was chosen to describe the category check, not the truthfulness of the report. Every community report carries an "Unverified" badge, because no report is fact-checked. A second badge shows the category check:

| Status | Additional category-review badge | Search filter wording | Meaning |
| --- | --- | --- | --- |
| unverified | none | No category review needed | Model confidence was above the review threshold, so the report was not flagged for category review |
| needs_review | Category needs review | Category needs review | Model was unsure; flagged for human checking |
| resolved | Category reviewed | Category reviewed | A person confirmed or corrected the category |

The review page explicitly states: "Confirming records that a person checked the sorting. It does not mean the report has been verified as true."

### 6.3.3 Accessibility

Accessibility was considered at the level of page structure and interaction. Every page starts with a skip link to the main content, headings follow a logical order, the current page is marked in the navigation (`aria-current="page"`), notices carry the `note` or `status` role, and the page language is set to English. Visible focus styles are provided for keyboard use. The layout adapts to phone screens, with a collapsible navigation menu, because a phone may be the only device at hand in a crisis. The category colours and the main text colours were chosen with the WCAG AA minimum contrast ratio in mind (W3C, 2024). The Inter font is loaded from Google Fonts with `display=swap`, so text appears before the font arrives.

### 6.3.4 Privacy and data use

The interface is designed to ask for little personal information. A location is optional. A selected report location is included only after the person confirms it, and its coordinates are rounded to about 1 km before publication, so exact coordinates are not displayed on report cards or maps. The text of a report is written by the person, so the reminder on the submit form asks them to leave out names, phone numbers and home addresses. Historical tweets from HumAID are labelled as past examples, with @usernames anonymised to `@user` and links removed. A few external services are involved when the matching feature is used: place-search text may be sent to Photon (Komoot, n.d.), confirmed coordinates may be sent to Nominatim to look up a place name (OpenStreetMap Foundation, n.d.), OpenStreetMap supplies the map tiles, and Google Fonts supplies the font. The About page and the location form tell the reader about each of these.

## 6.4 Demo Mode

Without `CRISISLENS_API_URL`, the frontend runs in demo mode on an in-memory demo backend (`services/mock_backend.py`). It offers:

- A keyword classifier whose confidence comes from the number of matching keywords
- A lightweight retriever that ranks the demo reports by the overlap of their content words, matched loosely by word stem
- In-memory report storage that resets on restart
- A visible "Demo mode" banner, so that the data is not taken for real

A fresh backend database may initially be empty, which makes its boards look unused. A seed script (`app/frontend/scripts/seed_demo_reports.py`) therefore adds nine demo reports across different categories for demonstrations and screenshots, and the interface marks them "Demo data". Instructions for running and deploying the frontend are in the repository README.

## 6.5 Usability Evaluation and Further Work

This prototype has not been tested with real users. Its interface is instead assessed by design review: each usability risk of a crisis-reporting tool is paired with the design choice that addresses it. The review shows the reasoning behind the design, but it does not show that real users find the interface easy to use.

### 6.5.1 Design review

| Usability risk | Design response | Where |
| --- | --- | --- |
| A person may trust a model guess as a fact. | Every community report carries an "Unverified" badge. "Category reviewed" is worded so that it only means a person checked the category. | `components/badges.py`, review page |
| A person may not understand the model's confidence. | The suggested category is shown with a confidence percentage. Low confidence adds a highlighted alert asking the person to check the category. | submit page |
| The model may be wrong and a person may not be able to correct it. | The person has the last word: all ten categories are listed in order of model probability, and a published report can be re-categorised later. The original model suggestion is kept. | submit page, report detail |
| A stale prediction could be published after the text changed. | Editing the text resets the review step and asks the person to analyse again. | submit page |
| A person may share personal or exact location data. | A privacy reminder is shown, the location is optional, a pin is included only after "Confirm location", and its coordinates are rounded to about 1 km and drawn as a circle. | location picker, detail map |
| The tool may be mistaken for an emergency service. | A safety line on every page except the report form, a larger box with emergency numbers on the report form, and a footer note. | `layout.py`, submit page |
| Search results from past disasters may look current. | Historical results are labelled "Historical reference", marked as not current, and shown with @usernames anonymised and links removed. | report cards |
| A person may mistake demo data for real data. | A "Demo mode" notice, and "Demo data" badges for seeded reports. | `layout.py`, badges |
| Slow or failed requests leave the person without feedback. | Loading placeholders, error messages with a "Try again" button, and an error instead of silent demo data when the backend is unreachable. | pages, `ui_kit.py` |
| Small screens, keyboard navigation or low-contrast controls may make the interface harder to use. | A skip link, visible focus styles, semantic headings, colours chosen with the AA contrast ratio in mind, and a layout that adapts to phones. | `base.css`, `layout.py` |

### 6.5.2 Limits of this evaluation

- No external usability study was conducted, so ease of use, the reading of the confidence display and the discoverability of the correction step have not been empirically validated.
- Accessibility features were inspected in the browser, but the prototype was not evaluated with screen readers or users of assistive technology.
- Testing used a relatively small set of reports, such as the nine demo reports. Behaviour with large datasets and concurrent use was not evaluated.
- The usefulness of the displayed confidence depends on the calibration of the underlying classifier, which is evaluated separately in the model sections.
- The prototype is English-only, and the review queue has no authentication or role-based access control.

### 6.5.3 Further work: user testing

The next step is a small usability test with real users, planned as follows:

- **Participants:** 3 to 5 people who are not on the project team.
- **Tasks:** submit a report, say what the confidence display means, correct a wrong category, find related past messages with search, and find the review queue.
- **Measures:** task completion, time on task, whether the board they chose matches the message, whether they understand "Unverified" and "Category reviewed", and the number and type of corrections made.
- **Material:** short realistic disaster messages, for example "Several families near the school need clean drinking water after the flood" (Urgent Needs), "Volunteers are collecting blankets and water bottles at the community centre" (could be Rescue & Donations or Urgent Needs) and "Sending prayers and thoughts to everyone affected" (Sympathy & Support). A real-world scenario is also available: the 3 October 2026 earthquake near Leongatha, Victoria (preliminary magnitude 4.8; Geoscience Australia, 2026). The 10 test reports for it are in `scripts/submit_earthquake_reports.py`, for example "Minor cracks appearing in the walls of our apartment building in Dandenong after the earthquake. Power flickered but came back."
- **Use of results:** the findings should lead to at least one visible interface change, such as clearer wording for the status badges or a more visible way to reach the correction form.

Other further work is a screen-reader and keyboard-only check, a test on real phones, and a wording check by people with a crisis-communication background.

### 6.5.4 Planned interface improvements

Beyond the user test, the following changes to the interface would build on the current design:

- **Clearer confidence display.** The percentage could be accompanied by a short explanation, or by a simple visual such as a bar or a plain-language level, so that readers who are unfamiliar with model confidence can interpret it. Which form works best would be decided in the user test.
- **Guidance while writing.** A few prompts or examples of what makes a report useful (what happened, where, when) could appear beside the text box, to help people who are unsure what to write.
- **Map view of reports.** The approximate locations that reports already carry could be shown together on one map, grouped when they are close, so that readers can browse by area as well as by category.
- **Shareable searches.** The query and filters are currently read from the address but not written back to it. Keeping them in sync would let a search be bookmarked or sent to someone else.
- **A faster review queue.** Sorting the queue by confidence, and confirming several reports at once, would help a reviewer who faces many entries.
- **Interface text in more languages.** Translating the interface, together with a language choice, would make it usable for more of the people affected by a disaster.
- **Wider accessibility checks.** Beyond the checks described above, the interface could offer larger text or a high-contrast option, and be tested with a screen reader.

## References

Geoscience Australia (2026) *Preliminary magnitude 4.8 earthquake recorded near Melbourne, Victoria*. Available at: https://www.ga.gov.au/news/earthquake-information-for-media-outlets (Accessed: 12 October 2026).

Komoot (n.d.) *Photon, search-as-you-type with OpenStreetMap*. Available at: https://photon.komoot.io/ (Accessed: 12 October 2026).

NiceGUI (n.d.) *Technological Foundations*. Available at: https://nicegui.io/documentation/section_foundations (Accessed: 12 October 2026).

OpenStreetMap Foundation (n.d.) *Nominatim Usage Policy (aka Geocoding Policy)*. Available at: https://operations.osmfoundation.org/policies/nominatim/ (Accessed: 12 October 2026).

World Wide Web Consortium (W3C) (2024) *Web Content Accessibility Guidelines (WCAG) 2.2*. Available at: https://www.w3.org/TR/WCAG22/ (Accessed: 12 October 2026).
