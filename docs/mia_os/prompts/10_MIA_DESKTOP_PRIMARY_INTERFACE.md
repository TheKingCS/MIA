PROMPT 10 — MIA DESKTOP & PRIMARY INTERFACE

Mission

Act as a principal desktop environment architect, Linux graphical systems engineer, interaction designer, human-computer interaction researcher, workspace systems architect, and AI-native interface designer.

Your mission is to design the complete desktop environment and primary user interface for MIA OS.

Prompts 00–09 have established the operating system philosophy, application ecosystem, core Linux architecture, hardware strategy, intelligence infrastructure, autonomy framework, and self-awareness architecture.

Now determine how a user actually experiences and interacts with MIA OS.

The objective is not to place a chatbot inside a conventional desktop.

The objective is to create an AI-native computing environment where MIA is the central coordinating intelligence, applications are first-class experiences, information is accessible through natural conversation and conventional navigation, and the user can move seamlessly between different modes of interaction.

The desktop must support both:

- A distinctive MIA-first environment.
- A conventional desktop experience with familiar Linux application and window management behavior.

The user must never be trapped inside the MIA interface.

MIA should make computing more intuitive without sacrificing flexibility, control, productivity, or direct access to the underlying operating system.

Planning and architecture research only. Do not begin implementation.

---

1. Review Previous Work and Existing MIA Interfaces

Review Prompts 00–09 and inspect the existing MIA repository.

Audit the current:

- Web interface.
- Android interface.
- Desktop interface, if present.
- Navigation architecture.
- Application launcher.
- Search.
- MIA conversational interface.
- Dashboard.
- Smart-glasses interface.
- Living Worlds and The Convergence.
- Mission and project interfaces.
- System settings.
- Notifications.
- Voice interaction.
- Window and workspace behavior.

Do not assume existing interfaces are complete or operational.

Identify:

1. Existing interface components worth preserving.
2. Existing navigation patterns.
3. Existing application layouts.
4. Existing interaction conventions.
5. Existing responsive behavior.
6. Existing visual and functional inconsistencies.
7. Existing architectural limitations.
8. Features that need to transition into native desktop experiences.

Preserve useful work rather than designing an entirely unrelated interface.

The desktop should become the primary full-computing environment while maintaining conceptual continuity with the phone and glasses.

---

2. Foundational Desktop Philosophy

Establish the principles governing the MIA desktop.

2.1 MIA-first, not MIA-only

MIA is the primary interface and coordinating intelligence.

However, users must retain access to:

- Conventional applications.
- Filesystem.
- Terminal.
- System settings.
- Window management.
- Development tools.
- Traditional desktop workflows.
- Linux administration.

2.2 Multiple interaction styles

Users should be able to:

- Speak naturally to MIA.
- Type requests.
- Search for applications and information.
- Open applications directly.
- Work with documents and files.
- Manage multiple windows.
- Use keyboard shortcuts.
- Interact through dashboards.
- Inspect system state.
- Control the operating system directly.

Natural language should complement conventional interaction rather than replace it.

2.3 Contextual continuity

MIA should understand the user's active context.

For example, when working on a software project, she should be able to connect relevant files, applications, tasks, agents, and project history.

Changing applications should not unnecessarily destroy that context.

2.4 User control

MIA may organize, suggest, and coordinate the environment.

The user must retain direct control over windows, applications, navigation, and system settings.

2.5 Interface independence

Separate functional behavior from visual styling.

The same application and workspace should support different themes and presentation styles without needing to be redesigned.

---

3. Overall Desktop Architecture

Design the complete MIA desktop architecture.

Evaluate the responsibilities of:

1. Desktop shell.
2. MIA dashboard.
3. Application launcher.
4. Navigation system.
5. Search system.
6. MIA conversational interface.
7. Workspace manager.
8. Window manager integration.
9. Notification system.
10. Context manager.
11. Application framework integration.
12. System status interface.
13. Task and mission interface.
14. Settings.
15. User and session management.
16. Conventional desktop access.

Define which elements belong to:

- The Linux graphical environment.
- The MIA desktop shell.
- Individual applications.
- Shared MIA services.
- The intelligence infrastructure.
- The autonomy infrastructure.

Determine which existing Linux desktop technologies should be reused and which elements require custom MIA development.

Do not assume MIA needs a completely custom window manager.

Compare integration approaches involving KDE Plasma, GNOME, COSMIC, Wayland compositors, and other appropriate technologies.

Explain the technical and maintenance consequences of each approach.

---

4. Primary Desktop Layout

Design the primary MIA desktop experience.

Consider the following conceptual elements as starting points rather than fixed layout requirements.

Persistent navigation

A consistent navigation area providing access to:

- Home.
- Applications.
- Search.
- Missions and projects.
- MIA.
- Notifications.
- Settings.

Main workspace

The central area where applications, dashboards, documents, and active workflows are displayed.

Contextual MIA presence

A persistent but unobtrusive way to access MIA.

She should be available without permanently consuming most of the screen.

System status

A suitable area for:

- Time and date.
- Weather.
- Connectivity.
- Audio.
- Battery or power.
- Resource status.
- Notifications.
- Active background work.

Workspace controls

Allow users to organize and switch between working environments.

Evaluate:

- Fixed navigation.
- Configurable sidebars.
- Dock and taskbar integration.
- Desktop widgets.
- Floating panels.
- Expandable panels.
- Adaptive layouts.

Do not assume every element must be visible at all times.

Establish a layout that can scale from smaller laptop screens to large desktop monitors and ultrawide displays.

---

5. MIA Dashboard and Home Environment

Design the primary dashboard as the user's central overview.

Investigate useful dashboard sections:

- Current date and time.
- Weather.
- Calendar.
- Upcoming events.
- Active missions.
- Projects.
- Tasks.
- MIA activity.
- Agent activity.
- System health.
- Notifications.
- Music and media.
- Home status.
- Smart devices.
- Personal goals.
- Relevant reminders.

Consider the user's existing vision for a shared household dashboard, including calendar, kitchen, workout tracking, music, and photo display.

Determine how dashboards can be personalized without creating a cluttered collection of unrelated widgets.

Support:

- Multiple dashboards.
- Personal and shared views.
- Custom layouts.
- Widget configuration.
- Information prioritization.
- Responsive behavior.
- Context-sensitive content.

Define widget contracts, data sources, refresh behavior, permissions, and failure states.

The dashboard must distinguish live data from cached or unavailable information.

---

6. Application Launcher and Application Discovery

Design the unified application discovery experience.

The launcher should support both broad exploration and organized navigation.

Consider:

- All applications.
- Categories.
- Favorites.
- Recently used.
- Installed applications.
- Recommended applications.
- Background services where appropriate.
- Capabilities that are not standalone applications.
- Agent interfaces.
- System tools.

Support multiple presentation styles:

- Searchable alphabetical list.
- Organized category cards.
- Compact launcher.
- Full application directory.
- Favorites and pinned applications.

Preserve the principle that users should be able to explore MIA's capabilities rather than needing to remember every feature name.

Clearly distinguish:

- Applications.
- Capabilities.
- Agents.
- System services.
- External integrations.
- Settings.

Determine how the launcher integrates with conventional Linux applications.

A Linux application installed outside the MIA application ecosystem should still be discoverable through the appropriate system mechanisms.

---

7. Unified Search and Command Discovery

Design a unified search experience.

Search should become one of the primary ways users interact with MIA OS.

Investigate search across:

- Applications.
- Files.
- Documents.
- Conversations.
- Memory.
- Projects.
- Tasks.
- Missions.
- Settings.
- System components.
- Devices.
- Capabilities.
- Knowledge resources.

Evaluate contextual search and natural-language requests.

For example:

- "Find the greenhouse project."
- "Open my current software project."
- "Show unfinished missions."
- "Find the document I edited yesterday."
- "Open display settings."
- "What applications can control my smart devices?"

Determine how search results distinguish between:

- Opening an application.
- Finding information.
- Asking MIA a question.
- Starting a workflow.
- Performing an action.

Search must not silently execute consequential operations.

Define indexing, permissions, relevance, privacy, freshness, and offline behavior.

---

8. MIA Conversational Interface

Design the primary conversational experience.

MIA should be accessible from anywhere in the desktop environment.

Evaluate:

- Persistent assistant panel.
- Expandable conversation window.
- Floating assistant.
- Full-screen conversational workspace.
- Voice-first interaction.
- Text-first interaction.
- Context-aware assistance.
- Conversation history.
- Project-specific conversations.
- Multi-agent activity.
- Rich responses and interactive outputs.

Determine how MIA handles context from:

- The active application.
- The current workspace.
- Selected files.
- Open documents.
- Current projects.
- Active missions.
- System state.

Context must be disclosed and permission-controlled.

MIA should not automatically inspect everything on the desktop simply because the assistant panel is open.

Define how users can explicitly share context, revoke access, and inspect what MIA can currently see.

---

9. Ambient, Workspace and Immersive Modes

The MIA experience must support different levels of engagement.

Design three conceptual modes.

Ambient Mode

MIA remains present without demanding attention.

Appropriate for:

- Dashboard information.
- Reminders.
- Background activity.
- System status.
- Music and media.
- Notifications.
- Proactive assistance.

Workspace Mode

The user actively works with applications and tools.

Appropriate for:

- Documents.
- Coding.
- Research.
- Productivity.
- File management.
- Project work.
- Multitasking.
- MIA assistance alongside applications.

Immersive Mode

The interface focuses on a specific experience.

Appropriate for:

- Living Worlds.
- The Convergence.
- Learning environments.
- Games and interactive experiences.
- Spatial interfaces.
- Rich creative environments.

Define how users transition between modes.

Preserve relevant context when switching.

These modes should be presentation and interaction states, not separate operating systems.

---

10. Workspace and Context Management

Design the desktop workspace architecture.

Investigate:

- Multiple workspaces.
- Virtual desktops.
- Project workspaces.
- Persistent layouts.
- Application grouping.
- Window restoration.
- Workspace switching.
- Context preservation.
- Session continuity.
- Workspace sharing.
- Workspace templates.

Consider specialized workspaces such as:

- Development.
- Research.
- Finance.
- Home.
- Homestead.
- Learning.
- Entertainment.
- Administration.

Determine how MIA can recognize and assist with the active workspace.

For example, a development workspace could associate:

- IDE.
- Terminal.
- Browser.
- Repository.
- Project documentation.
- Active tasks.
- Relevant agents.

MIA should be able to help restore a workspace without requiring every application to implement a custom MIA integration.

Investigate how conventional Linux virtual desktops can coexist with MIA's higher-level project workspaces.

---

11. Window Management and Multitasking

Design how MIA integrates with window management.

Investigate:

- Tiling.
- Floating windows.
- Snapping.
- Resizing.
- Multi-monitor layouts.
- Virtual desktops.
- Window grouping.
- Focus management.
- Application restoration.
- Picture-in-picture.
- Persistent panels.
- Keyboard navigation.

Determine how MIA can assist with organizing windows while preserving manual user control.

Consider contextual suggestions such as:

- Organizing windows for a project.
- Opening relevant applications.
- Restoring a previous workspace.
- Creating a focused work layout.

MIA should not constantly rearrange the desktop without authorization.

Evaluate Wayland-native approaches and compatibility with conventional Linux applications.

---

12. Notifications and Attention Management

Design a unified notification system.

Notifications may originate from:

- MIA.
- Applications.
- Operating-system services.
- Agents.
- Workflows.
- Smart devices.
- Calendar.
- Communications.
- System health.

Define:

- Priority.
- Grouping.
- Deduplication.
- Quiet hours.
- Notification history.
- Dismissal.
- Snoozing.
- Escalation.
- User preferences.
- Contextual suppression.

Distinguish urgent warnings from routine informational notifications.

MIA should be able to explain why a notification appeared and what action, if any, is required.

Do not allow proactive notifications to overwhelm the user.

---

13. Missions, Projects and Activity Interface

Design the user-facing interface for the autonomy and mission systems from Prompt 08.

Include:

- Active mission.
- Project overview.
- Task lists.
- Milestones.
- Dependencies.
- Agent assignments.
- Workflow status.
- Pending approvals.
- Completed work.
- Failed operations.
- Progress history.

Determine how users can:

- Start a mission.
- Pause work.
- Resume work.
- Change priorities.
- Reassign tasks.
- Cancel operations.
- Inspect plans.
- Approve actions.
- Review completed work.

Integrate The Dungeon and other game-like mission systems without forcing every productivity feature into a gamified interface.

Make it clear when an activity is a real-world task, a simulated experience, or a game mechanic.

---

14. System Settings and Administration

Design the MIA settings and system administration experience.

Investigate settings for:

- Appearance.
- Themes.
- Applications.
- Devices.
- Intelligence providers.
- Models.
- Memory.
- Voice.
- Autonomy.
- Permissions.
- Notifications.
- Networking.
- Storage.
- System health.
- Updates.
- User accounts.
- Privacy.
- Security.

Distinguish between:

- MIA preferences.
- Application settings.
- Linux system settings.
- Security policies.
- Administrative operations.

Do not hide important Linux controls merely to create a simplified MIA experience.

Determine how advanced settings and conventional Linux administration can remain accessible.

Sensitive configuration changes must use the authorization framework established in Prompt 08 and Prompt 13.

---

15. Files, Documents and Information Management

Design how the desktop supports everyday file and information workflows.

Investigate:

- File manager integration.
- Search.
- File previews.
- Metadata.
- Document viewers.
- Recent files.
- Favorites.
- Project folders.
- Cloud storage.
- Local storage.
- File sharing.
- MIA-assisted organization.

Determine how MIA can help users understand, summarize, organize, and work with files.

Preserve conventional filesystem behavior and user ownership.

MIA should not silently reorganize or delete files.

Define permission boundaries for accessing files from the assistant interface.

---

16. Voice and Multimodal Interaction

Design the desktop interaction model for voice and multimodal input.

Investigate:

- Push-to-talk.
- Continuous conversation.
- Wake-word activation.
- Voice interruption.
- Speech output.
- Microphone selection.
- Audio device management.
- Camera input.
- Screen context.
- Image sharing.
- Multimodal assistant responses.

Determine how the interface communicates microphone and camera state.

Users must always be able to understand when sensors are active.

Design controls for:

- Muting.
- Pausing.
- Ending conversations.
- Disabling sensors.
- Selecting input devices.
- Selecting output devices.
- Reviewing permissions.

The detailed intelligence pipeline belongs to Prompt 07. This prompt establishes how those capabilities are exposed through the desktop.

---

17. Accessibility and Interaction Flexibility

Design an accessibility strategy.

Investigate:

- Keyboard-only navigation.
- Screen reader support.
- High contrast.
- Text scaling.
- Color independence.
- Reduced motion.
- Captions.
- Speech interaction.
- Alternative input devices.
- Focus management.
- Touch support.
- Stylus support.

Do not make important functions dependent exclusively on color, animation, voice, or spatial interaction.

The desktop must remain usable without AI assistance.

---

18. Display, Hardware and Responsive Behavior

Design for a wide range of displays and interaction hardware.

Consider:

- Laptop displays.
- Desktop monitors.
- Ultrawide displays.
- Multiple monitors.
- Touchscreens.
- High-DPI displays.
- Tablets.
- Convertible devices.
- Future spatial displays.

Determine responsive layout rules and minimum supported display dimensions.

Investigate GPU acceleration, animation performance, rendering overhead, and resource usage.

The MIA shell must not consume excessive resources needed for local inference and applications.

---

19. Multi-User and Shared Household Experience

Design the desktop's user and shared-environment model.

Consider:

- Individual accounts.
- Personal dashboards.
- Shared household dashboards.
- Shared calendars.
- Shared tasks.
- Shared projects.
- Personal memory.
- Shared memory.
- User-specific preferences.
- Permission boundaries.

MIA should distinguish between personal information and information intentionally shared with another household member.

Do not assume that a shared dashboard implies shared access to every personal account or conversation.

Define how shared experiences work without compromising individual privacy.

---

20. Visual System and Interface Architecture

Establish the functional visual architecture, leaving detailed visual identity and styling to Prompt 11.

Define:

- Layout primitives.
- Component hierarchy.
- Navigation patterns.
- Application surfaces.
- Cards.
- Panels.
- Dialogs.
- Toolbars.
- Menus.
- Notifications.
- Workspace elements.
- Responsive containers.
- Interaction states.

Determine how themes can change:

- Color.
- Typography.
- Density.
- Motion.
- Surface appearance.
- Iconography.
- Spatial presentation.

Without changing application behavior or data contracts.

Do not prematurely lock in every visual detail.

---

21. Application Integration and Native Desktop Experience

Determine how the MIA application framework from Prompt 03 integrates with the desktop.

Investigate:

- Application manifests.
- Launching.
- Deep links.
- Application windows.
- Multi-window support.
- Notifications.
- Shared services.
- Context sharing.
- File associations.
- Application search.
- Permissions.
- Application lifecycle.

Define how traditional Linux applications coexist with MIA-native applications.

Determine whether MIA applications should use a shared UI framework, web technologies, native Linux toolkits, or a hybrid approach.

Evaluate maintainability, performance, accessibility, security, and developer experience.

Do not force all applications into one framework without evidence.

---

22. Desktop Reliability and Failure Behavior

Design interface failure handling.

Investigate:

- Shell crashes.
- Application crashes.
- Window manager failures.
- Assistant service failures.
- Model unavailability.
- Network loss.
- Display changes.
- GPU failures.
- Memory pressure.
- Session interruption.

The user must retain access to the conventional desktop if MIA's primary interface fails.

Define:

- Shell restart.
- Session recovery.
- Workspace restoration.
- Application restoration.
- Safe interaction mode.
- Conventional desktop fallback.

Coordinate with Prompt 14 for comprehensive boot and recovery architecture.

---

23. Architecture Diagrams

Produce diagrams showing:

1. Complete MIA desktop architecture.
2. Primary desktop layout.
3. Navigation architecture.
4. Application launcher and discovery.
5. Unified search.
6. Conversational interface and context sharing.
7. Ambient, Workspace, and Immersive modes.
8. Workspace and context lifecycle.
9. Window management integration.
10. Notification architecture.
11. Missions and activity interface.
12. Settings and administration boundaries.
13. File and information management.
14. Voice and multimodal interaction.
15. Accessibility architecture.
16. Shared household experience.
17. Application integration.
18. Desktop failure and fallback.

Use Mermaid diagrams where appropriate and explain each.

Also provide several representative layout wireframes using Mermaid, ASCII, or another text-based format.

These should communicate structure and interaction without pretending to be final visual designs.

---

24. Technology Evaluation and Research

Evaluate suitable technologies for:

- Linux desktop shell development.
- Wayland compositors.
- Window management.
- Application frameworks.
- Desktop integration.
- Search and indexing.
- Notifications.
- Widget systems.
- Voice interfaces.
- Accessibility.
- Multi-monitor support.
- Session management.

Compare appropriate options such as KDE Plasma, GNOME, COSMIC, Qt, GTK, Tauri, Electron, Flutter, and other relevant technologies.

Do not assume these options are interchangeable. Explain their actual architectural roles and limitations.

For every major recommendation, document:

1. Technology.
2. Purpose.
3. Alternatives.
4. Advantages.
5. Limitations.
6. Linux compatibility.
7. Performance implications.
8. Accessibility implications.
9. Security implications.
10. Integration complexity.
11. Maintenance requirements.
12. Recommendation.
13. Supporting evidence.

Prioritize official documentation, maintained projects, and reproducible technical evaluations.

---

25. Required Deliverables

Create the following documents:

1. "MIA_OS_DESKTOP_ARCHITECTURE.md"
2. "MIA_OS_PRIMARY_DESKTOP_EXPERIENCE.md"
3. "MIA_OS_DESKTOP_LAYOUT_SPECIFICATION.md"
4. "MIA_OS_DASHBOARD_ARCHITECTURE.md"
5. "MIA_OS_APPLICATION_LAUNCHER_AND_DISCOVERY.md"
6. "MIA_OS_UNIFIED_SEARCH_ARCHITECTURE.md"
7. "MIA_OS_CONVERSATIONAL_INTERFACE.md"
8. "MIA_OS_AMBIENT_WORKSPACE_IMMERSIVE_MODES.md"
9. "MIA_OS_WORKSPACE_AND_CONTEXT_MANAGEMENT.md"
10. "MIA_OS_WINDOW_MANAGEMENT_INTEGRATION.md"
11. "MIA_OS_NOTIFICATION_AND_ATTENTION_SYSTEM.md"
12. "MIA_OS_MISSIONS_AND_ACTIVITY_INTERFACE.md"
13. "MIA_OS_SETTINGS_AND_ADMINISTRATION.md"
14. "MIA_OS_FILE_AND_INFORMATION_INTERFACE.md"
15. "MIA_OS_DESKTOP_VOICE_AND_MULTIMODAL_INTERACTION.md"
16. "MIA_OS_DESKTOP_ACCESSIBILITY.md"
17. "MIA_OS_DESKTOP_DISPLAY_AND_RESPONSIVE_STRATEGY.md"
18. "MIA_OS_SHARED_HOUSEHOLD_DESKTOP_EXPERIENCE.md"
19. "MIA_OS_DESKTOP_VISUAL_COMPONENT_ARCHITECTURE.md"
20. "MIA_OS_APPLICATION_DESKTOP_INTEGRATION.md"
21. "MIA_OS_DESKTOP_FAILURE_AND_FALLBACK.md"
22. "MIA_OS_DESKTOP_TECHNOLOGY_EVALUATION.md"
23. "MIA_OS_DESKTOP_ARCHITECTURE_DIAGRAMS.md"
24. "MIA_OS_DESKTOP_ACCEPTANCE_CRITERIA.md"
25. "MIA_OS_DESKTOP_OPEN_QUESTIONS.md"

Also update:

- "MIA_OS_MASTER_PLAN.md"
- "MIA_OS_DECISION_LOG.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_REQUIREMENTS_TRACEABILITY.md"
- "MIA_OS_IMPLEMENTATION_STATUS.md"
- "MIA_OS_APPLICATION_FRAMEWORK.md"
- "MIA_OS_FEATURE_ECOSYSTEM.md"
- "MIA_OS_SYSTEM_REQUIREMENTS.md"

Maintain consistency with Prompts 00–09.

---

26. Decision Records and Traceability

Create formal decision records for significant desktop architecture decisions.

Each record must include:

- Decision ID.
- Decision title.
- Context.
- Requirements affected.
- Options evaluated.
- Evidence.
- Selected approach.
- Alternatives rejected.
- Consequences.
- Risks.
- Reversibility.
- Conditions for reconsideration.

Maintain traceability between:

- User requirements.
- Desktop features.
- Application framework.
- Linux graphical infrastructure.
- Intelligence infrastructure.
- Autonomy infrastructure.
- Self-awareness services.
- Security requirements.
- Accessibility requirements.
- Implementation phases.

Clearly identify decisions that require user approval.

---

27. Acceptance Criteria

Prompt 10 is complete only when:

- Existing MIA interfaces have been audited.
- The primary desktop architecture is defined.
- MIA-first and conventional desktop experiences coexist.
- The primary layout is specified.
- Dashboard architecture is established.
- Application discovery is designed.
- Unified search is designed.
- Conversational interaction is defined.
- Context sharing is permission-aware.
- Ambient, Workspace, and Immersive modes are established.
- Workspace persistence is designed.
- Window management integration is specified.
- Notifications and attention management are designed.
- Missions and project activity are integrated.
- System settings remain accessible.
- File management preserves conventional behavior.
- Voice and multimodal interaction are addressed.
- Accessibility is addressed.
- Responsive display behavior is specified.
- Shared household and personal experiences are distinguished.
- Application integration is established.
- Failure and conventional desktop fallback are defined.
- Technology recommendations have supporting evidence.
- All diagrams and deliverables are complete.
- Open questions and risks are documented.
- The architecture is consistent with Prompts 00–09.

---

28. Boundaries With Future Prompts

Do not duplicate the detailed scope of later prompts.

- Prompt 11 handles visual identity, themes, styling, and spatial interface design.
- Prompt 12 handles complete multi-device and distributed architecture.
- Prompt 13 handles comprehensive security, privacy, identity, and permissions.
- Prompt 14 handles boot, recovery, updates, and system reliability.
- Prompt 15 handles development and build infrastructure.
- Prompt 16 handles implementation sequencing and migration.
- Prompt 17 consolidates and independently reviews the complete master plan.

This prompt establishes desktop structure, interaction behavior, and application integration.

It does not finalize the visual aesthetic or define every spatial experience.

---

29. Planning Restrictions

This is an architecture research and planning exercise.

Do not:

- Build the desktop shell.
- Replace the existing interface.
- Change the Linux desktop environment.
- Install graphical frameworks.
- Modify application navigation.
- Remove conventional desktop functionality.
- Deploy visual redesigns.
- Change system configuration.
- Begin implementation.

You may inspect source code, screenshots, existing interfaces, documentation, and non-destructive diagnostics.

Preserve existing MIA work and distinguish current functionality from proposed design.

---

30. Final Objective

The final desktop architecture should establish a computing environment that feels like MIA rather than a conventional Linux desktop with an AI assistant attached.

The user should be able to:

- Enter MIA and immediately understand their environment.
- Access applications and capabilities intuitively.
- Ask MIA for help from anywhere.
- Work traditionally with windows, files, and applications.
- Manage projects and missions.
- Inspect system and agent activity.
- Move between ambient, productive, and immersive experiences.
- Retain context between workspaces.
- Access conventional Linux functionality whenever needed.

MIA should feel present, capable, and integrated without being intrusive.

The desktop must be visually distinctive when styled in Prompt 11, but its underlying architecture must remain usable, accessible, responsive, and maintainable.

Produce a technically rigorous, evidence-based, internally consistent desktop architecture.

When finished, summarize:

1. The recommended desktop architecture.
2. The selected Linux graphical foundation and integration strategy.
3. The primary desktop layout.
4. Application launcher and search design.
5. MIA conversational and contextual interaction.
6. Ambient, Workspace, and Immersive modes.
7. Workspace and multitasking strategy.
8. Dashboard and shared household experience.
9. Conventional desktop compatibility.
10. The most significant technical risks.
11. Decisions requiring user approval.
12. Questions that must be resolved before Prompt 11.

Stop after completing Prompt 10. Wait for review and approval before beginning Prompt 11.
