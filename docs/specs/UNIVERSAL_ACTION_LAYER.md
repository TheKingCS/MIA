<!--
The Universal Action Layer (UAL): Zac's handoff of 2026-11-15, kept as given. Status: approved as a foundational
MIA OS subsystem (DEC-0165), absorbing DEC-0164. How it maps onto what MIA already has, and the build plan:
docs/mia_os/MIA_OS_UNIVERSAL_ACTION_LAYER_PLAN.md. Nothing here is built yet.
-->

MIA OS ARCHITECTURAL HANDOFF

Universal Action Layer (UAL)

Feature Classification: Foundational OS Subsystem
Priority: Core Architectural Capability
Status: Proposed — Requires Architectural Integration
System: MIA (Multifunctional Intelligent Assistant)

---

1. Vision and Purpose

MIA OS should provide an intelligent action layer that makes MIA's capabilities accessible from virtually anywhere in the operating system, regardless of which application, website, document, or interface the user is interacting with.

The user should not need to leave their current application, open the MIA dashboard, navigate to a particular tool, or manually transfer information to MIA.

Instead, MIA should be accessible directly through contextual interactions.

Core principle: Intelligence should be an interface to everything.

For example, a user should be able to highlight a paragraph on a website, right-click it, and assign MIA to:

- Research the selected information.
- Investigate and verify its claims.
- Build a reusable skill from the information.
- Convert the content into another format.
- Draft an email or other communication using the context.
- Generate code or technical implementations.
- Save information to MIA's knowledge system.
- Create a workflow or mission.
- Compare the information against existing knowledge.
- Explain, summarize, or expand upon the selection.
- Send the material to a specialized agent or AI council.

This functionality must extend beyond browsers to the entire operating system.

2. Universal Contextual Interaction

MIA should provide a universal contextual menu accessible through standard OS interactions, particularly right-clicking selected content.

The menu should adapt its available actions based on the selected content, active application, file type, and available context.

Example: Selected Text

When text is selected, MIA could offer:

1. Research this.
2. Build a skill.
3. Explain this.
4. Summarize this.
5. Expand this research.
6. Verify these claims.
7. Translate this.
8. Convert this into another format.
9. Draft an email.
10. Save to knowledge.
11. Create a project or mission.
12. Generate code.
13. Ask MIA.

Example: Selected Files

When interacting with files, MIA could offer:

- Analyze document.
- Extract information.
- Summarize.
- Convert file format.
- Compare against another document.
- Organize into an appropriate knowledge category.
- Extract tasks and deadlines.
- Generate a presentation.
- Create a report.
- Build a skill from the document.
- Add to an existing project.

Example: Images

- Describe and analyze.
- Extract text using OCR.
- Identify objects or components.
- Explain diagrams.
- Extract structured information.
- Convert into another supported format.
- Add to a project or knowledge collection.

Example: Code

- Explain selected code.
- Debug.
- Optimize.
- Generate tests.
- Document.
- Identify vulnerabilities.
- Research dependencies.
- Integrate into an existing MIA project.

These are illustrative action categories, not a requirement to display every option in every context.

The interface should prioritize relevant actions and provide access to the complete action catalog when needed.

3. Universal Action Engine

The contextual interface must not independently implement each AI capability.

Instead, it should communicate with a centralized Universal Action Engine.

The proposed architecture:

ANY APPLICATION / WEBSITE / FILE
↓
CONTEXT CAPTURE
↓
MIA UNIVERSAL ACTION INTERFACE
↓
CONTEXT INTERPRETATION
↓
ACTION REGISTRY
↓
MIA ORCHESTRATION ENGINE
↓
SPECIALIZED AGENTS / TOOLS / SKILLS / AI COUNCIL
↓
EXECUTION ENGINE
↓
PERMISSION AND APPROVAL SYSTEM
↓
RESULT DELIVERY

Action Registry

Create a standardized registry of available MIA actions.

Each registered action should define:

- Unique action identifier.
- Display name and description.
- Supported input types.
- Required contextual information.
- Required capabilities and dependencies.
- Execution handler.
- Permission requirements.
- Expected output types.
- Error handling behavior.
- Reversibility and recovery characteristics.
- Whether local or cloud execution is supported.

New actions should be registerable without requiring modifications to every application integration.

This registry should serve as the common capability source for the contextual menu, command palette, application integrations, browser integrations, and future MIA endpoints.

4. Context Capture and Interpretation

MIA must understand the context in which an action is requested.

Context should include, when available and permitted:

- Selected text.
- Selected files or objects.
- Active application.
- Application type.
- Current URL or document location.
- Surrounding content.
- File metadata.
- Relevant user-selected project or mission.
- Relevant existing MIA knowledge.
- Current task context.

Context capture should be modular and support multiple integration methods.

Potential methods:

1. Native operating system APIs.
2. Accessibility APIs.
3. Clipboard integration.
4. Browser extensions.
5. Application-specific APIs.
6. File-system integrations.
7. Computer-use capabilities.
8. OCR and visual interpretation when necessary.

MIA should gracefully degrade when an application does not expose certain information.

It must never pretend to have access to information that it could not actually retrieve.

5. Universal Command Palette

In addition to contextual menus, MIA OS should provide a global command palette.

Proposed default shortcut: Super + Space.

The command palette should be accessible from anywhere in MIA OS.

Examples:

- "Research what I'm looking at."
- "Turn this into a spreadsheet."
- "Find everything I know about this subject."
- "Build a skill from these instructions."
- "Continue working on my greenhouse project."
- "Explain the current error."
- "Have the council review this."
- "Convert this document into a presentation."

The command palette should automatically incorporate active context when available.

Users must also be able to issue commands without relying on active selections.

The interface should support natural-language commands, action discovery, contextual suggestions, and recent actions.

6. Skill Creation and Knowledge Integration

One of the most important capabilities is the ability to turn information encountered anywhere in the operating system into reusable MIA capabilities.

Example workflow:

The user encounters an article describing automated greenhouse irrigation.

1. The user selects relevant information.
2. The user right-clicks and chooses Build a Skill.
3. MIA researches the underlying concepts.
4. MIA identifies required hardware, software, dependencies, and procedures.
5. MIA investigates existing implementations.
6. MIA drafts a reusable skill.
7. MIA creates documentation and appropriate tests.
8. MIA validates the proposed implementation.
9. MIA presents the skill for review and approval.
10. Upon approval, the skill is registered in MIA's skill ecosystem.

The resulting skill should become available to relevant MIA agents and future workflows.

The original source should be retained as provenance where appropriate.

MIA must distinguish between information that has merely been read, information that has been verified, and capabilities that have actually been tested.

7. Cross-Application Integration Strategy

The Universal Action Layer should be application-independent.

MIA should support multiple integration levels rather than requiring custom development for every application.

Integration| Capability
Native OS| Context menus and global shortcuts
Accessibility| Read and interact with exposed UI elements
Clipboard| Transfer selected content
Browser| Understand pages, selections, and browser context
Application APIs| Deeper application-specific operations
File system| Read and process supported files
Computer Use| Interact with interfaces lacking direct integrations
Terminal| Understand commands, output, logs, and code

The system should prioritize reliable, structured integrations over visual automation whenever possible.

Computer-use functionality should serve as a fallback or complementary capability.

8. Proactive Contextual Assistance

MIA should eventually be capable of suggesting relevant actions without requiring the user to right-click.

Examples:

- While reading technical documentation, MIA offers to explain unfamiliar concepts.
- While viewing a product, MIA offers to compare specifications.
- While reading an article, MIA identifies a relationship to an existing project.
- While reviewing an error message, MIA offers troubleshooting assistance.
- While filling out a form, MIA offers to help populate relevant fields.
- While researching a topic, MIA identifies opportunities to update an existing MIA skill.

Proactive suggestions must be configurable, unobtrusive, and respectful of user attention.

The user should control the level of proactive assistance.

9. Security, Privacy, and Permissions

This subsystem must follow MIA's established security philosophy.

Requirements:

- Local-first context processing wherever practical.
- Explicit permission boundaries.
- No unrestricted access to application data.
- Clear visibility into what context MIA is using.
- User approval for consequential actions.
- Confirmation before sending communications, making purchases, deleting data, executing potentially destructive commands, or changing important settings.
- Audit logs for consequential operations.
- Undo, rollback, or recovery mechanisms wherever technically possible.
- Secure handling of credentials and sensitive application data.
- No silent transmission of private contextual information to cloud models.

Reading and summarizing information should not require the same permission level as executing actions.

10. Multi-Device and Future Endpoint Compatibility

The Universal Action Layer must not be designed exclusively around a desktop interface.

Its underlying action and orchestration architecture should be reusable across the MIA ecosystem.

Future endpoints include:

- MIA desktop environment.
- MIA mobile application.
- MIA browser integration.
- Meta Ray-Ban Display.
- Zeta Astralis.
- MIA Home endpoints.
- Future wearable and spatial computing interfaces.

The same registered actions should be discoverable through different interfaces.

For example, selecting an object through smart glasses, highlighting text on a phone, and right-clicking a paragraph on the desktop should all be capable of invoking the same underlying MIA action when their available context supports it.

11. Architectural Placement

The Universal Action Layer should be treated as a foundational MIA OS subsystem.

It should integrate with:

- MIA Core.
- AI Orchestration.
- Agent Ecosystem.
- Skills Library.
- Knowledge Management.
- File Management.
- Browser Integration.
- Application Integration.
- Permission and Security Systems.
- Mission and Project Management.
- AI Council.
- Cross-Device Communication.

Avoid creating isolated implementations of the same action across different interfaces.

The Action Registry and execution infrastructure should be shared.

12. Implementation Requirements for Claude

Before implementing this subsystem:

1. Examine the existing MIA repository and MIA OS architecture.
2. Identify existing services, interfaces, skills, agents, permissions, and orchestration infrastructure that can be reused.
3. Determine which components already provide partial versions of these capabilities.
4. Identify architectural gaps.
5. Map the Universal Action Layer into the existing system.
6. Identify dependencies and implementation sequencing.
7. Define service boundaries and interface contracts.
8. Identify Linux-specific integration requirements.
9. Define a security and permission model.
10. Establish testing and validation requirements.

Do not duplicate existing MIA functionality merely to satisfy this specification.

Do not assume that every proposed component needs to be built from scratch.

Preserve existing architectural decisions unless a documented reason justifies changing them.

Produce an implementation plan with clear phases, dependencies, acceptance criteria, and testing requirements before beginning substantial implementation.

13. Desired End State

MIA OS should make intelligence available wherever the user works.

The user should be able to encounter information, select it, and immediately delegate meaningful work to MIA without disrupting their workflow.

MIA should be able to research, understand, transform, organize, create, automate, and learn from information encountered throughout the operating system.

Most importantly, capabilities should not remain isolated inside individual applications.

A capability registered once should be accessible through every compatible MIA interface.

Final Design Principle: The user should never have to ask, "Where do I go in MIA to do this?" MIA should be available wherever the task occurs.
