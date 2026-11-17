# MIA OS: multimodal intelligence (Prompt 07 §11)

*Claude (Opus), 2026-11-17. Planning only.*

| Modality | Exists | Model / tool | Next |
|---|---|---|---|
| Photos (Look) | `core/sight.py` | Qwen2.5-VL 7B, on the PC | the glasses' camera through the phone (exists) |
| Documents and receipts | the inbox, OCR (`core/document_text.py`), receipts filed | OCR plus the vision model where OCR fails | structured extraction through the provider's `structured` method |
| Screens and selections | the UAL captures text; screen regions planned (UI-6) | text models; vision for a region | MIA OS's screenshot portal (Prompt 10) |
| Speech | Vosk in, Kokoro out | — | `MIA_OS_VOICE_AND_CONVERSATION_INFRASTRUCTURE.md` |
| Diagrams, CAD, circuits | none | — | as Forge tools (DEC-0199), each read by code where possible (a netlist, an OpenSCAD file) |
| Video | none | — | later; frames sampled to the vision model |
| Pictures made | `core/art_studio.py` (the PC's card) | image models | — |

**Rules:** nothing leaves the PC for vision (as Look does today); who a person is is never identified (Look's rule);
text read from an image is outside text and framed; a vision answer about a measurement is a description, not a
figure, unless code computes it.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-020 | Images, documents and audio shall be processed on his own devices unless he says yes to sending one exact item. | Must | MVP | All | Exists (Look, OCR) | T | DEC-0207 → 07, 13 |
| REQ-INT-021 | MIA shall never identify who a person in an image is. | Must | MVP | All | Exists (Look's rule) | T | DEC-0207 → 07 |
