# MIA: Natural Continuous Conversation Mode (Phone Call Experience)

*From Zac, 2026-11-10, kept as given. Claude's inspection of the voice architecture and the plan: `docs/CONVERSATION_MODE_PLAN.md`.*

I want to introduce a new interaction mode for MIA that makes talking to her feel much more like having a natural phone conversation with another person.

Currently, voice interaction feels too much like a walkie-talkie:

1. Press the microphone button.
2. Say something.
3. Wait for MIA to process what I said.
4. Wait for her response.
5. Press the microphone button again to respond.

I want to move beyond this interaction model.

The Vision

I want to be able to start a conversation with MIA, and from that point forward, simply talk to her naturally, as if I'm on a phone call.

Once the conversation starts:

- MIA continuously listens for my speech without requiring me to press the microphone button for every message.
- When I finish speaking, MIA recognizes that I've finished and begins processing my message.
- MIA responds using her voice.
- Once she finishes speaking, she automatically returns to listening.
- I can immediately respond without touching anything.
- We can continue this back-and-forth conversation for as long as I want.

The experience should feel fluid, conversational, and nearly instantaneous.

Essential Capabilities

1. Continuous Listening

- Maintain an active listening session throughout the conversation.
- Use voice activity detection to recognize when I begin and finish speaking.
- Automatically distinguish speech from background noise and silence.
- Avoid requiring manual microphone activation between turns.

2. Natural Conversation Flow

- Automatically transition between listening, thinking, and speaking.
- Minimize the silence between my message and MIA's response.
- Stream responses whenever possible rather than waiting for an entire response to be generated.
- Avoid awkward pauses and unnecessary confirmation messages.

3. Interruptions and Barge-In
This is particularly important.

I should be able to interrupt MIA while she's speaking, just like I could interrupt another person during a phone call.

When I start speaking:

- MIA should recognize that I'm talking.
- Immediately stop or pause her current speech.
- Switch attention to what I'm saying.
- Process my interruption and respond accordingly.

She should also understand natural conversational behavior, including brief interjections, corrections, and changing subjects.

4. Natural Conversational Personality
MIA should not sound like she's reading responses from a chatbot.

She should:

- Speak naturally and conversationally.
- Avoid unnecessarily long responses.
- Understand conversational context and references.
- Use appropriate pauses and natural speech patterns.
- Recognize when a short response is more appropriate than a detailed explanation.
- Feel like an intelligent companion rather than a voice-command interface.

5. Conversation Controls

Provide simple controls to:

- Start a live conversation.
- End the conversation.
- Temporarily mute or pause listening.
- Resume listening.
- Adjust microphone sensitivity and other audio settings.

The interface should clearly communicate whether MIA is listening, thinking, or speaking.

Technical Direction

Investigate the best architecture for implementing this using MIA's existing voice infrastructure.

Consider:

- Continuous microphone capture.
- Voice Activity Detection (VAD).
- Streaming Speech-to-Text.
- Streaming Text-to-Speech.
- Low-latency response generation.
- Full-duplex audio interaction where supported.
- Interruption detection and playback cancellation.
- Conversation session management.
- Echo cancellation so MIA doesn't mistake her own voice for mine.
- Background noise suppression.

Avoid implementing this as simply an automatically repeated push-to-talk mechanism. I want a genuinely continuous conversational experience.

Integration With MIA

This should become a first-class interaction mode available throughout MIA, not an isolated voice experiment.

I envision having two primary voice interaction styles:

- Command Mode: Existing push-to-talk interaction for quick commands and deliberate voice input.
- Conversation Mode: Continuous, natural, phone-call-style interaction.

Both should share MIA's existing personality, memory, context, capabilities, and permissions.

The experience should eventually work consistently across my phone, PC, and Meta Ray-Ban Display glasses, accounting for each device's microphone and audio capabilities.

Before Implementation

First, inspect MIA's existing voice architecture and identify:

1. What infrastructure can be reused.
2. What needs to change.
3. What technologies or components would be needed.
4. Potential latency and performance bottlenecks.
5. How to support interruptions reliably.
6. How this should integrate with the existing interface and device ecosystem.

Then propose an implementation plan that fits MIA's existing architecture.

The ultimate goal: I want to be able to say "Hey MIA, let's talk," and then have a completely natural conversation with her without ever needing to touch the microphone button again until I decide to end the conversation.

I want it to feel like I'm talking to someone, not operating a piece of software.
