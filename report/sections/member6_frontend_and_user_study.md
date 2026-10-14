# Member 6: Frontend Interface and Usability

## 6.1 Design Concept

### 6.1.1 Starting points

The interface was designed around five observations about crisis information and the people who use it.

1. **Crisis information is scattered and hard to scan.** Reports, updates and requests for help are unstructured, so readers need ways to find what matters to them quickly.
2. **People arrive with different tasks.** Some want to report what they see, some look for a particular need such as water or shelter, some browse by topic, and some check the quality of the automatic sorting.
3. **Model output is uncertain, and reports are not verified.** The interface has to show what the classifier suggests without presenting it, or the report itself, as fact.
4. **Safety and privacy matter more than in an ordinary web application.** The tool must not be mistaken for an emergency service, and it must not encourage people to share personal details.
5. **People in a crisis have little time and attention.** Every step should be short, and the next step should be obvious.

### 6.1.2 Design principles

Four principles follow from these observations. They recur throughout the interface, and Section 6.2 shows how each one appears in the final design.

- **Show the model's output together with its uncertainty.** The suggested category appears with a confidence percentage, and an alert asks for a check when the model is unsure.
- **Keep the person in control.** Nothing is published before the person has seen the suggestion, the category can be changed before and after publishing, and the original suggestion is kept.
- **Separate what the system knows from what it does not.** Every community report is marked "Unverified", a reviewed category is not presented as verified fact, and historical results and demo data carry their own labels.
- **Ask for and show as little personal information as the task allows.** Location is optional and approximate, and historical tweets are anonymised.

Two terms are used throughout this section. A *category* is one of the ten HumAID labels. A *board* is the page that collects the community reports of one category.

### 6.1.3 Technology choice

The frontend is built with NiceGUI, a Python framework that serves a reactive web interface from a single process. This keeps the entire stack in Python, matching the backend and the models. NiceGUI describes the pages in Python on the server; in the browser, each element is shown as a Vue component, and Quasar supplies the Material Design components (NiceGUI, n.d.). No separate JavaScript build toolchain was needed in this project. The frontend talks to the backend only through the shared REST API, and it can also run on built-in demo data, so it could be developed and shown before the model stack was ready (Appendix A).

## 6.2 The Final Interface

### 6.2.1 Design highlights

- **Task-oriented entry points.** The home page offers a direct "Report a crisis" button, a search box, example searches, category links and the latest reports, so that each kind of reader can start from their own task.
- **Uncertainty made visible.** The suggested category is shown with its confidence, and a highlighted alert appears when the model is unsure.
- **A person has the last word.** Reporting is split into describe, review and publish, and the category can be changed at the review step and later on the report page.
- **Honest status language.** "Unverified" is attached to every community report, and a second badge only says whether the category was checked.
- **History kept apart from the present.** Past disasters appear as clearly marked, anonymised references, not as current reports.
- **Privacy built into location.** A location is optional, is included only after confirmation, and is shown as an area of about 800 m.

### 6.2.2 Home page

The home page (`/`) serves several tasks from one screen. A "Report a crisis" button sits in the first view for people who want to share what they see. The search box starts a search with Enter or the arrow button, and leaving it empty opens the full list of reports, which supports browsing without a query. Below it, four example searches ("water", "shelter", "medical help", "looking for family") open results directly, including historical examples, so that a first-time reader sees useful content at once. Six main categories are shown by default, with "View all 10" for the rest, to avoid a crowded start. The three latest community reports and their total appear beside them, giving readers an immediate view of recent activity. The header offers four destinations: Home, Report a crisis, Search and Review queue.

### 6.2.3 Reporting a crisis

Reporting is split into three steps on the submit page (`/submit`), so that a model suggestion is not published without the person having seen it.

1. **Describe.** The person writes the message (up to 2,000 characters) and may add a location. A place can be searched for, the device location can be used, or a point can be tapped on the map, and the location is included only after the person presses "Confirm location". A reminder asks them to leave out names, phone numbers and home addresses, and a box at the top gives emergency numbers (000 in Australia, 112 in many other countries).
2. **Review category.** The suggested category appears with its confidence as a percentage. If the model is unsure, a highlighted alert asks the person to check it. A drop-down lists all ten categories ordered by model probability, with a short description of the selected one, so the suggestion can be changed before publishing. Similar earlier reports are shown beneath it.
3. **Publish.** The report is saved and the board of its category opens, where a message confirms that it was published. The page states that a published report is visible to everyone and cannot be edited or deleted in this prototype.

Editing the text after the review resets the review step and asks for a new analysis. Without this, a prediction made for the old text could be published with the new one.

### 6.2.4 Browsing and searching

All ten categories are listed on `/boards`. Each board (`/boards/{label}`) shows its community reports, five to a page and filterable by status, followed by a few historical references that are marked as not current. A newly published report is highlighted on its board.

Search (`/search`) supports keyword queries and plain browsing, with filters for category, status and source (community reports, the historical dataset, or both). Community and historical results are visibly distinguished. Repeated copies of a historical message are grouped into one result with a "+N similar" note.

### 6.2.5 Report detail

Every saved community report has its own page (`/reports/{id}`), laid out as one card. It shows the text, the category and status, the time and place, and the model's original suggestion with its confidence. When a location was given, a map shows it as a circle of about 800 m instead of a pin, with links to open the same area in OpenStreetMap or Google Maps. A form on the same page lets anyone suggest a different category, and it opens by default for reports that still need review. Related reports are listed as single lines below.

### 6.2.6 Review queue and About page

Reports that the backend marks as needing review (`needs_review=true`, because the model's confidence fell below its review threshold) are collected in a queue at `/review`. Each entry shows the full text, the model's suggestion and a drop-down for confirming or changing the category, and confirming sets the status to `resolved`. The page states that anyone can review in this prototype and that a real deployment would limit the task to trained moderators.

An About page (`/about`) explains how CrisisLens works, what its categories can and cannot tell the reader, where the information comes from and how location data is handled.

### 6.2.7 Interaction details

Several smaller interaction choices reduce unnecessary effort. Search starts with Enter, the search box and filters stay under the header while the results scroll, and the example searches on the home page open straight on their results because the search page accepts a query and filters from the address. When a list is empty, the message explains why and suggests a next step, such as searching all sources. Each page has its own browser title, which helps when several tabs are open and when a screen reader announces the page, and each category keeps one colour and one icon on every page. A report page links back to its board, and the review step on the submit page lets the person return to editing before publishing.

## 6.3 Safety, Privacy, Ethics and Accessibility

### 6.3.1 Safety notices and status language

The same safety reminder is repeated at several levels, so that a reader who misses one message is likely to see another: a strip under the header on every page except the submit page ("Not an emergency service. In danger, call your local emergency number first."), the larger emergency box on the submit page, and a footer note ("Student prototype. Reports are not verified.").

Status terminology describes the category check, not the truthfulness of a report. Every community report carries an "Unverified" badge because no report is fact-checked. A second badge shows the category check:

| Status | Additional category-review badge | Meaning |
| --- | --- | --- |
| unverified | none | Model confidence was above the review threshold, so the report was not flagged for category review |
| needs_review | Category needs review | Model was unsure; flagged for human checking |
| resolved | Category reviewed | A person confirmed or corrected the category |

The review page states: "Confirming records that a person checked the sorting. It does not mean the report has been verified as true."

### 6.3.2 Privacy and data use

The interface is designed to ask for little personal information. A location is optional. A selected report location is included only after the person confirms it, and its coordinates are rounded to about 1 km before publication, so exact coordinates are not displayed on report cards or maps. The text of a report is written by the person, so the reminder on the submit form asks them to leave out names, phone numbers and home addresses. Historical tweets from HumAID are labelled as past examples, with @usernames anonymised to `@user` and links removed. A few external services are involved when the matching feature is used: place-search text may be sent to Photon (Komoot, n.d.), confirmed coordinates may be sent to Nominatim to look up a place name (OpenStreetMap Foundation, n.d.), OpenStreetMap supplies the map tiles, and Google Fonts supplies the font. The About page and the location form tell the reader about each of these.

### 6.3.3 Accessibility

Accessibility was considered at the level of page structure and interaction. Every page starts with a skip link to the main content and has one main heading, the current page is marked in the navigation (`aria-current="page"`), notices carry the `note` or `status` role, icon buttons and the logo have text labels, and the page language is set to English. Visible focus styles are provided for keyboard use, and animations are reduced when the system setting asks for it. The layout adapts to phone screens, with a collapsible navigation menu, because a phone may be the only device at hand in a crisis. The category colours and the main text colours were chosen with the WCAG AA minimum contrast ratio of 4.5:1 for normal text in mind (W3C, 2024).

### 6.3.4 Ethical considerations

A tool that sorts crisis information raises ethical questions beyond usability, and several design choices respond to them. The sections above describe each choice; this section brings them together.

- **Misinformation and over-reliance.** Reports are not fact-checked, and a model's suggestion can be wrong. The interface therefore marks every community report "Unverified", shows the model's confidence, asks for a check when the model is unsure, and words "Category reviewed" so that it is less likely to be read as verified information. The aim is to reduce the risk that readers treat an automatic label, or a report, as established fact.
- **Harm from relying on the wrong source in an emergency.** CrisisLens cannot send help. The safety line, the emergency numbers on the report form and the footer note repeat that people in danger should contact the emergency services first.
- **Privacy and personal data.** The interface asks for little personal information, keeps the location optional and approximate, and reminds people not to write names, phone numbers or home addresses in a report. It also tells people before publishing that a report is visible to everyone and cannot be edited or deleted in the prototype, so that they can decide with that in mind. External services that receive data, such as place search, are named in the About page and in the location form.
- **Use of real people's words.** The historical examples come from tweets written by real people during past disasters. They are labelled as past examples, with @usernames anonymised to `@user` and links removed, and are kept apart from current reports. The dataset's licence and terms need to be respected when the data is shared, as the repository README records.
- **Fairness and inclusion.** The interface and the models currently work in English only, and model performance may differ between disaster types and regions. This could leave some communities less well served, and the interface only partly reduces the risk through its confidence display and review step. The limitations in Section 6.5.5 describe what remains to be done.
- **Human oversight and accountability.** A person can correct the category before and after publishing, and uncertain reports go to a review queue, which gives people a way to catch the model's mistakes. The same openness is a weakness. In this prototype anyone can change a category or mark a report as reviewed, so a mistaken or malicious edit could mislabel a report or give it a false sign of having been checked. The model's original suggestion is kept, but earlier edits are not. A real deployment would need trained reviewers, a record of their decisions and a way to undo a change (Section 6.5.1).
- **Research ethics.** Participation in the planned user test would be voluntary. Records would be anonymised, without names or other identifying information, and no more personal data than needed would be stored.

## 6.4 Evaluation

This prototype has not been tested with real users. Its interface is instead assessed by design review: each usability risk of a crisis-reporting tool is paired with the design choice that addresses it. The review shows the reasoning behind the design, but it does not show that real users find the interface easy to use.

### 6.4.1 Design review

| Usability risk | Design response |
| --- | --- |
| A person may trust a model guess as a fact. | Every community report carries an "Unverified" badge. "Category reviewed" is worded so that it only means a person checked the category. |
| A person may not understand the model's confidence. | The suggested category is shown with a confidence percentage. Low confidence adds a highlighted alert asking the person to check the category. |
| The model may be wrong and a person may not be able to correct it. | The person has the last word: all ten categories are listed in order of model probability, and a published report can be re-categorised later. The original model suggestion is kept. |
| A stale prediction could be published after the text changed. | Editing the text resets the review step and asks the person to analyse again. |
| A person may share personal or exact location data. | A privacy reminder is shown, the location is optional, a pin is included only after "Confirm location", and its coordinates are rounded to about 1 km and drawn as a circle. |
| The tool may be mistaken for an emergency service. | A safety line on every page except the report form, a larger box with emergency numbers on the report form, and a footer note. |
| Search results from past disasters may look current. | Historical results are labelled "Historical reference", marked as not current, and shown with @usernames anonymised and links removed. |
| A person may mistake demo data for real data. | A "Demo mode" notice, and "Demo data" badges for seeded reports. |
| Slow or failed requests leave the person without feedback. | Loading placeholders, error messages with a "Try again" button, and an error instead of silent demo data when the backend is unreachable. |
| Small screens, keyboard navigation or low-contrast controls may make the interface harder to use. | A skip link, visible focus styles, a main heading on every page, colours chosen with the AA contrast ratio in mind, and a layout that adapts to phones. |

### 6.4.2 Planned user testing

The next step is a small usability test with real users, planned as follows:

- **Participants:** 3 to 5 people who are not on the project team, with varied English-language backgrounds.
- **Tasks:** submit a report, explain what the confidence display means, correct a wrong category, find related historical messages using search, and locate the review queue.
- **Measures:** task completion, time on task, whether the selected category matches the intended message, whether participants understand "Unverified" and "Category reviewed", and the number and type of corrections made.
- **Material:** short realistic disaster messages, and the 3 October 2026 earthquake near Leongatha, Victoria (preliminary magnitude 4.8; Geoscience Australia, 2026), for which 10 test reports have been prepared in `scripts/submit_earthquake_reports.py`.
- **Records:** results would be anonymised and stored in `report/user_study/`, without names or other identifying information.
- **Use of results:** findings should lead to at least one visible design change and should also be used to identify wider product issues, such as confusion about model confidence, trust in unverified reports, or difficulty distinguishing current reports from historical references.

Further evaluation should later include keyboard-only and screen-reader testing, testing on real mobile devices, and feedback from people with crisis-communication or emergency-management experience.

## 6.5 Product Limitations and Future Development

The prototype demonstrates the intended interaction design for the CrisisLens workflow, but several limitations remain before it could be treated as a reliable crisis-information product. They are described here for the product as a whole, as they appear at the interface, and each is followed by the development that would address it.

### 6.5.1 Credibility and moderation

The system does not verify whether a submitted report is true. Human review checks only the assigned category, and the "Unverified" label on every community report says so, but a production service would need stronger processes before reports could support operational decisions. At present a report becomes public as soon as it is published, anyone can submit reports and use the review function, and there is no way to flag a misleading, duplicate or harmful report. A published report also cannot be edited or deleted, which the interface states before publishing.

The correction and review functions are open in the same way. Anyone can change a report's category or mark it "Category reviewed", and the change takes effect at once, including in search results. A mistaken or malicious edit could therefore move an urgent report to a less visible board, or make an unchecked report look reviewed, and only the latest category is stored, with no history of earlier changes.

Future development should add authenticated reviewer roles, so that "Category reviewed" can only be set by a trained reviewer and other people's changes are shown as suggestions. A moderation workflow would keep an audit history that can be reverted and could send disputed changes to a second reviewer. Further additions are flagging of problematic reports and a way to request the withdrawal or correction of a report. Rate limiting and pre-moderation would give protection against spam and malicious submissions. Category review and factual verification should remain clearly separated.

### 6.5.2 Dependence on the models and communication of uncertainty

The usefulness of the interface depends on the performance and calibration of the underlying NLP models. Classification confidence is shown directly to users and decides whether a report enters the review queue, so poorly calibrated scores, or weaker performance on new types of disasters, would affect both trust and the amount of manual review. The model evaluation in the earlier sections does not establish performance across every disaster type, region or future distribution shift. The interface itself shows only a percentage, without any explanation of what it means.

Future development should monitor classification performance and calibration after deployment, and use low-confidence and corrected reports as evidence for later retraining. The presentation of confidence, uncertainty and historical similarity should be refined: a short explanation, a plain-language level or a simple visual could accompany the percentage, and user testing should decide which is easiest to understand without encouraging over-trust in the model.

### 6.5.3 Relevance and findability of information

Historical retrieval gives useful context, but similar wording may come from a different disaster, place or period, so it does not guarantee relevance to the current situation. The interface labels historical material as not current. Readers can narrow searches by category, status and source, but not by place, although reports already carry approximate locations. The pages do not refresh by themselves and offer no notifications, and a search cannot be bookmarked or sent to someone else, because the search page reads its query and filters from the address but does not write them back.

Future development should extend retrieval with time, location and disaster type, and use the approximate locations already attached to reports for area filters and a map view in which nearby reports are grouped, while keeping the current protections around exact coordinates. Automatic refresh, notifications for a chosen area and shareable searches would help readers follow a developing situation.

### 6.5.4 From organising information to supporting action

CrisisLens sorts and presents information, but it does not yet support the response that follows. The status describes only whether the category was checked, so a request cannot be marked as being handled or fulfilled, and a person who has submitted a report sees no follow-up. Potential users with different needs, such as affected people, responders, volunteers or donors, currently see the same screens, and the review queue handles entries one at a time.

Future development should add action states and follow-up, views adapted to the different groups of readers, and a review workflow that ranks entries by confidence or urgency and allows batch confirmation where appropriate.

### 6.5.5 Access and inclusion

The interface is English-only, and accessibility has not been tested with screen readers or other assistive technology. Areas that refresh, such as search results or the analysis result, are not marked as live regions, so these changes may not be announced. The interface needs a stable connection and loads fonts and map tiles from external services. When a request fails it shows a message asking the person to check the connection, but there is no lightweight or offline mode, although poor networks are common in disasters.

Future development should extend both the interface and the NLP pipeline to more languages, complete keyboard-only and screen-reader testing, add live regions and options such as larger text or higher contrast, and provide a lighter mode for weak connections.

### 6.5.6 Scale and reliability

The interface has been checked at small scale, for example with the nine demo reports, and not with sustained concurrent use or high submission volumes. System timing and failure results are reported in the backend and evaluation section. Before any public deployment, the product would also need monitoring, database backup and recovery procedures, and load testing.

Taken together, the next steps for the product are to explain model uncertainty better, add area-based browsing and action states, introduce moderation and access control, and test the interface with real users.

## Appendix A: Implementation Notes

### A.1 Architecture

The frontend follows a pages-services-components structure:

| Layer | Path | Responsibility |
| --- | --- | --- |
| Pages | `app/frontend/pages/` | One file per route: home, submit, boards, board, search, review, report_detail, about |
| Services | `app/frontend/services/` | API client, in-memory demo backend, place search (geocoding) |
| Components | `app/frontend/components/` | Reusable UI elements: cards, badges, location picker, form controls |
| Constants | `app/frontend/constants/` | Display names, descriptions, icons and colours of the ten labels |
| Layout | `app/frontend/layout.py` | Shared header, navigation, safety notice, footer |
| Theme | `app/frontend/theme.py` | CSS token system, colour palette, Google Fonts (Inter) |

The service layer (`services/api.py`) handles the communication between the pages and the backend. When `CRISISLENS_API_URL` is set, it calls the real REST API; otherwise it uses an in-memory demo backend. The choice is made once at start-up. If the real backend cannot be reached, the pages show an error and do not switch to demo data, which keeps simulated data from being mistaken for real data.

The frontend defines its own data classes (`schemas/api.py`) that follow the shared API contract. Search results do not always carry a time, status or location, so the frontend asks the report detail for any that a community result lacks.

### A.2 Label contract

The frontend accepts only the ten shared labels. When the backend returns any other label, the API service raises a `BackendError`; it neither displays the label nor maps it to another category, and the page shows an error message instead. A silent fallback would have hidden a mismatch between the model and the interface, so failing visibly was judged safer. Three dedicated tests (`test_frontend_labels.py`) verify this behaviour: known labels pass through unchanged, unknown labels are rejected, and related items with unknown labels are not relabelled.

Each label also has a display name (for example "Urgent Needs" for `requests_or_urgent_needs`), a short description, an icon and a colour pair. The colours were chosen with the WCAG AA minimum contrast ratio of 4.5:1 for normal text in mind (W3C, 2024). All of these are defined once in `constants/labels.py`, so a category looks the same on every page.

### A.3 Demo mode

Without `CRISISLENS_API_URL`, the frontend runs in demo mode on an in-memory demo backend (`services/mock_backend.py`). It offers:

- A keyword classifier whose confidence comes from the number of matching keywords
- A lightweight retriever that ranks the demo reports by the overlap of their content words, matched loosely by word stem
- In-memory report storage that resets on restart
- A visible "Demo mode" banner, so that the data is not taken for real

A fresh backend database may initially be empty, which makes its boards look unused. A seed script (`app/frontend/scripts/seed_demo_reports.py`) therefore adds nine demo reports across different categories for demonstrations and screenshots, and the interface marks them "Demo data". Instructions for running and deploying the frontend are in the repository README.

## References

Geoscience Australia (2026) *Preliminary magnitude 4.8 earthquake recorded near Melbourne, Victoria*. Available at: https://www.ga.gov.au/news/earthquake-information-for-media-outlets (Accessed: 12 October 2026).

Komoot (n.d.) *Photon, search-as-you-type with OpenStreetMap*. Available at: https://photon.komoot.io/ (Accessed: 12 October 2026).

NiceGUI (n.d.) *Technological Foundations*. Available at: https://nicegui.io/documentation/section_foundations (Accessed: 12 October 2026).

OpenStreetMap Foundation (n.d.) *Nominatim Usage Policy (aka Geocoding Policy)*. Available at: https://operations.osmfoundation.org/policies/nominatim/ (Accessed: 12 October 2026).

World Wide Web Consortium (W3C) (2024) *Web Content Accessibility Guidelines (WCAG) 2.2*. Available at: https://www.w3.org/TR/WCAG22/ (Accessed: 12 October 2026).
