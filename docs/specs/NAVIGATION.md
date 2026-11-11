# MIA Navigation & Application Organization — Architecture Handoff

*Zac's spec, 2026-11-11, saved as he sent it. Claude's response is
`docs/NAVIGATION_ARCHITECTURE.md`; the decision is DEC-0153.*

For: Claude Code
Project: TheKingCS/MIA
Purpose: Establish a coherent primary navigation structure and reorganize existing applications, subdashboards, and features around it.

## 1. Overall Vision

MIA currently has many individual applications, but several of them are really features of larger systems or different interfaces into the same functional area.

I want to move away from treating every capability as an independent app.

MIA should feel like one cohesive intelligent assistant with a well-organized ecosystem—not a collection of loosely connected applications.

The goal is to establish:

- Primary Dashboards: The main destinations in MIA's everyday navigation.
- Subdashboards: Larger functional areas within a primary dashboard.
- Features and Tools: Individual capabilities belonging to a subdashboard or primary dashboard.
- Widgets and Shortcuts: Contextual information and quick actions that can appear elsewhere without duplicating ownership.

The following eight primary destinations are my preferred structure. Treat this as the intended direction and source of truth.

## 2. The Eight Primary Destinations

### 1. DASHBOARD

The central overview and starting point for everyday interaction with MIA.

Contents:

- Time, weather, and date
- Active Mission overview
- Music player
- Agent Activity
- Good News Radio

The Dashboard should provide a useful snapshot of what's happening without becoming another place where every application is duplicated.

It should surface relevant information and provide direct access to the appropriate destination.

### 2. HOME

Everything associated with the household, property, personal life, and everyday living.

Subdashboards:

- Kitchen
  - Kitchen management
  - Meal planning and food-related functionality
  - Related household tools
- Smart Devices
  - Cameras
  - Connected devices
  - Home automation
  - Energy monitoring and controls
  - Sensors and smart-home functionality
- Homestead
  - Greenhouse
  - Garden and plants
  - Chickens and other animals
  - Pets
  - Homestead management
- Recreation
  - Music and entertainment
  - Games
  - Maps and navigation
  - Expeditions
  - Recreational activities
- Personal Tools
  - Calendar
  - Journal
  - Notes
  - Memories
  - Memory Vault
  - Personal records and files
  - Relationships and personal organization
  - Other everyday personal tools
- Learning
  - Classroom
  - Knowledge library
  - Courses and educational resources
  - Guitar and other learning tools

Also include home-related missions, upkeep, and household management where appropriate.

### 3. GARAGE

Everything associated with vehicles, equipment, tools, and maintenance.

Contents:

- Vehicles
- Vehicle records and maintenance
- Tools and equipment inventory
- Repairs and troubleshooting
- Equipment maintenance
- Related missions

Maintenance functionality should belong to the asset or equipment it manages rather than existing as an unrelated standalone application.

### 4. FINANCES

The central financial management and business oversight destination.

Contents:

- Income and expenses
- Budgets
- Debts and financial obligations
- Financial graphs and reports
- Insurance
- Compliance
- Taxes and permits
- Businesses

Businesses should have their own subdashboards.

Examples:

- Real Estate
- Woodworking / Workshop
- Other Businesses

Each business should have access to relevant functionality such as:

- Income and expenses
- Assets
- Inventory
- Customers
- Orders and quotes
- Projects and jobs
- Business performance
- Reports

The purpose is to consolidate business-related functionality instead of scattering it across unrelated primary destinations.

Business operations should remain practical and fully functional. This organization should not reduce access to operational tools just because the overall business portfolio is located under Finances.

### 5. HEALTH + FITNESS

Everything associated with physical health, fitness, and wellness.

Contents:

- Health statistics
- Health records and relevant tracking
- Fitness plans
- Workout routines
- Exercise tracking
- Progress tracking
- Diet and meal plans
- Sleep and recovery
- General wellness

Connect relevant meal-planning functionality with Kitchen without duplicating ownership of either system.

### 6. AI TOOLS

The collection of tools that MIA provides for interacting with and working with information.

Contents:

- Look
- Browser
- Inbox
- Communications

These are user-facing capabilities and tools.

Keep this distinction in mind: MIA's internal intelligence, agent orchestration, model management, development environment, and self-inspection capabilities are not necessarily user-facing AI Tools. Those belong in system administration or other appropriate areas.

### 7. MISSIONS

The central destination for goals, progression, challenges, and projects.

Contents:

- Active Mission
- Mission management
- The Dungeon
- Projects
- Skills and character progression
- Rewards and achievements
- Chronicle and progression history

Missions should connect to all other dashboards.

Examples:

- A greenhouse project can have associated missions.
- A vehicle repair can have associated missions.
- A workout routine can contribute to fitness missions.
- A business milestone can become a mission.

However, the actual greenhouse records, vehicle records, workout data, and business information should remain owned by their respective systems.

The Dashboard may display the active mission, but Missions owns the actual mission system.

### 8. SETTINGS

Everything associated with configuring, securing, and understanding MIA.

Contents:

- Security
- Password manager
- Identity and account management
- Application settings
- Preferences
- Diagnostics
- System health
- Connected accounts
- Agent configuration
- About MIA
- MIA system information
- Data management and backups

Keep technical administration and internal system management organized here rather than mixing it into everyday user-facing dashboards.

## 3. Important Organizational Decisions

These are examples of how I want the existing application ecosystem consolidated.

| Existing functionality | New destination |
|---|---|
| Greenhouse | Home → Homestead |
| Chickens / Flock | Home → Homestead |
| Pets | Home → Homestead |
| Household | Home |
| Home Upkeep | Home |
| Power | Home → Smart Devices |
| Kitchen | Home → Kitchen |
| Calendar | Home → Personal Tools |
| Journal / Notes | Home → Personal Tools |
| Kept | Home → Personal Tools |
| Memories | Home → Personal Tools |
| Memory Vault | Home → Personal Tools |
| Classroom | Home → Learning |
| Knowledge | Home → Learning |
| Guitar | Home → Learning |
| Maps | Home → Recreation |
| Navigation | Home → Recreation |
| Tracks / Expeditions | Home → Recreation |
| Garage | Garage |
| Maintenance | Relevant asset dashboard |
| Property / Real Estate | Finances → Businesses → Real Estate |
| Workshop | Finances → Businesses → Woodworking |
| Orders & Quotes | Relevant business dashboard |
| Insurance | Finances |
| Compliance | Finances |
| Budget / Money | Finances |
| Communications | AI Tools |
| Inbox | AI Tools |
| Look / Sight | AI Tools |
| Browser | AI Tools |
| Missions | Missions |
| Dungeon | Missions |
| Projects | Missions |
| Character / Skills | Missions |
| Reward Shop | Missions |
| Party / Chronicle | Missions |
| Passwords / ID Wallet | Settings → Security |
| Diagnostics | Settings |
| Notifications | Global notification system / Dashboard |

This is a directional ownership map, not permission to blindly move every item without inspecting its dependencies.

Some existing capabilities may have broader responsibilities or need to be split into smaller features. Identify those cases before changing anything.

## 4. Architecture Rules

These rules are especially important.

**Rule 1: Every feature has one canonical owner.** A feature should have one primary location in the application hierarchy. Other dashboards may display relevant information, widgets, shortcuts, or contextual actions, but they should not create duplicate versions of the feature.

**Rule 2: Subdashboards should represent meaningful functional areas.** For example: Finances → Businesses → Real Estate → Rental Management, or Home → Homestead → Greenhouse → Water Monitoring. Avoid creating unnecessary navigation levels for small features.

**Rule 3: Missions are system-wide.** Missions can reference and interact with every major area of MIA. They should not own the underlying operational data of those areas.

**Rule 4: The Dashboard is an overview.** The Dashboard should surface important information from other destinations. Examples: active mission summary, music playback controls, agent activity, weather, relevant notifications. It should not become a duplicate application containing independent copies of those systems.

**Rule 5: Global assistant interaction stays accessible.** Talking to MIA, searching, requesting assistance, and accessing relevant agent activity should remain easy regardless of which dashboard is open. Do not force users to navigate back to the Dashboard just to interact with MIA.

**Rule 6: Keep ordinary MIA navigation separate from Living Worlds.** The Nexus / Portals concept is intended to be the primary gateway into Living Worlds / The Convergence. It should not become the universal navigation mechanism for ordinary MIA applications. Keep practical MIA navigation separate from the immersive world-selection experience.

**Rule 7: Preserve functionality.** This is an organizational change, not a reason to remove capabilities. Preserve existing functionality, workflows, integrations, data, and permissions.

## 5. Existing Architecture and Files to Audit

Before implementing changes, inspect the current application architecture.

Known important files:

- `core/web_areas.py` — canonical area registry (DEC-0129)
- `core/web_surfaces.py` — application registry, routes, tool/action domains, and retired applications
- `docs/ORGANIZATION_REVIEW.md` — existing organizational audit

The existing audit identified: 16 Nexus portals; 83 applications/pages listed in areas; 376 voice tools; 434 screen action kinds; 21 web pages outside areas; multiple applications appearing in more than one area; several overlapping functional clusters; Personal currently functioning as a miscellaneous category.

Use the current repository state rather than assuming these counts or registrations have remained unchanged.

## 6. Implementation Instructions

I do not want a superficial navigation redesign. I want the underlying organization to make sense. Please proceed in stages:

**Stage 1 — Audit.** Inspect: all registered primary areas; all application registrations; all routes and navigation entry points; subdashboard structures; existing app ownership and duplication; orphaned pages and capabilities; voice tools and screen actions associated with existing apps; dependencies between applications; existing Nexus / Portal behavior.

Produce a complete mapping of the current architecture to the proposed eight destinations. Identify: applications that can move directly; applications that should be consolidated; applications that should be split into smaller features; applications that need new subdashboards; applications that have ambiguous ownership; features that should remain globally accessible.

**Stage 2 — Proposed Architecture.** Create an updated organizational specification. It should include: the eight primary destinations; their subdashboards; feature ownership; cross-dashboard widgets and shortcuts; global navigation elements; special cases and exceptions; a mapping from existing app IDs to their new owners.

I want to review the architecture before major implementation changes.

**Stage 3 — Implementation Plan.** Once the architecture is established, determine the safest migration strategy. Prefer: preserving existing app IDs and routes where possible; maintaining backwards compatibility; reusing existing components; avoiding unnecessary rewrites; maintaining existing data and integrations; updating navigation registries consistently; preventing duplicate app registrations; keeping voice and action routing functional.

Do not retire or delete existing functionality just because its standalone navigation entry disappears.

**Stage 4 — Implementation and Validation.** After the architecture is approved, implement the changes. Validate: every existing capability has a clear owner; all eight destinations work; subdashboards open correctly; existing routes continue working or redirect appropriately; no important application becomes inaccessible; voice commands still resolve correctly; screen actions still resolve correctly; cross-dashboard links work; Missions integrate with other areas; Nexus / Portals remain separate from ordinary MIA navigation; no duplicate ownership or broken navigation remains.

Run the relevant tests and update the documentation.

## 7. Expected Deliverables

1. Current Architecture Audit — What exists today and how it is organized.
2. New Navigation Architecture — The proposed eight-destination hierarchy.
3. Application Ownership Matrix — Every existing app/page mapped to one canonical owner.
4. Migration Plan — How to reorganize without breaking functionality.
5. Implementation — Once the architecture has been reviewed and approved.
6. Validation Report — Tests, issues discovered, and any remaining organizational problems.

## Final Direction

The central idea is simple: I want MIA organized around the major areas of my life and the things I actually do, rather than around the individual features developers have built.

The eight destinations should feel like the natural structure of one intelligent personal ecosystem.

A user should be able to open Home and find everything related to their household and homestead, open Finances and manage their financial life and businesses, open Garage and manage vehicles and equipment, or open Missions and see their goals and progression across the entire system.

The individual features should exist within these larger systems, not compete with them for space in the primary navigation.

Prioritize clarity, logical ownership, consistency, discoverability, and long-term scalability.

## The glasses (same message)

Also we have decided on 3 main screens for the glasses view.
The orb, the menu, and the nexus.
The menu will have Dashboard, Home, Garage, Finances, Health and Fitness, AI Tools, Missions, and Settings and the user will navigate through all aspects of MIA under sub dashboards in these areas. The nexus will no longer be the over all navigation system and instead will just be for the Living Worlds/Convergence feature having portals for the different worlds/timelines/story you want to access.
