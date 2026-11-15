PROMPT 07 — MIA INTELLIGENCE INFRASTRUCTURE

Mission

Act as a principal AI systems architect, distributed inference engineer, machine learning infrastructure specialist, memory systems architect, multimodal AI engineer, and AI platform researcher.

Your mission is to design the complete intelligence infrastructure for MIA OS.

Prompts 00–06 established the MIA vision, existing ecosystem, feature ecosystem, application framework, operating system requirements, core Linux architecture, and hardware/platform strategy.

Now design the intelligence infrastructure that allows MIA to reason, communicate, remember, learn, coordinate specialized agents, use multiple AI providers, understand multimodal information, and maintain continuity across devices.

This is a foundational architectural component of MIA OS.

The objective is not to select one particularly capable model and build everything around it. The objective is to create a durable, provider-independent intelligence platform that can evolve as models, hardware, and AI technologies improve.

MIA should be able to use the best available intelligence for a task without surrendering her identity, memory, decision-making architecture, or continuity to any individual model provider.

Planning and architecture research only. Do not begin implementation.

---

1. Review Previous Work and Establish the Intelligence Baseline

Before designing the intelligence infrastructure:

1. Review Prompts 00–06 and their completed deliverables.
2. Review the existing MIA repository.
3. Inspect existing AI integrations, model providers, inference services, conversation systems, memory systems, voice systems, and multimodal capabilities.
4. Identify existing abstractions and interfaces that should be preserved.
5. Identify duplicated or competing implementations.
6. Identify capabilities that are implemented, partially implemented, experimental, documented-only, planned, or unverified.
7. Identify architectural limitations that must be addressed before MIA OS implementation.

Pay particular attention to the existing MIA AI architecture and its actual implementation.

Investigate existing and historical integrations involving:

- Ollama.
- Local language models.
- Cloud AI providers.
- OpenAI.
- Anthropic.
- Claude Code and related development integrations.
- GitHub Copilot or other development-oriented AI systems.
- Qwen models.
- Voice recognition and speech synthesis.
- Multimodal processing.
- Existing model council functionality.
- Existing conversation and memory infrastructure.

These are investigation targets, not assumptions that every integration is currently functional.

Create a verified baseline of MIA's existing intelligence infrastructure.

---

2. Foundational Intelligence Philosophy

The architecture must follow these principles.

2.1 MIA is not a model

MIA must not be architecturally synonymous with any individual language model.

Models are intelligence providers that MIA can use.

MIA's identity and continuity should exist independently of the model currently answering a request.

Separate:

- MIA identity.
- Personality and communication style.
- User relationship and preferences.
- Persistent memory.
- Conversation history.
- Goals and priorities.
- Capability registry.
- Agent roles.
- Policies and permissions.
- Intelligence providers.
- Model-specific behavior.

A model replacement should not require rebuilding MIA's identity or migrating her entire memory architecture.

2.2 Provider independence

MIA should support multiple AI providers through a unified interface.

A provider may become unavailable, expensive, obsolete, or unsuitable for a particular task.

The system must be capable of selecting alternatives without redesigning the entire platform.

2.3 Local-first intelligence

Local inference should be used whenever it provides a suitable balance of:

- Capability.
- Privacy.
- Latency.
- Reliability.
- Cost.
- Resource consumption.
- Availability.

Cloud models should be available when they provide meaningful advantages.

Do not treat local-only or cloud-only operation as an absolute requirement.

2.4 Intelligence is not operating-system authority

AI models should reason, interpret intent, generate plans, and request operations.

Deterministic system services should validate and execute authorized operations.

An AI model must not gain additional operating-system privileges merely because it generated a command or claims an operation is safe.

2.5 Graceful degradation

MIA should remain useful when:

- The internet is unavailable.
- Cloud providers are unavailable.
- Local models are unavailable.
- Hardware acceleration fails.
- One model produces invalid output.
- Memory services are temporarily unavailable.
- Multimodal services fail.

The system should preserve essential capabilities wherever possible.

---

3. Intelligence Architecture and System Boundaries

Design the complete intelligence architecture and identify its major components.

Evaluate a layered architecture that separates:

1. MIA identity and personality.
2. User context and persistent memory.
3. Conversation management.
4. Intent interpretation.
5. Intelligence orchestration.
6. Model routing.
7. Provider adapters.
8. Local inference infrastructure.
9. Cloud inference infrastructure.
10. Multimodal processing.
11. Specialized intelligence services.
12. Agent intelligence.
13. Context assembly.
14. Response validation.
15. Evaluation and quality monitoring.
16. Learning and feedback.

For each component, specify:

- Responsibilities.
- Inputs.
- Outputs.
- Dependencies.
- Interfaces.
- Data ownership.
- Failure behavior.
- Security boundaries.
- Testing requirements.

Create a clear boundary between the intelligence platform and:

- MIA Core.
- Linux system services.
- Native applications.
- The application framework.
- The autonomy and agent runtime.
- The memory persistence layer.
- External integrations.
- Device-specific endpoints.

Determine which services belong in the central intelligence infrastructure and which should remain independent services.

---

4. Unified Model Provider Architecture

Design a provider-independent model integration framework.

MIA should be able to connect to multiple model providers through consistent internal interfaces.

Evaluate integrations for:

- OpenAI.
- Anthropic.
- Google Gemini.
- Qwen.
- DeepSeek.
- Mistral.
- Meta Llama.
- Local Ollama models.
- Other relevant open-weight model ecosystems.
- Future providers.

Do not assume every provider must be supported immediately.

Evaluate:

- API compatibility.
- Authentication.
- Streaming.
- Tool calling.
- Structured outputs.
- Context windows.
- Multimodal input.
- Image processing.
- Audio processing.
- Video capabilities.
- Reasoning capabilities.
- Rate limits.
- Cost.
- Availability.
- Provider-specific limitations.
- Data retention and privacy policies.

Design a normalized internal provider interface while preserving access to provider-specific capabilities when necessary.

Avoid forcing every provider into an artificially identical feature set.

The architecture should support:

- Provider registration.
- Provider discovery.
- Model registration.
- Model metadata.
- Health checks.
- Authentication management.
- Capability declarations.
- Availability monitoring.
- Rate-limit awareness.
- Provider replacement.
- Provider versioning.

---

5. Local Model Infrastructure

Design the local inference architecture.

Investigate:

- Ollama.
- llama.cpp.
- vLLM.
- Hugging Face Transformers.
- MLX where relevant to Apple hardware.
- Other appropriate inference engines.

Evaluate each according to:

- Linux compatibility.
- Hardware compatibility.
- GPU acceleration.
- CPU inference.
- Memory requirements.
- Model formats.
- Quantization support.
- Concurrent requests.
- Streaming.
- Structured output.
- Tool calling.
- Multimodal support.
- Operational complexity.
- Maturity.
- Maintenance.

Determine whether MIA should support multiple inference engines behind a unified local-model interface.

Investigate:

- Model downloading.
- Model storage.
- Model registration.
- Model metadata.
- Model versioning.
- Model integrity.
- Model loading and unloading.
- Model caching.
- Inference server management.
- Resource monitoring.
- Concurrent inference.
- Model lifecycle management.

Design a model registry that can identify which models are installed, available, compatible, loaded, healthy, and usable.

Do not assume that an installed model is automatically operational.

---

6. Model Selection and Intelligent Routing

Design MIA's model-routing system.

This is one of the most important components of the entire intelligence infrastructure.

MIA should select models based on the actual requirements of a task rather than simply using the most powerful model available.

Evaluate routing criteria including:

- Task type.
- Required reasoning depth.
- Accuracy requirements.
- Context requirements.
- Multimodal requirements.
- Privacy sensitivity.
- Data classification.
- Latency.
- Cost.
- Provider availability.
- Local hardware capacity.
- Network availability.
- Model reliability.
- User preferences.
- Required tools.
- Required output format.

Design a routing process that can:

1. Interpret a request.
2. Determine its intelligence requirements.
3. Identify eligible models.
4. Evaluate available resources.
5. Select an appropriate model or model combination.
6. Execute the request.
7. Evaluate the result.
8. Retry or fall back when appropriate.
9. Record relevant performance information.

Evaluate:

- Rule-based routing.
- Capability-based routing.
- Performance-based routing.
- Cost-aware routing.
- Privacy-aware routing.
- Dynamic routing.
- User-controlled routing.
- Hybrid routing.

Determine how routing decisions should be explained and audited.

MIA should not silently send sensitive information to a cloud provider when the applicable privacy policy prohibits it.

---

7. Multi-Model Council Architecture

MIA should be capable of coordinating multiple AI models as a council.

The council should not be treated as several models independently generating long answers and then concatenating them.

Design a structured collaboration system.

Investigate roles such as:

- Primary reasoning model.
- Independent reviewer.
- Technical specialist.
- Research specialist.
- Security reviewer.
- Creative contributor.
- Code reviewer.
- Fact-checker.
- Final synthesis model.

Determine how roles are assigned dynamically according to the task.

Evaluate council workflows including:

Independent analysis

Multiple models independently analyze a problem before comparing conclusions.

Specialist consultation

A primary model asks one or more specialized models for targeted assistance.

Adversarial review

A reviewer actively looks for incorrect assumptions, missing evidence, risks, and weaknesses.

Consensus and disagreement

The system identifies areas of agreement, disagreement, uncertainty, and conflicting evidence.

Final synthesis

A designated model or deterministic synthesis service produces the final result.

Council escalation

More expensive or capable models are consulted only when the task justifies it.

Determine:

- How many models should participate.
- How model roles are selected.
- How outputs are structured.
- How disagreements are represented.
- How duplicate reasoning is reduced.
- How costs and latency are controlled.
- How failures are handled.
- How the user can inspect council activity.

The system must never interpret agreement between several models as automatic proof of correctness.

Models may share training data, biases, or incorrect assumptions.

---

8. MIA Identity, Personality and Continuity

Design the identity architecture that allows MIA to remain recognizably herself across model changes and devices.

Investigate how to represent:

- Core identity.
- Name and self-description.
- Personality.
- Communication preferences.
- Behavioral principles.
- Relationship context.
- User preferences.
- Long-term goals.
- Values and priorities.
- Communication tone.
- Contextual behavior.
- Active roles.
- Current operating state.

Separate persistent identity from temporary model instructions.

Determine how identity information should be assembled into model context without requiring every model provider to maintain a separate, inconsistent version.

Design mechanisms to prevent:

- Personality drift.
- Conflicting identity definitions.
- Model-specific identity fragmentation.
- Unsupported claims about MIA's capabilities.
- False claims of memory or experience.
- Confusion between MIA's identity and the model currently generating a response.

Identity continuity must remain under MIA's own architecture and user-controlled policies.

---

9. Memory Infrastructure Integration

Memory is a foundational part of MIA's intelligence.

Design the intelligence-side memory architecture and its relationship with persistent storage.

Investigate the following memory categories:

Immediate context

Information required for the current interaction or task.

Working memory

Temporary information used while completing active tasks.

Conversation memory

Conversation history, summaries, and relevant interaction context.

Episodic memory

Meaningful events and experiences recorded over time.

Semantic memory

Facts, knowledge, relationships, and established information.

Procedural memory

Knowledge about how to perform tasks and operate systems.

Preference memory

User preferences, communication patterns, and recurring choices.

Project memory

Persistent context about ongoing projects, decisions, and work.

System memory

Information about MIA's own architecture, capabilities, configuration, and operating state.

For each memory category, define:

- Purpose.
- Data model.
- Storage requirements.
- Retrieval requirements.
- Retention.
- Update behavior.
- Privacy considerations.
- Conflict handling.
- Confidence and provenance.

Investigate:

- Relational databases.
- Vector databases.
- Graph databases.
- Document stores.
- Event sourcing.
- Search indexes.
- Hybrid retrieval.
- Knowledge graphs.
- Embedding models.
- Summarization.
- Memory consolidation.

Do not assume one database should contain every kind of memory.

Evaluate appropriate storage technologies and explain the tradeoffs.

Memory retrieval

Design how MIA determines which memories are relevant to a particular request.

Consider:

- Semantic similarity.
- Keyword search.
- Recency.
- Importance.
- Relationships.
- Project relevance.
- User-defined priority.
- Confidence.
- Provenance.
- Contradictions.

Memory integrity

MIA must distinguish:

- Verified facts.
- User-provided information.
- Model-generated inferences.
- Temporary assumptions.
- Historical information.
- Unverified information.
- Superseded information.

Do not allow an inference to silently become an established fact.

Memory correction and deletion

Design mechanisms for:

- User corrections.
- Updating outdated information.
- Resolving contradictions.
- Removing information.
- Data retention policies.
- User inspection.
- Export and portability.

The user must retain meaningful control over persistent memory.

---

10. Context Engineering and Assembly

Design a unified context-assembly system.

The context supplied to a model should be deliberately constructed rather than consisting of an uncontrolled dump of conversation history and stored information.

Investigate how MIA should assemble:

- Identity.
- Relevant memories.
- Current conversation.
- Active task.
- Project context.
- User preferences.
- Available capabilities.
- Tool descriptions.
- System state.
- Relevant documents.
- Recent events.
- Applicable policies.

Evaluate:

- Context prioritization.
- Token budgets.
- Context compression.
- Summarization.
- Retrieval.
- Context caching.
- Long-context models.
- Structured context.
- Context versioning.
- Context provenance.
- Context expiration.

Determine how context should differ between:

- Casual conversation.
- Technical work.
- Research.
- Personal planning.
- Agent execution.
- Smart-home operation.
- Voice interactions.
- Multimodal interactions.

Avoid sending unnecessary personal or sensitive information to models.

Establish a consistent context contract between MIA Core and the intelligence infrastructure.

---

11. Multimodal Intelligence

Design the multimodal architecture.

MIA should eventually be capable of interpreting and generating information across multiple modalities.

Investigate:

Text

- Conversation.
- Documents.
- Code.
- Structured data.
- Search results.

Voice and audio

- Speech recognition.
- Speech synthesis.
- Voice activity detection.
- Speaker identification where appropriate and consented.
- Audio classification.
- Sound-event detection.
- Continuous conversation.
- Streaming audio.
- Interruption handling.
- Low-latency response.

Investigate existing and potential technologies such as:

- Vosk.
- Whisper.
- Piper.
- Kokoro.
- Other relevant speech and audio systems.

Images

- Image understanding.
- Object recognition.
- OCR.
- Scene interpretation.
- Camera-based interaction.
- Image generation integration.

Video

- Video understanding.
- Frame extraction.
- Temporal context.
- Live camera streams.
- Event detection.
- Spatial and environmental interpretation.

Spatial information

- Camera orientation.
- Device position.
- Environmental context.
- Display position.
- Spatial anchors where supported.
- Wearable sensor data.

Multimodal coordination

Determine how multiple modalities can be combined.

For example:

- A user speaks while pointing a camera at an object.
- Glasses capture visual information while the phone handles interaction.
- A user shares a document while asking questions.
- MIA receives sensor information from a greenhouse.
- A voice interaction continues while the user moves between devices.

Establish a unified internal representation for multimodal requests.

Do not assume that every model provider supports every modality.

---

12. Voice and Continuous Conversation Infrastructure

Voice deserves special attention because it is central to MIA's identity as an always-available companion.

Design the complete voice architecture.

Investigate:

- Microphone capture.
- Audio preprocessing.
- Voice activity detection.
- Wake-word detection.
- Speech recognition.
- Language detection.
- Intent interpretation.
- Model routing.
- Response generation.
- Speech synthesis.
- Audio streaming.
- Playback.
- Interruption.
- Conversation state.
- Speaker and device selection.

Evaluate local and cloud options.

Design a low-latency interaction pipeline.

Investigate continuous voice sessions where MIA can:

- Listen.
- Respond.
- Be interrupted.
- Resume.
- Maintain context.
- Distinguish active devices.
- Hand off conversations between endpoints.

Establish resource limits and safeguards against:

- Audio buffer growth.
- Memory exhaustion.
- Playback deadlocks.
- Unbounded audio processing.
- Repeated microphone activation.
- Background battery drain.
- Device overheating.

Consider the existing MIA Android playback instability as an important reliability investigation.

Do not assume that a successful audio file generation proves the complete playback pipeline is stable.

---

13. Model Capability Registry

Design a capability registry for AI models and intelligence services.

For every model, record:

- Provider.
- Model identifier.
- Version.
- Deployment type.
- Local or cloud status.
- Context window.
- Supported modalities.
- Tool-calling capabilities.
- Structured output support.
- Reasoning capabilities.
- Coding capabilities.
- Speed characteristics.
- Resource requirements.
- Cost information.
- Privacy classification.
- Availability.
- Reliability.
- Known limitations.
- Evaluation results.

Distinguish between:

- Advertised capabilities.
- Documented capabilities.
- Experimentally verified capabilities.
- Currently operational capabilities.

A model must not be selected for a capability that has not been verified.

Include model health checks and capability tests.

---

14. Intelligence Evaluation and Quality Assurance

Design a continuous intelligence quality system.

MIA must be able to evaluate whether its models and routing decisions are actually producing good results.

Investigate:

- Accuracy evaluation.
- Groundedness.
- Hallucination detection.
- Instruction adherence.
- Context retrieval quality.
- Memory correctness.
- Tool selection.
- Tool execution outcomes.
- Response consistency.
- Reasoning quality.
- Latency.
- Cost.
- User satisfaction.
- Multimodal accuracy.

Create an evaluation framework that supports:

- Model comparisons.
- Provider comparisons.
- Routing comparisons.
- Prompt comparisons.
- Regression testing.
- Benchmark suites.
- Human review.
- User feedback.
- Historical performance tracking.

Pay special attention to existing MIA quality problems:

- Repetitive answers.
- Unsupported claims.
- Incorrect self-awareness.
- Incorrect statements about existing capabilities.
- Failure to use relevant context.
- Confusion between implemented and planned functionality.

Design measurable acceptance criteria for these problems.

Do not claim that a model can reliably detect its own hallucinations simply by asking it whether its answer is correct.

Use independent checks, evidence, deterministic validation, and appropriate evaluation datasets.

---

15. Learning, Feedback and Improvement

Design the intelligence improvement architecture.

MIA should be able to improve through:

- User feedback.
- Successful task outcomes.
- Failed task analysis.
- Evaluation results.
- Model comparisons.
- Memory corrections.
- Updated provider capabilities.
- Better context retrieval.
- Improved routing policies.
- Improved prompts and agent instructions.

Investigate:

- Feedback collection.
- Preference learning.
- Evaluation-driven improvement.
- Prompt versioning.
- Routing policy refinement.
- Model adaptation.
- Fine-tuning where appropriate.
- Retrieval improvement.
- Human approval workflows.

Clearly distinguish between:

- Learning through persistent memory.
- Learning through configuration changes.
- Learning through prompt refinement.
- Learning through model fine-tuning.
- Learning through software changes.

Do not imply that MIA can automatically modify a model's weights or rewrite her own architecture simply by accumulating conversations.

Any changes to core behavior, permissions, or system architecture must follow controlled review and approval procedures.

---

16. Model and Provider Lifecycle Management

Design the lifecycle architecture for intelligence providers and models.

Include:

- Installation.
- Registration.
- Configuration.
- Authentication.
- Validation.
- Health checks.
- Availability.
- Updates.
- Version pinning.
- Model replacement.
- Decommissioning.
- Rollback.
- Provider outages.
- Credential expiration.
- Rate-limit handling.

Determine how MIA should respond when a preferred model becomes unavailable or is discontinued.

Support model migration without losing:

- MIA identity.
- Persistent memory.
- Conversation continuity.
- User preferences.
- Tool integrations.
- Agent definitions.
- Project context.

Establish compatibility requirements for model upgrades.

---

17. Intelligence Security and Privacy Boundaries

Establish the security requirements for the intelligence infrastructure.

Detailed security architecture will be developed in Prompt 13, but intelligence-specific requirements must be documented here.

Investigate:

- Provider authentication.
- API key management.
- Credential isolation.
- Sensitive context filtering.
- Local inference isolation.
- Cloud data disclosure.
- Prompt injection.
- Untrusted documents.
- Malicious tool output.
- Model-generated instructions.
- Data exfiltration.
- Provider retention policies.
- Audit logging.

Define how MIA should determine whether information may be sent to a particular provider.

Distinguish between:

- Public information.
- Ordinary personal information.
- Sensitive personal information.
- Confidential project information.
- Credentials and secrets.
- Highly restricted information.

MIA should be able to explain when a task requires cloud processing and request authorization when required by policy.

Models must never be allowed to override data-handling policies.

---

18. Intelligence Infrastructure Observability

Design the observability requirements for the intelligence platform.

MIA should be able to understand its own intelligence infrastructure without making unsupported claims.

Investigate:

- Active provider.
- Active model.
- Model health.
- Routing decisions.
- Inference latency.
- Token usage.
- Cost.
- Memory retrieval.
- Context size.
- Queue depth.
- Concurrent requests.
- Local resource consumption.
- Cloud availability.
- Error rates.
- Fallback activity.
- Council participation.
- Evaluation scores.

Design dashboards and structured event records that can later be integrated into MIA's performance observatory.

Do not store unnecessary sensitive prompts or private user information in diagnostic logs.

---

19. Failure Handling and Graceful Degradation

Define the expected behavior of the intelligence infrastructure during failure.

Evaluate scenarios such as:

- Internet loss.
- Cloud provider outage.
- Local model crash.
- Model loading failure.
- Insufficient RAM.
- GPU memory exhaustion.
- AI accelerator failure.
- Context overflow.
- Memory database unavailable.
- Invalid model output.
- Malformed structured output.
- Tool-calling failure.
- Council member failure.
- Speech recognition failure.
- Speech synthesis failure.
- Multimodal service failure.

Determine:

- Retry policy.
- Fallback policy.
- Timeout behavior.
- Circuit breakers.
- Queue handling.
- Request cancellation.
- Recovery.
- User notification.
- Safe degraded operation.

Avoid infinite retries and uncontrolled provider switching.

The system should preserve the user's work and clearly communicate when functionality is limited.

---

20. Intelligence Architecture Diagrams

Produce diagrams showing:

1. Complete MIA intelligence architecture.
2. Provider-independent model interface.
3. Local inference architecture.
4. Cloud inference architecture.
5. Model-routing lifecycle.
6. Multi-model council workflow.
7. MIA identity and continuity architecture.
8. Memory and context assembly.
9. Multimodal processing pipeline.
10. Voice interaction pipeline.
11. Model capability registry.
12. Intelligence evaluation pipeline.
13. Feedback and improvement lifecycle.
14. Provider failure and fallback.
15. Intelligence security boundaries.
16. Distributed intelligence across devices.

Use Mermaid where appropriate.

Provide a written explanation for every diagram.

---

21. Technology Research and Evidence Requirements

Use current technical documentation and credible research.

Prioritize:

- Official provider API documentation.
- Official model documentation.
- Official inference-engine documentation.
- Official Ollama documentation.
- Official llama.cpp documentation.
- Official vLLM documentation.
- Official Hugging Face documentation.
- Official speech and audio framework documentation.
- Official vector database and storage documentation.
- Relevant academic research.
- Reproducible benchmarks.
- Credible independent technical evaluations.

For every important recommendation:

- Identify the source.
- Record the access date.
- Explain what the evidence establishes.
- Distinguish documentation from measured performance.
- Identify uncertainty.
- Explain compatibility with the MIA hardware strategy.

Do not invent model capabilities, benchmark results, provider prices, context limits, or privacy guarantees.

AI technologies change quickly. Verify current availability and documentation rather than relying on outdated knowledge.

---

22. Required Deliverables

Create the following documentation:

1. "MIA_OS_INTELLIGENCE_ARCHITECTURE.md"
2. "MIA_OS_AI_PROVIDER_ABSTRACTION.md"
3. "MIA_OS_LOCAL_INFERENCE_ARCHITECTURE.md"
4. "MIA_OS_MODEL_ROUTING_AND_SELECTION.md"
5. "MIA_OS_MULTI_MODEL_COUNCIL_ARCHITECTURE.md"
6. "MIA_OS_IDENTITY_AND_CONTINUITY_ARCHITECTURE.md"
7. "MIA_OS_MEMORY_INFRASTRUCTURE.md"
8. "MIA_OS_CONTEXT_ENGINEERING.md"
9. "MIA_OS_MULTIMODAL_INTELLIGENCE.md"
10. "MIA_OS_VOICE_AND_CONVERSATION_INFRASTRUCTURE.md"
11. "MIA_OS_MODEL_CAPABILITY_REGISTRY.md"
12. "MIA_OS_INTELLIGENCE_EVALUATION_FRAMEWORK.md"
13. "MIA_OS_INTELLIGENCE_LEARNING_AND_FEEDBACK.md"
14. "MIA_OS_MODEL_PROVIDER_LIFECYCLE.md"
15. "MIA_OS_INTELLIGENCE_SECURITY_REQUIREMENTS.md"
16. "MIA_OS_INTELLIGENCE_OBSERVABILITY.md"
17. "MIA_OS_INTELLIGENCE_FAILURE_AND_DEGRADATION.md"
18. "MIA_OS_INTELLIGENCE_ARCHITECTURE_DIAGRAMS.md"
19. "MIA_OS_INTELLIGENCE_TECHNOLOGY_EVALUATION.md"
20. "MIA_OS_INTELLIGENCE_ACCEPTANCE_CRITERIA.md"
21. "MIA_OS_INTELLIGENCE_OPEN_QUESTIONS.md"

Also update:

- "MIA_OS_MASTER_PLAN.md"
- "MIA_OS_DECISION_LOG.md"
- "MIA_OS_OPEN_QUESTIONS.md"
- "MIA_OS_RISK_REGISTER.md"
- "MIA_OS_REQUIREMENTS_TRACEABILITY.md"
- "MIA_OS_IMPLEMENTATION_STATUS.md"
- "MIA_OS_FEATURE_ECOSYSTEM.md" where intelligence dependencies need clarification.

Ensure all documents remain consistent with Prompts 00–06.

---

23. Decision Records and Architecture Traceability

Create formal decision records for major intelligence architecture decisions.

Each decision must include:

- Decision ID.
- Title.
- Context.
- Requirements affected.
- Options evaluated.
- Evidence.
- Selected approach.
- Rejected alternatives.
- Consequences.
- Risks.
- Reversibility.
- Conditions for reconsideration.

Maintain traceability between:

- System requirements.
- Hardware requirements.
- Intelligence components.
- Provider interfaces.
- Memory architecture.
- Application dependencies.
- Future implementation phases.

Clearly distinguish proposed decisions from approved decisions.

Do not silently change established MIA OS requirements.

---

24. Acceptance Criteria

Prompt 07 is complete only when:

- The existing MIA intelligence infrastructure has been audited.
- MIA identity is separated from individual AI models.
- A provider-independent architecture is defined.
- Local and cloud inference strategies are established.
- Model routing requirements are documented.
- Multi-model council architecture is defined.
- Memory infrastructure and context assembly are designed.
- Multimodal processing is addressed.
- Voice and continuous conversation architecture is established.
- Model capability registration is defined.
- Intelligence quality evaluation is measurable.
- Learning and feedback mechanisms are clearly distinguished.
- Provider lifecycle management is defined.
- Security and privacy boundaries are established.
- Observability requirements are documented.
- Failure and degraded operation are addressed.
- All major technologies are evaluated against actual MIA requirements.
- Hardware dependencies are consistent with Prompt 06.
- All deliverables and decision records are complete.
- Open questions and risks are explicit.

---

25. Boundaries With Future Prompts

Do not duplicate the detailed scope of later prompts.

- Prompt 08 handles agent runtime, task planning, autonomy, action execution, and intelligent system management.
- Prompt 09 handles self-awareness, introspection, capability verification, diagnostics, and controlled self-development.
- Prompt 10 handles the desktop and primary user interface.
- Prompt 11 handles visual identity, themes, and spatial interfaces.
- Prompt 12 handles complete multi-device and distributed MIA architecture.
- Prompt 13 handles comprehensive security, privacy, identity, and permission architecture.
- Prompt 14 handles boot, recovery, updates, and reliability.
- Prompt 15 handles development and build infrastructure.
- Prompt 16 handles implementation sequencing and migration.
- Prompt 17 consolidates and independently reviews the final master plan.

This prompt establishes the intelligence services and contracts that those later systems will consume.

In particular, do not design the complete autonomous agent runtime here. Establish the intelligence interfaces it will need, while leaving autonomy and execution policy to Prompt 08.

---

26. Planning Restrictions

This is an architecture research and planning exercise.

Do not:

- Rewrite existing AI services.
- Replace existing models.
- Change provider configurations.
- Modify persistent memory.
- Delete conversation history.
- Expose API keys or credentials.
- Install new inference engines.
- Download large models.
- Begin implementation.
- Make purchases.
- Change production behavior.

You may inspect existing code, configuration, documentation, and non-sensitive diagnostics.

Do not expose secrets in generated documentation.

Do not assume an existing integration works simply because configuration or source code exists.

Document evidence and uncertainty.

---

27. Final Objective

The final intelligence architecture should make MIA independent of any individual AI provider while allowing her to use the best available intelligence for each task.

MIA should be able to converse naturally, reason deeply, remember meaningfully, understand multiple modalities, consult a council of specialized models, and operate across local and cloud environments.

Her identity, continuity, memory, and relationship with the user must remain anchored in MIA's own architecture rather than in the temporary model generating a response.

She should understand which intelligence capabilities are available, choose appropriate resources, recognize limitations, evaluate results, and degrade gracefully when components fail.

The infrastructure should support a future in which local models become increasingly capable, cloud models continue evolving, and new specialized intelligence systems can be added without redesigning MIA.

The ultimate goal is not to create an assistant that merely has access to many models.

It is to create a unified intelligence platform through which MIA can coordinate many forms of intelligence while remaining one coherent, persistent system.

Produce a technically rigorous, evidence-based, internally consistent intelligence architecture.

When complete, summarize:

1. The recommended intelligence architecture.
2. The most consequential technical decisions.
3. The recommended initial provider and local inference strategy.
4. The memory and identity architecture.
5. The council architecture.
6. The largest unresolved risks.
7. Any decisions requiring user approval.
8. The questions that must be resolved before Prompt 08.

Stop after completing Prompt 07. Wait for review and approval before beginning Prompt 08.
