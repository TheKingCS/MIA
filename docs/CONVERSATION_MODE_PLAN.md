# Conversation Mode: what is there today, and a plan

*Claude, 2026-11-10. Answers the "Before Implementation" section of
`docs/specs/CONVERSATION_MODE.md` (Zac's spec, kept verbatim). Nothing
here is built. It is a proposal: the choices in section 8 are Zac's.*

The spec asks for a phone call with MIA: the microphone stays open, she
knows when you've finished, she starts answering quickly, and you can
talk over her. It also says not to build it as push-to-talk pressed
automatically. This document says what the voice code does now, what of
it carries over, what has to be new, and in what order.

How this was written: by reading the code named below. Nothing was
timed for it. Every number in section 4 that isn't marked *measured* is
an estimate to be replaced by a measurement (stage 0).

## 0. What happens today

There are three ways to talk to her, and all three are one recording in,
one finished reply out.

| Where | Hearing | Answering | Speaking |
|---|---|---|---|
| Desktop (Qt Assistant, and the headless `core/voice_loop.py`) | `VoiceManager.start_recording()` / `stop_recording()` (sounddevice) writes a WAV while a button is held; Vosk's small model reads the whole file | `core/assistant_turn.run_assistant_turn()` | `VoiceManager.synthesize()` writes the whole reply to a WAV (Kokoro, Piper as fallback), `play()` plays it |
| Web pages (Talk on every page, `web/assistant.js`, `web/glasses.js`) | `MIAShell.voiceRecorder()`: the browser records until you press stop, the page converts it to 16 kHz WAV and posts all of it to `/api/voice/turn` | the same turn, inside `respond()` in `server/app.py` | the server synthesizes the whole reply and returns it as base64 inside the JSON answer; the page plays it |
| Phone app and glasses (`Voice.kt`, owned by `ListenService.kt`) | Android's own speech recognizer, one utterance per tap; the words (not the sound) go to `/api/glasses/voice` | the same turn, through `core/glasses_voice.handle()` | Android's own text-to-speech on the phone |

What that means for a call:

- **Nothing streams.** The model is called with `"stream": False`
  (`core/llm_manager.py`), the voice is made only after the whole reply
  exists, and the sound travels as one block. Her first word waits for
  her last.
- **Nothing decides you've finished** in MIA's own code. A button or a
  tap ends the recording; on the phone, Android's recognizer ends it.
- **She can't be interrupted.** `VoiceManager.stop_playback()` exists
  for the desktop, but nothing is listening while she speaks, and the
  web pages keep no handle on the sound they started.
- **Each turn is a separate request.** Nothing holds "we are in a
  conversation" between them except the stored conversation.

## 1. What can be reused

Most of what makes a turn *right* is reusable as it stands; what has to
change is how sound gets in and out around it.

- **The turn itself**: `run_assistant_turn()` with everything it
  carries: instant answers from code, the safety floor, her own
  records, tools, actions and their approval, memories, the follow-up.
  A call must go through it, not around it, or a call would be a second,
  weaker MIA.
- **Ordering and locking**: one conversation's turns in order
  (`conversation_lock`), the store lock released while the model thinks.
- **How a reply is shaped for speech**: `core/response_composer.py`
  (the phone and glasses surfaces already strip openers and closers) and
  `prepare_text_for_speech()`.
- **Her voice**: Kokoro through `VoiceManager.synthesize()`. Its own
  notes say about five times faster than real time on the home
  computer, which is what makes sentence-by-sentence speech possible.
- **Vosk can already hear as it goes.** `VoskBackend.transcribe()` feeds
  the recognizer in pieces; the same recognizer gives partial words and
  an end-of-utterance signal when fed live audio. Today that ability is
  unused.
- **Stage timings**: `turn_timings()` already logs heard / thought /
  spoke for every phone turn. That is the baseline to beat.
- **A pushed channel exists**: `/api/live` (server-sent events) shows the
  server and the pages can hold a connection open. The `websockets`
  package is installed, so a two-way socket needs no new dependency.
- **The phone's always-on microphone service**: `ListenService.kt` is a
  foreground microphone service that survives the app being closed and
  the screen being off, claims the headset button, and routes sound
  through the glasses (`Voice.useHeadset`). A call is that service
  staying in the conversation instead of listening once.
- **What she is doing, shown**: listening / thinking / speaking / ready
  already drive the glasses' orb (`/api/glasses/orb`) and the Talk orb.

## 2. What needs to change

1. **A conversation session in core** (new, `core/conversation_mode.py`):
   one object per call holding its state (listening, hearing you,
   thinking, speaking, interrupted, ended) and the rules for moving
   between them. Pure logic, no audio, so it can be tested with made-up
   events. Devices feed it events and act on what it says.
2. **Continuous hearing with end-of-utterance detection.** The
   microphone stays open; a voice-activity detector marks speech and
   silence; a pause long enough ends your turn. This replaces "press to
   stop".
3. **A two-way connection** for the length of the call (a WebSocket,
   `/api/call`): sound up, and down come events (heard so far, she is
   thinking, a sentence of text, a piece of sound, stop).
4. **A reply that arrives as it's written.** A streamed chat call in
   `core/llm_manager.py`, and a path through the turn that hands on each
   finished sentence. *This is the one change inside files I've been
   keeping my hands off* (the model check in CI watches them); it needs
   Zac's say-so.
5. **Speech made sentence by sentence.** The first sentence is spoken
   while the second is still being written.
6. **Interruption** (section 5).
7. **What a call does about tools and approvals.** A tool that takes a
   few seconds needs a short spoken "one moment" (a fixed line from
   code, not the model). An action that needs approval is asked aloud
   and approved by a spoken yes, by the same person-approves rule as
   everywhere else; anything outward or irreversible still shows on a
   screen.
8. **A "call" surface in the composer**: shorter replies, no lists, no
   markdown, nothing that only makes sense read.

What should *not* change: the stored conversation (a call is a
conversation like any other and appears in the list), the safety floor
running in code on every utterance, and "facts are assembled in code,
the model phrases them".

## 3. Technologies and components

| Need | Proposed | Why | Cost |
|---|---|---|---|
| Voice activity (is someone speaking?) | Silero VAD as an ONNX model, run with `onnxruntime` | `onnxruntime` is already installed for Kokoro; the model is about 2 MB; runs on CPU in well under real time | one small model file in `voice_models/` |
| End of utterance | silence after speech from the VAD, with the wait adjusted by what was heard (a trailing "and" or "um" waits longer) | a fixed pause is either too slow or cuts people off | tuning, by ear |
| Speech to text | **Decision needed.** Vosk small (installed) for live partial words; consider `faster-whisper` for the final text of each utterance | Vosk small was chosen for the Pi and mishears open conversation; a call makes that much more noticeable. Whisper on the home computer is far more accurate | a new dependency and a model download (hundreds of MB); more load on the PC |
| Transport | FastAPI WebSocket | already available; one connection carries both directions | none |
| Model | the model already running through Ollama, called with streaming | no new model | a new method in `core/llm_manager.py` |
| Voice | Kokoro, per sentence | already her voice | none |
| Echo cancellation | the browser's and Android's own (`echoCancellation` on `getUserMedia`; the voice-communication audio source on Android) | she must not hear herself; both platforms ship this and it's good | none on the phone and in the web view; the Qt-native desktop path has none |
| Phone | a call mode in `ListenService.kt` | the service, permissions, headset routing and notification exist | Kotlin, compiled only by CI, tried only on the real phone |

Nothing here needs the internet. Whisper, if chosen, runs locally.

## 4. Where the time goes

A reply feels like conversation when her first word comes within about
a second of your last. Today's chain, for a spoken turn from a web page:

| Step | Today | In a call |
|---|---|---|
| Knowing you've stopped | you press stop | the pause that ends the turn: about 0.6 to 0.8 s *(estimate; this wait is itself part of the delay)* |
| Getting the sound there | whole recording converted and uploaded after you stop | already there, it was sent as you spoke |
| Speech to text | the whole file, after upload | done as you speak; only the last words remain |
| The model | waits for the entire reply | first sentence only *(depends on the model and the size of what it is sent; to be measured)* |
| The voice | the whole reply synthesized | the first sentence |
| Getting the sound back | the whole reply, base64 inside JSON | first sentence, as it's made |

Known bottlenecks, largest first:

1. **The model's time to its first words.** A turn sends her
   instructions, the facts assembled for it, and tool definitions. The
   time to read all that comes before any word. Streaming doesn't
   shorten it; a smaller prompt for call turns might. Needs measuring
   before deciding anything.
2. **Turns that use a tool** call the model twice. This is where a
   spoken "one moment" earns its place.
3. **Answers that never reach the model** (instant answers, greetings,
   the safety floor) are already fast and will feel immediate.
4. **The end-of-turn pause.** Too short and she talks over a breath;
   too long and every reply drags.
5. **The home computer doing three things at once** (hearing, the
   model, the voice). The voice and the model compete for the same
   machine while she speaks and thinks ahead.
6. **A phone away from home** adds the network both ways. The phone's
   own recognizer and voice (what `Voice.kt` uses now) remain the
   fallback when home can't be reached.

## 5. Interruptions

The hard part is not stopping her; it's knowing that the sound is *you*
and not her own voice, a cough, or "mm-hm".

- **Echo first.** With the microphone open while she speaks, her voice
  comes back in. Use the platform's echo cancellation and play her voice
  through the same page or app that holds the microphone, so the
  canceller knows what to subtract. Headphones or the glasses make this
  nearly a non-problem.
- **A real interruption** is speech lasting more than a moment (about a
  third of a second of voiced sound) while she is speaking. Shorter
  sounds, and a short list of listening noises ("mm-hm", "yeah",
  "okay"), don't stop her.
- **Stopping is the device's job.** The page or the phone stops the
  sound at once and tells the server; it doesn't wait to be told. Then
  the server stops writing and stops making speech.
- **What she said is what you heard.** The reply stored in the
  conversation is cut to the sentences actually spoken, marked as
  interrupted, so her next turn doesn't refer to things you never heard.
- **Then she listens**, and your interruption is the next turn.
- **Actions.** An action already carried out when you interrupt stays
  done and stays undoable in the usual way; she says so if it matters.
  An approval never rides on an interrupted sentence.

Where echo cancellation isn't available (the desktop's Qt-native voice
path with open speakers), the call runs half-duplex: she finishes or you
press a key. The desktop window is the web front end now, so in practice
the page's microphone is used there and this case is the exception.

## 6. How it fits MIA

- **One conversation mode, three devices** (DEC-0125): started by voice
  ("let's talk") and by a Call control in Talk; ended by voice or the
  control. Same abilities everywhere; what differs is what's shown.
- **Phone**: the natural home for it. Works with the screen off and
  through the glasses, via the existing service.
- **Glasses**: the orb already follows listening / thinking / speaking.
  A call adds only "in a call" and the words heard.
- **Desktop window**: the Talk panel, with the orb.
- **The microphone is never open quietly.** A call is always visible
  (the orb, the phone's notification), ends itself after a stretch of
  silence, and keeps no recording: sound is held in memory only long
  enough to be turned into words.
- **Private and personal conversations** keep their existing rules
  (nothing offered to keep, nothing sent for a second opinion).
- **The communication gate** isn't involved: everything she says in a
  call is a reply to you.
- **Music**: the shared player (`web/player.js`) should drop its volume
  or pause while a call is on, and come back after.

## 7. Proposed order

Each stage is usable on its own and each ends with something Zac can try.

0. **Measure.** Ten spoken turns on the home computer with the real
   model, recording each stage. Try the same ten with Vosk and with
   Whisper for accuracy. This decides the speech-to-text question and
   shows whether the model's first-word time needs work before anything
   else.
1. **A reply that streams, no microphone changes.** The session object,
   the streamed model call, sentence-by-sentence voice, the socket.
   Typed and push-to-talk turns already get faster: her first sentence
   plays while the rest is written.
2. **Hands-free turns in the web page.** The microphone stays open, the
   detector ends your turn, she answers, it listens again. While she
   speaks the microphone is ignored (no interruption yet). This is
   already not push-to-talk: nothing is pressed between turns.
3. **Interruption.** Full duplex with echo cancellation, the rules in
   section 5, the stored reply cut to what was heard.
4. **The phone app and the glasses.** Call mode in the listening
   service, through the headset, with the screen off.
5. **Feel.** The pause adjusted by what was said, listening noises
   ignored, "one moment" during tools, the call surface in the composer,
   music ducking.

Tests follow the existing split: the session and its rules with made-up
events (no audio, no real process); the socket with FastAPI's test
client; real sound checked by hand with a script that isn't run by
pytest, as the voice and music checks already are.

## 8. Decisions for Zac

1. **Speech to text**: keep Vosk small, or add Whisper on the home
   computer for accuracy (a new dependency and a model download)?
   Stage 0 gives the evidence.
2. **Changing `core/llm_manager.py`** to add a streamed call. Nothing
   existing changes behaviour; the model check will run on it.
3. **Which device first** after the web page: I'd propose the phone with
   the glasses, since that's where a call is most useful.
4. **How long a silent call stays open** before ending itself.
5. **Spoken approval**: is a spoken "yes" enough to approve a routine
   action during a call, with outward or irreversible ones still needing
   a screen? This follows the existing rule (routine actions run with an
   exact undo), but a call is a new place to apply it.

## 9. What this document doesn't know

- No timings were taken for it. Section 4's shape is from the code; its
  numbers aren't measurements.
- How well echo cancellation works through the glasses' speakers and
  microphone is unknown until tried.
- Whether Android lets the recognizer run continuously in the
  background service the way one-shot listening does, or whether the
  phone has to send raw sound home instead, needs a small experiment
  early in stage 4.
- Whether the home computer can run Whisper, the model and Kokoro
  together without the model slowing noticeably.
