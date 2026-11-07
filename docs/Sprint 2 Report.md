# Sprint 2 Report

**Team/Project Name:** Team 3 PNW RoadWatch  
**Sprint Dates:** Sprint 2 - October 13 to November 5  
**Demo Video Link:** https://youtu.be/JJt2sawljGE

## 1. Work Completed

List the main features, bug fixes, or tasks completed. Include the corresponding GitHub issue links.

- **Location feature:** Displays the user's current location on the map. — https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/22
- **Directions feature:** Users can enter a start and destination using Google Places. Both locations are validated to be in Washington, Oregon or Idaho. Out-of-region input displays an error. — https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/4
- **Normalized alerts database:** Built a normalization layer that converts the WSDOT, ODOT, and Idaho 511 formats into one common alert schema (ID, location, type, severity, description, last updated, source agency). Bad records are skipped instead of crashing a whole state's feed. — https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/5
    - Connect all APIs: Added a fetch module for each agency (`WA.py` for WSDOT, `OR.py` for ODOT, `ID.py` for Idaho 511) that pulls live alert data. API keys are loaded from a `.env` file rather than hard-coded, and WSDOT's timestamp format is converted into a usable date. - https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/1, https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/2, https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/12
- **Back-end:** Built a backend that passes normalized alert data from WSDOT, ODOT, and Idaho 511 to the map. — https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/13, https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/29 
- **Real-time alerts:** The map now shows current road and weather alerts from the WA, OR, and ID DOTs instead of mock data. If one state's API goes down, the other states still load. If nothing is available, the map shows its warning banner. — https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/3
- **Front-end:** - Restyled the website with plain CSS so it looks polished and consistent. Added a defined color palette, a font hierarchy, and a styled header showing the PNW RoadWatch name. The route inputs, buttons, directions panel, and map now sit in styled cards and containers with consistent spacing. All existing features work as before. — https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/30

## 2. Incomplete Work

List unfinished tasks, why they remain incomplete, and the next step. Write **“None”** if all planned work is complete.

| Task / GitHub Issue | Reason Incomplete | Next Step |
|---|---|---|
| Normalizing Data | The mapping of the data priority level to alert severity level is functional but incomplete. It needs to be refined. | Compile complete list of external API returns and make sure they're mapped. |
| Backend Deployement | The backend is currently being deployed on Render on the free tier. So, our NFR-03 (scaling to 1000 users) is not possible on our current setup. | To fix this, we would use a paid service. |

## 3. Team Contributions

Briefly describe each member’s contribution.

| Team Member | Main Contribution |
|---|---|
| Anastasia Chepel | Location feature and directions feature |
| Abby Gardner | Normalized alerts database and connection of all APIs |
| Himanshi Vasani | Backend setup and real-time alerts |
| Emily Tran | Frontend responsive layout and style improvements |

## 4. Code for Review

Link to **2–3 key code files or pull requests** developed during this sprint and briefly describe the changes. If no code was developed, write **“Not applicable”** and link to the research, design, or setup materials produced instead.

- roadwatch-directions.js / https://github.com/Diogee23/CptS322_PNW-RoadWatch/blob/2abdf1d0b5ee13e202839e383600415579d63bc1/code/map/roadwatch-directions.js — Takes a start and destination location from Google Places, draws the route on the map, shows a trip summary, and lists turn-by-turn steps.
- app.py / https://github.com/Diogee23/CptS322_PNW-RoadWatch/blob/3ca26c426f08311adc3f76943de4900e6d4a6d9f/code/API/app.py — This file gives permissions to our front-end URL so it can grab data from the backend. It grabs all the information from the normalized state data functions, which are in different files, and creates API endpoints with that data.
- WA.py / https://github.com/Diogee23/CptS322_PNW-RoadWatch/blob/3ca26c426f08311adc3f76943de4900e6d4a6d9f/code/API/WA.py — This file pulls highway alerts from the external Washington DOT API, parses the data, and puts it in a normalized form so that app.py can cleanly read it and send it to the frontend.

## 5. Reflection and Next Sprint

Provide **1–2 bullet points** for each question.

**What went well?**

- Three different state DOT formats now convert into one schema, and a single bad record no longer breaks a state's feed
- Directions work end to end: place entry, route drawing, step highlighting, and nearby alerts

**What should improve?**

- Backend data normalization currently skips bad records
- In the future, we need to count skipped records and improve alert fetching
- Improve digital security

**What will you focus on next sprint?**

- Mobile app
- Push notifications
- Saved routes

---

**Before submitting:** Check that all links are accessible, GitHub issues show their current status and assigned contributors, and unfinished issues are moved to an appropriate future sprint.
