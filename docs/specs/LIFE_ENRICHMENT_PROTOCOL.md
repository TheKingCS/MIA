<!--
The Life Enrichment Protocol (LEP): Zac's handoff of 2026-11-15, kept as given except that names,
towns and nearby places are replaced by <placeholders> (the repo is public; CLAUDE.md: never
commit personal data or hardcode the owner's places). The real values belong in the person's own
data in MIA (person settings), never here. Status: approved feature direction (DEC-0161); not built.
-->

MIA DEVELOPMENT HANDOFF

THE LIFE ENRICHMENT PROTOCOL (LEP)

Project: M.I.A. – Multifunctional Intelligent Assistant
Feature: The Life Enrichment Protocol
Abbreviation: LEP
Priority: Major MIA subsystem
Audience: GitHub Copilot – Architecture, Implementation & QA
Status: Feature vision and requirements established; implementation planning required.

---

1. VISION AND PURPOSE

The Life Enrichment Protocol (LEP) is a major MIA subsystem designed to help the user actively experience, explore, enjoy, and enrich their life.

MIA should not simply organize responsibilities, track productivity, and manage household affairs. She should also help the user discover opportunities, spend meaningful time with loved ones, explore the world, develop new interests, and pursue long-term life experiences.

LEP should transform MIA into a proactive lifestyle and experience-planning companion.

Its primary responsibilities are:

- Discovering local and regional events and activities.
- Maintaining an evolving catalog of experiences.
- Planning dates, outings, vacations, and adventures.
- Understanding individual and shared interests.
- Integrating schedules, location, weather, and transportation.
- Understanding household finances and recommending affordable experiences.
- Maintaining seasonal and long-term experience calendars.
- Tracking shared memories, accomplishments, and bucket-list goals.
- Supporting long-term travel and lifestyle aspirations.

Core philosophy: Help the user build a life worth remembering, not merely organize the life they already have.

2. ARCHITECTURAL PRINCIPLES

Before implementation, inspect MIA's existing architecture, services, modules, memory systems, integrations, and UI conventions.

Do not build LEP as an isolated application that duplicates existing functionality.

Instead, create a modular subsystem that integrates with existing MIA capabilities.

LEP should reuse or communicate with:

- Memory Vault
- Financial Intelligence
- Calendar and Scheduling
- Location Awareness
- Weather Intelligence
- Maps and Navigation
- Notifications
- Personality and Preferences
- Event Discovery
- Travel Planning
- Camera and Photo Systems
- User Profiles and Household Context

Maintain MIA's existing visual identity: dark interfaces, cyan/light-blue accents, elegant futuristic HUD elements, spatial presentation, and cinematic interaction.

LEP should eventually be accessible through the main MIA dashboard, mobile interface, glasses interface, and voice interaction.

3. CORE MODULE: LOCAL EVENT DISCOVERY

MIA should maintain an evolving understanding of what's happening around the user.

Initial geographic configuration:

- Home region: <home town>.
- Primary discovery radius: approximately 1–1.5 hours.
- Extended discovery radius: up to 2–2.5 hours for particularly interesting experiences.
- Allow configurable distance and travel preferences.

Discover and monitor:

Events

- Festivals and fairs.
- Concerts and live performances.
- Car shows.
- Technology expos and conventions.
- Renaissance festivals.
- Food and beer festivals.
- Farmers markets.
- Antique markets.
- Seasonal attractions.
- Sporting events.
- Fishing tournaments.
- Holiday celebrations.
- Workshops and classes.
- Museum exhibitions.
- Theater and comedy shows.
- Community events.

Permanent Attractions

- Museums and galleries.
- Botanical gardens and arboretums.
- Zoos and animal sanctuaries.
- Aquariums.
- Historical attractions.
- Science centers.
- Technology museums.
- Recreation centers.
- Bowling alleys.
- Arcades.
- Skating facilities.
- Breweries.
- Restaurants and cafes.
- Parks and nature preserves.

Discovery Requirements

MIA should:

1. Discover new opportunities through available sources.
2. Verify event dates, locations, availability, and relevant details.
3. Track event expiration and remove outdated opportunities.
4. Distinguish confirmed events from tentative or unverified listings.
5. Identify events that require advance tickets or reservations.
6. Recommend experiences based on user interests.
7. Maintain a record of previously visited attractions.
8. Avoid repeatedly recommending experiences the user has declined or already completed unless relevant.

Event discovery should operate as a background research capability rather than requiring the user to manually request a search every time.

Implement source adapters so additional event providers can be integrated without rewriting the discovery engine.

4. CORE MODULE: COUPLES' EXPERIENCE PLANNER

MIA should understand the interests of both the user and his partner.

Maintain separate preference profiles and a shared couples' profile.

User interests

- Exploring new cities.
- Coffee shops and cafes.
- Restaurants and sushi.
- Shopping and clothing.
- Museums and art galleries.
- Technology expos.
- Parks and arboretums.
- Botanical gardens.
- Shows and theater.
- Petting zoos and animal attractions.
- Bowling and skating.
- Movies.
- Arcades.
- Laser tag.
- Intellectual and educational experiences.
- Comfortable, elegant environments.

Partner's interests

- Hiking.
- Fishing.
- Beer and breweries.
- Outdoor adventure.
- Nature and wildlife.
- Hands-on activities.
- Recreational exploration.

Shared Experience Discovery

MIA should find experiences that combine both partners' interests.

Examples:

<nearby river city> exploration day

- Downtown exploration.
- Coffee and shopping.
- Museum or gallery.
- Riverfront walking.
- Brewery and dinner.

Wildlife adventure

- Wildlife viewing (a nearby preserve).
- A nature centre.
- Picnic.
- Hiking.

<regional city> cultural day

- Botanical gardens.
- Sushi lunch.
- Art museum.
- Shopping.
- Evening entertainment.

Recreation evening

- Pickleball.
- Dinner.
- Arcade or bowling.

Date Planning Capabilities

Support:

- Spontaneous dates.
- Evening outings.
- Weekend adventures.
- Full-day trips.
- Special occasions.
- Anniversary planning.
- Seasonal activities.
- Overnight trips.
- Multi-day vacations.

MIA should learn from feedback and improve recommendations based on which experiences each partner enjoys.

5. CORE MODULE: RECREATION & CASUAL ACTIVITIES

Create a dedicated recreational activity category.

This is important because not every enjoyable experience requires a major destination, expensive tickets, or extensive preparation.

Include:

- Pickleball.
- Throwing a frisbee at a local park.
- Disc golf.
- Badminton.
- Tennis.
- Basketball.
- Volleyball.
- Mini golf.
- Bowling.
- Roller skating.
- Ice skating.
- Swimming.
- Public pools.
- Cycling.
- Hiking.
- Kayaking.
- Paddleboarding.
- Cornhole.
- Geocaching.
- Archery.
- Axe throwing.
- Public recreation centers.
- Community sports leagues.
- Outdoor fitness classes.
- Recreational fishing.
- Park picnics.
- Casual outdoor games.

MIA should discover public facilities, equipment rental opportunities, costs, access requirements, operating hours, and available facilities.

Prioritize accessible activities that can be done spontaneously.

For example, if the user has two free hours and pleasant weather, MIA might suggest visiting a nearby park to play frisbee, followed by coffee or lunch.

6. CORE MODULE: FINANCIAL INTELLIGENCE INTEGRATION

This is a critical requirement.

MIA must understand the user's financial situation when recommending experiences.

LEP must integrate with Financial Intelligence to determine what the user can comfortably afford.

Financial context may include:

- Checking balances.
- Available discretionary funds.
- Household income.
- Recurring bills.
- Debt obligations.
- Savings goals.
- Upcoming expenses.
- Existing financial commitments.
- Entertainment budget.
- Travel savings.
- Long-term financial priorities.

MIA must distinguish between available account balances and money that is actually available for discretionary spending.

Experience Cost Estimation

Calculate estimated total outing costs, including:

- Fuel.
- Travel distance.
- Vehicle fuel efficiency.
- Admission tickets.
- Activity fees.
- Equipment rentals.
- Food.
- Drinks.
- Parking.
- Lodging.
- Optional expenses.

Budget-Aware Recommendations

Example:

The household has an approved monthly entertainment budget.

MIA identifies:

- Local park and frisbee outing: $10–20.
- <nearby city> day trip: $50–85.
- <regional attraction> visit: $60–100.
- <regional city> day trip: $140–200.

These are illustrative estimates, not verified prices.

MIA should prioritize recommendations that fit the available budget.

She should also be capable of explaining why a more expensive option is not currently recommended.

Financial Safeguards

- Never assume unrestricted financial access.
- Use only authorized financial connections and user-approved data.
- Respect reserved funds and financial goals.
- Never make purchases or commitments without explicit approval.
- Never recommend compromising essential obligations to fund recreational spending.
- Allow the user to configure entertainment spending limits.

The objective is to help the user enjoy life while continuing to pursue financial independence.

7. CORE MODULE: SEASONAL EXPERIENCE PLANNING

MIA should maintain a rolling 12-month experience calendar.

Spring

- Botanical gardens.
- Flower festivals.
- Fishing.
- Farmers markets.
- Outdoor cafes.
- Hiking.
- Wildlife viewing.
- Scenic drives.

Summer

- Lakes.
- Swimming.
- Kayaking.
- Paddleboarding.
- Outdoor concerts.
- Camping.
- Fishing.
- Breweries.
- Festivals.
- Night markets.

Autumn

- Fall foliage.
- Scenic hikes.
- Pumpkin patches.
- Apple orchards.
- Renaissance festivals.
- Haunted attractions.
- Craft fairs.
- Harvest festivals.
- Outdoor markets.

Winter

- Christmas markets.
- Light displays.
- Museums.
- Theater.
- Indoor recreation.
- Ice skating.
- Cooking classes.
- Cozy restaurants.
- Holiday attractions.

MIA should understand seasonal timing and notify the user when an experience is approaching.

For events requiring advance planning, provide appropriate lead time.

Maintain a distinction between recurring seasonal attractions and dated annual events.

8. CORE MODULE: EXPERIENCE JOURNAL & MEMORY INTEGRATION

Create a shared couples' adventure journal.

Integrate with Memory Vault.

Track:

- Places visited.
- Cities explored.
- Photos and videos.
- Restaurants visited.
- Favorite cafes.
- Trails completed.
- Recreational activities tried.
- Events attended.
- Experiences rated.
- Favorite memories.
- Experiences to repeat.
- Future destinations.
- Shared achievements.

Allow both partners to contribute memories and feedback, subject to their permissions.

Achievement System

Examples:

- First new city explored.
- Ten new restaurants visited.
- Five museums visited.
- First fishing trip together.
- Twenty hiking trails completed.
- First recreational sports activity.
- One new adventure every month.
- First international trip.

Achievements should encourage exploration rather than create pressure or punish missed goals.

9. CORE MODULE: JAPAN — LONG-TERM LIFE OBJECTIVE

The user has a long-term ambition to travel to Japan and eventually purchase another home there.

This must be represented as a persistent life objective within LEP.

Do not treat Japan as simply another vacation recommendation.

Create a dedicated long-term journey:

PROJECT: JAPAN

Phase 1: Exploration and Preparation

- Research Japanese cities and regions.
- Identify preferred environments.
- Research cultural attractions.
- Develop a travel bucket list.
- Support Japanese language learning.
- Research cultural expectations and practical travel information.
- Identify preferred travel seasons.
- Track flight and accommodation estimates.

Potential destinations include:

- Tokyo.
- Kyoto.
- Osaka.
- Hokkaido.
- Okinawa.
- Japanese countryside and rural communities.

Phase 2: First Major Trip

MIA should help develop a complete travel plan:

- Flights.
- Accommodation.
- Transportation.
- Itinerary.
- Attractions.
- Food experiences.
- Cultural activities.
- Budget.
- Travel documents.
- Seasonal considerations.

Phase 3: Financial Preparation

Integrate Japan planning with Financial Intelligence.

Track:

- Dedicated travel savings.
- Travel budget.
- Estimated flights.
- Accommodation expenses.
- Spending allowances.
- Future property savings.
- Financial milestones.

Do not undermine existing debt payoff, savings, or financial independence goals.

Phase 4: Future Property Ownership

Eventually research:

- Traditional Japanese homes.
- Akiya (vacant houses).
- Rural properties.
- Urban and suburban properties.
- Property prices by region.
- Renovation requirements.
- Property taxes.
- Maintenance costs.
- Foreign ownership regulations.
- Residency and visa requirements.
- Ongoing ownership obligations.

Clearly distinguish legal property ownership from immigration or residency rights.

MIA should help the user compare potential regions and maintain a long-term property research database.

This objective should persist across years and evolve as the user's financial position and preferences change.

10. SPONTANEOUS MODE

Implement a natural-language experience discovery mode.

Example user command:

"I'm bored. Find us something to do."

MIA should consider:

- Current location.
- Weather.
- Time available.
- Travel distance.
- Available budget.
- Partner preferences.
- Existing schedule.
- Current event listings.
- Previously visited places.

Example recommendations:

1. A nearby park for frisbee.
2. A public pickleball court.
3. A coffee shop neither partner has visited.
4. A nearby restaurant for dinner.

MIA should be able to combine multiple activities into a mini-adventure.

Other supported commands:

- "What should <partner> and I do this weekend?"
- "Find something inexpensive for tonight."
- "What's happening around <home town>?"
- "Plan a day trip."
- "Find something outdoors if the weather is nice."
- "Find an event we can attend next month."
- "Show me our Japan bucket list."
- "How much can we afford to spend on a date?"

11. THREE PLANNING HORIZONS

LEP should provide three distinct planning modes.

Spontaneous

What can we do right now?

Focus on:

- Nearby activities.
- Available recreation.
- Current weather.
- Immediate availability.
- Short outings.

Weekly

What should we do on our days off?

Focus on:

- Shared calendar availability.
- Weekend events.
- Date itineraries.
- Budget.
- Advance reservations.

Seasonal and Long-Term

What experiences should we plan ahead for?

Focus on:

- Annual events.
- Seasonal opportunities.
- Vacations.
- Bucket-list experiences.
- International travel.
- Japan property aspirations.

12. DASHBOARD AND USER EXPERIENCE

Create an LEP entry in MIA's main dashboard.

Suggested navigation:

THE LIFE ENRICHMENT PROTOCOL

1. Explore Today
2. What's Happening Nearby
3. Weekend Planner
4. Date Planner
5. Recreation
6. Seasonal Calendar
7. Experiences & Bucket List
8. Adventure Journal
9. Travel & Destinations
10. Project Japan

Explore Today

A daily discovery dashboard showing:

- Upcoming local events.
- New attractions.
- Recommended activities.
- Weather-compatible experiences.
- Upcoming weekend opportunities.
- Budget-compatible recommendations.
- Important booking deadlines.

Visual Design

Use MIA's established design language:

- Dark background.
- Cyan/light-blue accents.
- Futuristic HUD presentation.
- Elegant typography.
- Map-based discovery.
- Image-rich experience cards.
- Calendar views.
- Spatial and voice-friendly navigation.

The glasses interface should prioritize concise recommendations, nearby opportunities, navigation, and quick interactions.

The full mobile and PC interfaces can provide detailed itineraries and research.

13. PROACTIVE INTELLIGENCE AND NOTIFICATIONS

LEP should not depend entirely on user requests.

Examples of useful proactive messages:

- "There is a festival in <nearby city> this Saturday."
- "The weather looks excellent for hiking this weekend."
- "A seasonal attraction you've saved is opening next month."
- "I found a new museum exhibition you might enjoy."
- "You and <partner> have an open Saturday. Would you like me to plan something?"
- "Your Japan travel savings are approaching their next milestone."

Avoid excessive notifications.

Use configurable notification frequency, relevance thresholds, quiet hours, and user feedback.

Prioritize meaningful opportunities rather than notifying the user about every available event.

14. IMPLEMENTATION AND DEVELOPMENT REQUIREMENTS

GitHub Copilot should begin with an architecture audit.

Step 1: Inspect

Identify existing:

- Calendar systems.
- Financial services.
- Location and mapping integrations.
- Memory Vault capabilities.
- Notification services.
- User preference storage.
- Event discovery integrations.
- UI components.
- Background task infrastructure.
- Existing travel or planning functionality.

Step 2: Design

Produce:

- Proposed module architecture.
- Data models.
- Service boundaries.
- Integration map.
- Event discovery pipeline.
- Financial data permission model.
- Background refresh strategy.
- UI navigation proposal.
- Testing strategy.

Step 3: Implement Incrementally

Recommended implementation sequence:

1. LEP foundation and navigation.
2. Interest and preference profiles.
3. Local event discovery.
4. Recreation and activity catalog.
5. Couples' date planner.
6. Itinerary generation.
7. Financial Intelligence integration.
8. Seasonal calendar.
9. Experience journal and Memory Vault integration.
10. Spontaneous Mode.
11. Travel planning.
12. Project Japan.

The Japan objective should be represented in the initial data architecture even if advanced property research is implemented later.

Step 4: Validate

Requirements:

- Unit tests.
- Integration tests.
- UI tests.
- Event expiration tests.
- Duplicate event handling.
- Incorrect event information handling.
- Financial calculation tests.
- Budget protection tests.
- Permission and authorization tests.
- Calendar conflict tests.
- Preference matching tests.
- Memory persistence tests.

Maintain existing architecture conventions and test standards.

Do not break existing MIA functionality.

15. ACCEPTANCE CRITERIA

LEP should eventually satisfy the following:

1. MIA can discover current and upcoming local events.
2. MIA can recommend recreational activities, including casual park activities.
3. MIA understands both partners' interests.
4. MIA can create complete date itineraries.
5. MIA can calculate estimated outing costs.
6. MIA can respect household financial constraints.
7. MIA can plan around shared availability.
8. MIA can account for weather and seasonality.
9. MIA maintains a shared experience journal.
10. MIA can suggest spontaneous activities.
11. MIA maintains seasonal and annual experience opportunities.
12. MIA understands Japan as a persistent long-term life objective.
13. MIA can integrate future travel and property planning with Financial Intelligence.
14. MIA can proactively surface relevant opportunities.
15. All financial actions, bookings, and purchases remain under explicit user authorization.

16. FINAL DEVELOPMENT DIRECTION

LEP should become a living subsystem that continuously improves its understanding of the user's interests, relationships, opportunities, and long-term aspirations.

It should help the user discover things he would not have found independently, make meaningful memories with his partner, enjoy recreational activities, explore new places, and progressively work toward larger life ambitions.

This feature is not merely an events calendar or date-night generator.

It is MIA's system for helping the user actively participate in life.

THE LIFE ENRICHMENT PROTOCOL

Discover more. Experience more. Remember more. Live more.

---

COPILOT DIRECTIVE: Audit the existing MIA repository before implementation. Return an architecture proposal identifying reusable infrastructure, missing capabilities, data models, integration dependencies, and a phased development plan. Do not immediately generate a separate application or duplicate existing MIA services. Preserve modularity, privacy, financial safeguards, existing design conventions, and backward compatibility.
