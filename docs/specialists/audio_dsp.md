# Audio signal processing

*One of MIA's specialists (DEC-0109). Written by `core/specialists.py` from its workbook (`work/specialists/audio_dsp.json`); don't edit by hand.*

Sound as numbers: sample rates and bit depth, buffers and latency, filters and equalisers, FFTs, delays and mixing, codecs, I2S and audio on a microcontroller, and keeping audio smooth on small hardware.

**Limits:** Numbers come from her calculators (core/eng_calcs.py), never from memory. A change that makes audio louder says how loud it ends up at the ears (the acoustics specialist's safe listening time). Every note says where it comes from; a claim without a source isn't written. When the right answer depends on where someone lives (a code, a law, a licence), the note says so and names who to check with. Nothing about a real person's private life.

**Develops:** skills: Technology, Creative.

## Open questions

- How small can an audio buffer be on an ESP32 before it crackles?
- What sample rate and bit depth does voice need, and what does music need?
- How do you design a simple equaliser filter?
