# MIA capability checklist

*From Zac's "Master Capability Inventory & Development Handoff", 2026-11-12.
We work down this list. An item is ticked only when it is fully usable:
it works by voice and on screen (DEC-0125), it is tested, and its evidence
is cited. Nothing on this list claims to exist until it is ticked.*

**How to work an item:**
1. Audit what already exists (`docs/ASSISTANT_CAPABILITIES.md`,
   `docs/PARITY.md`, `docs/ORGANIZATION_REVIEW.md`).
2. Mark it with the state found: implemented, partial, planned, broken or
   missing.
3. Finish it, test it, then tick it with the commit that did it.

**Owners:** each section names its destination among the eight (DEC-0153).

---

## 1. Core intelligence and personality (AI Tools / Settings)

**Goal:** one consistent companion, not a collection of separate AI tools.

- [ ] Persistent identity and self-awareness
- [ ] Personality, humor, conversational style, emotional expression
- [ ] Reasoning, analysis, problem-solving, decision-making
- [ ] Natural conversation and contextual understanding
- [ ] Intent recognition and interpretation
- [ ] Context and situational awareness
- [ ] Orchestration across models, tools and specialized agents
- [ ] Proactive initiative and recommendations
- [ ] Adapting to preferences and circumstances
- [ ] Self-reflection and performance evaluation
- [ ] Knowing her own limits and uncertainty

## 2. Memory, knowledge and context (Home › Personal Tools)

- [ ] Personal memory and preferences
- [ ] Conversation history and retrieval
- [ ] Long-term knowledge storage
- [ ] Short-term conversational context
- [ ] Project-specific memory
- [ ] Life-state awareness
- [ ] Relationship and household context
- [ ] Event history and timelines
- [ ] Knowledge retrieval and search
- [ ] Memory organization, consolidation and correction
- [ ] Shared versus private memory

## 3. Sensing and perception (AI Tools › Look, Home › Smart Devices)

- [ ] Computer vision and camera access
- [ ] Object and equipment recognition
- [ ] Scene and environment understanding
- [ ] OCR and document reading
- [ ] Audio and environmental sound processing
- [ ] Speech recognition
- [ ] Speaker identification
- [ ] Voice synthesis
- [ ] Spatial awareness
- [ ] Location awareness
- [ ] Activity recognition
- [ ] Wearable and external sensors

## 4. Communication and interaction (AI Tools)

- [ ] Hands-free voice assistant
- [ ] Text conversation
- [ ] Visual responses and on-screen interaction
- [ ] "Hey MIA" wake word
- [ ] Conversation modes (phone-call mode: `docs/CONVERSATION_MODE_PLAN.md`)
- [ ] Multi-person shared conversation
- [ ] Speaker recognition and selection
- [ ] Notifications and proactive messages (through the communication gate)
- [ ] Conversation continuing across devices
- [ ] Custom voice identity and delivery

## 5. Personal life management (Dashboard, Home › Personal Tools)

- [ ] Personal dashboard and daily overview (Your Week, weather, mission in play: 6161aa02)
- [ ] Tasks and to-dos
- [ ] Calendar and scheduling
- [ ] Reminders
- [ ] Goals
- [ ] Routines
- [ ] Journaling
- [ ] Habit tracking
- [ ] Shopping lists
- [ ] Travel planning
- [ ] Navigation and location help
- [ ] Daily planning
- [ ] Activity and life tracking

## 6. Missions, quests and progression (Missions)

- [ ] Creating and managing missions
- [ ] Generating and tracking quests
- [ ] XP
- [ ] Character progression
- [ ] Skills and attributes
- [ ] Achievements and milestones
- [ ] Personal statistics
- [ ] Challenges
- [ ] Streaks
- [ ] Rewards
- [ ] Turning real-world goals into missions
- [ ] Progress from other apps updating missions on its own (workouts, upkeep: 6161aa02, ...)

## 7. Health and fitness (Health and Fitness)

- [ ] Workout tracking
- [ ] Workout plans and programs
- [ ] Exercise library
- [ ] Exercise recognition where supported
- [ ] Rep and set counting
- [ ] Rest timing
- [ ] Workout progress analytics
- [ ] Body measurements
- [ ] Nutrition (Health's meals widget from Kitchen is still to come)
- [ ] Hydration
- [ ] Sleep
- [ ] Health records
- [ ] Wearables: Apple Watch and other devices
- [ ] Fitness missions and progression

## 8. Homestead and property (Home › Homestead, Garage, Finances › Businesses)

- [ ] Property records
- [ ] Homestead dashboard
- [ ] Garden planning
- [ ] Planting and harvest records
- [ ] Greenhouse
- [ ] Environmental monitoring
- [ ] Aquaponics
- [ ] Fish and plant health
- [ ] Livestock and animals
- [ ] Chicken flock and eggs
- [ ] Food production
- [ ] Workshop and equipment
- [ ] Woodworking projects
- [ ] CNC projects and toolpaths
- [ ] 3D printing
- [ ] Laser engraving
- [ ] Construction and building projects
- [ ] Property maintenance (upkeep as scheduled missions: 6161aa02)
- [ ] Materials and equipment inventory
- [ ] Homestead business operations
- [ ] Farm stand
- [ ] Products and sales
- [ ] Homestead expenses and revenue
- [ ] Permits, regulations and compliance

## 9. Finances and real estate (Finances)

- [ ] Household budget
- [ ] Expenses
- [ ] Income
- [ ] Bank accounts (Plaid)
- [ ] Debts and payoff plans
- [ ] Investments
- [ ] Net worth
- [ ] Real estate portfolio
- [ ] Rental properties
- [ ] Tenants and rental records
- [ ] Mortgages and loans
- [ ] Property investment analysis
- [ ] Rental cash flow
- [ ] Taxes and records
- [ ] Business accounting (a dashboard per business: 6161aa02)
- [ ] Forecasting

## 10. Knowledge, research and learning (Home › Learning, AI Tools)

**Critical requirement:** she keeps verified fact, reasonable inference and
speculation apart, and never invents a source, evidence, capability or
information.

- [ ] Web research
- [ ] Deep research
- [ ] Fact checking
- [ ] Sources and citations
- [ ] Notes
- [ ] Document analysis
- [ ] Learning help
- [ ] Tutorials and step-by-step instructions (Trade Master)
- [ ] Math
- [ ] Product and option comparisons
- [ ] Technical research
- [ ] Knowledge library
- [ ] Synthesis

## 11. Computer and digital work (AI Tools, Settings › System)

- [ ] Using and controlling the PC
- [ ] Opening and controlling apps
- [ ] Files
- [ ] Creating and editing documents
- [ ] The browser (her own, with approval: DEC-0117)
- [ ] Software inspection
- [ ] Hardware and system monitoring
- [ ] Workflow automation
- [ ] Multi-step tasks
- [ ] Remote access
- [ ] Device sync
- [ ] Organizing the digital environment

## 12. Self-knowledge and self-development (Settings › System)

**Standing rules:**
- She proposes improvements herself.
- Testing is both automated and supervised.
- The PC is where development happens.
- Every change is tested before it reaches production.
- She knows exactly which capabilities exist.

- [ ] Inspecting her own system
- [ ] Knowing her architecture and modules
- [ ] Knowing her capabilities
- [ ] Hardware inspection
- [ ] Software inspection
- [ ] Diagnostics
- [ ] Automated testing
- [ ] Performance monitoring
- [ ] Development help
- [ ] Writing and changing code
- [ ] Proposing her own improvements
- [ ] Growing her technical knowledge
- [ ] Managing her own evolution

## 13. Security, privacy and trust (Settings › Security)

- [ ] Sign-in
- [ ] Identifying who is speaking or using her
- [ ] Permissions and access
- [ ] Password manager and credentials
- [ ] Encryption
- [ ] Private memory kept separate
- [ ] Shared household information
- [ ] Audits and activity logs
- [ ] Approval for sensitive actions
- [ ] Backup and recovery
- [ ] Security monitoring
- [ ] Data protection

## 14. Entertainment and Living Worlds (the Nexus, from Home › Recreation)

- [ ] Game Master / Dungeon Master
- [ ] Narrative generation
- [ ] The Living Worlds experience
- [ ] The Convergence multiverse
- [ ] Creating worlds and characters
- [ ] Procedural world generation
- [ ] Quest and adventure generation
- [ ] Intelligent NPCs
- [ ] Persistent world state
- [ ] Inventory
- [ ] Character progression
- [ ] Lore and world knowledge
- [ ] Interactive storytelling
- [ ] Player-driven world building
- [ ] Many worlds and dimensions (the Nexus is their gateway: da378961)

## 15. Creative studio and production (AI Tools, Finances › Businesses)

- [ ] Image generation
- [ ] Image editing
- [ ] Graphic design
- [ ] 3D design
- [ ] CAD help
- [ ] CNC design and production prep
- [ ] Laser engraving design
- [ ] Writing and content
- [ ] Music help
- [ ] Video help
- [ ] Product development
- [ ] Prototyping

## 16. Smart devices and the physical world (Home › Smart Devices)

**Hardware:** the phone, the PC, Meta Ray-Ban Display glasses, the Apple
Watch, the Neural Band, and future devices.

- [ ] Smart home control
- [ ] Environmental sensors
- [ ] Wearables
- [ ] Neural Band
- [ ] Hand gestures
- [ ] Eye tracking
- [ ] Spatial interaction
- [ ] Robotics
- [ ] Equipment and machinery
- [ ] Automating the environment
- [ ] Control across devices

## 17. Interface and experience (all)

- [ ] Nexus as the Living Worlds gateway (da378961)
- [ ] Dashboards: the eight and their subdashboards (da378961, 6161aa02)
- [ ] App architecture: one owner per feature (DEC-0153, `tests/test_web_areas.py`)
- [ ] Reusable information and control cards
- [ ] Notifications
- [ ] Universal search
- [ ] Command interface
- [ ] Spatial and holographic interfaces
- [ ] Visual skins and themes
- [ ] Layouts that adapt to each device
- [ ] Navigation architecture
- [ ] Customization
- [ ] The same experience on every device
- [ ] **Glasses:** the orb, the menu (the eight) and the Nexus (da378961)
- [x] **Phone bottom bar:** Dashboard, Apps, MIA, Search (Zac confirmed 2026-11-12; built in 3c9bd222)
- [ ] **Apps menu, two views:** Broad (every app and area alphabetically)
  and Organized (eight destination cards). Today only the organized
  list exists (3c9bd222).
- [ ] **PC:** the phone's layout, larger, with multi-panel workspaces

## 18. Shared services (Settings, the frame)

- [ ] Universal search and discovery
- [ ] Commands by conversation
- [ ] Notifications
- [ ] Automation and scheduled workflows
- [ ] Task orchestration
- [ ] Events and messaging (`core/event_bus.py`, `docs/EVENTS.md`)
- [ ] Context shared between apps
- [ ] One permission system
- [ ] Sync across devices
- [ ] Analytics and reporting
- [ ] Personalization
- [ ] Shared memory and knowledge
- [ ] Discovering apps and capabilities
- [ ] Central error handling and diagnostics

---

## Principles (the handoff's ten, in short)

1. **One MIA:** every device and app reaches the same intelligence,
   identity and shared services.
2. **Every capability by conversation:** reachable by talking to her
   where it makes sense, whatever screen is open.
3. **Clear ownership:** every app and capability has one logical home.
4. **Shared services, not rebuilt ones:** apps reuse what exists.
5. **Consistent navigation:** the phone and PC share one hierarchy; the
   glasses use their adapted three screens.
6. **Capability awareness:** she knows what exists, where it lives and
   whether it works.
7. **Evidence:** she never claims an action succeeded or a capability
   exists without evidence.
8. **Apps feed each other:** especially into Missions, the Dashboard and
   shared memory.
9. **Modular development:** each capability can be maintained and grown
   without breaking unrelated ones.
10. **Human oversight:** sensitive operations, security changes and
    production changes need a person's approval.

## Order of work (the handoff)

1. Audit every section above, marking each item implemented, partial,
   planned, broken or missing.
2. **A. Conversational intelligence:**
   - natural conversation;
   - reasoning and context;
   - memory and continuity;
   - personality and voice;
   - choosing and combining tools;
   - capability awareness and grounding;
   - proactive help.
3. **B. Finishing features:**
   - finish the partial apps;
   - build the missing planned ones;
   - connect the apps to each other;
   - sync across devices;
   - reliability, testing, security and performance.

## Questions for Zac

None open. (2026-11-12: Zac confirmed the bottom bar as Dashboard, Apps, MIA, Search.)
