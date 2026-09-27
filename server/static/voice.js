// MIA phone voice: microphone capture, end-of-speech detection, and
// 16 kHz mono WAV encoding (the format MIA's offline Vosk model wants),
// so the computer at home needs no audio conversion tools.
//
// The pure helpers (downsample, encodeWav, SpeechDetector) are exported
// for Node too, so they can be unit-tested outside a browser.

(function (root) {
    "use strict";

    const TARGET_RATE = 16000;

    // Average-downsample Float32 samples from inputRate to TARGET_RATE.
    function downsample(samples, inputRate, targetRate = TARGET_RATE) {
        if (inputRate === targetRate) return Float32Array.from(samples);
        if (inputRate < targetRate) throw new Error("Input sample rate is below the target rate.");
        const ratio = inputRate / targetRate;
        const outLength = Math.floor(samples.length / ratio);
        const out = new Float32Array(outLength);
        for (let i = 0; i < outLength; i++) {
            const start = Math.floor(i * ratio);
            const end = Math.min(samples.length, Math.floor((i + 1) * ratio));
            let sum = 0;
            for (let j = start; j < end; j++) sum += samples[j];
            out[i] = end > start ? sum / (end - start) : 0;
        }
        return out;
    }

    // Float32 [-1, 1] samples -> mono 16-bit PCM WAV bytes.
    function encodeWav(samples, sampleRate = TARGET_RATE) {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);
        const writeString = (offset, text) => {
            for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
        };
        writeString(0, "RIFF");
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(8, "WAVE");
        writeString(12, "fmt ");
        view.setUint32(16, 16, true);          // fmt chunk size
        view.setUint16(20, 1, true);           // PCM
        view.setUint16(22, 1, true);           // mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true); // byte rate
        view.setUint16(32, 2, true);           // block align
        view.setUint16(34, 16, true);          // bits per sample
        writeString(36, "data");
        view.setUint32(40, samples.length * 2, true);
        for (let i = 0; i < samples.length; i++) {
            const s = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
        }
        return new Uint8Array(buffer);
    }

    function rms(samples) {
        let sum = 0;
        for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
        return samples.length ? Math.sqrt(sum / samples.length) : 0;
    }

    // Decides, block by block, when an utterance starts and ends.
    // feed() returns "idle" | "speech" | "done". Keeps a short pre-roll so
    // the first syllable isn't clipped, adapts to background noise (road
    // noise, AC), and stops after trailing silence or a hard maximum.
    class SpeechDetector {
        constructor({
            sampleRate,
            minThreshold = 0.012,
            noiseMultiplier = 3.0,
            silenceMs = 1200,
            minSpeechMs = 300,
            maxUtteranceMs = 30000,
            preRollMs = 400,
        }) {
            Object.assign(this, { sampleRate, minThreshold, noiseMultiplier, silenceMs, minSpeechMs, maxUtteranceMs, preRollMs });
            this.reset();
        }

        reset() {
            this.noiseFloor = null;
            this.inSpeech = false;
            this.speechMs = 0;
            this.silenceRunMs = 0;
            this.totalMs = 0;
            this.preRoll = [];
            this.preRollMsHeld = 0;
            this.chunks = [];
        }

        threshold() {
            return Math.max(this.minThreshold, (this.noiseFloor || 0) * this.noiseMultiplier);
        }

        feed(block) {
            const ms = (block.length / this.sampleRate) * 1000;
            const level = rms(block);
            const loud = level > this.threshold();

            if (!this.inSpeech) {
                // Track background noise only while nobody is talking.
                this.noiseFloor = this.noiseFloor === null ? level : this.noiseFloor * 0.95 + level * 0.05;
                this.preRoll.push(block);
                this.preRollMsHeld += ms;
                while (this.preRoll.length > 1 && this.preRollMsHeld - (this.preRoll[0].length / this.sampleRate) * 1000 >= this.preRollMs) {
                    this.preRollMsHeld -= (this.preRoll.shift().length / this.sampleRate) * 1000;
                }
                if (!loud) return "idle";
                this.inSpeech = true;
                this.chunks = this.preRoll.slice();
                this.totalMs = this.preRollMsHeld;
                this.preRoll = [];
                this.preRollMsHeld = 0;
                this.speechMs = ms;
                this.silenceRunMs = 0;
                return "speech";
            }

            this.chunks.push(block);
            this.totalMs += ms;
            if (loud) {
                this.speechMs += ms;
                this.silenceRunMs = 0;
            } else {
                this.silenceRunMs += ms;
            }
            if (this.totalMs >= this.maxUtteranceMs) return "done";
            if (this.silenceRunMs >= this.silenceMs) {
                if (this.speechMs >= this.minSpeechMs) return "done";
                // A cough or door slam, not speech: go back to waiting.
                this.reset();
                return "idle";
            }
            return "speech";
        }

        takeUtterance() {
            const length = this.chunks.reduce((n, c) => n + c.length, 0);
            const out = new Float32Array(length);
            let offset = 0;
            for (const c of this.chunks) { out.set(c, offset); offset += c.length; }
            this.reset();
            return out;
        }
    }

    // Browser-only: live microphone -> SpeechDetector -> WAV callback.
    class Microphone {
        constructor({ onUtterance, onLevelState }) {
            this.onUtterance = onUtterance;
            this.onLevelState = onLevelState || (() => {});
            this.paused = true;
        }

        async start() {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
            });
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioCtx();
            await this.ctx.resume();
            const source = this.ctx.createMediaStreamSource(this.stream);
            // ScriptProcessor is deprecated but, unlike AudioWorklet, works on every phone browser today.
            this.processor = this.ctx.createScriptProcessor(4096, 1, 1);
            const mute = this.ctx.createGain();
            mute.gain.value = 0;
            source.connect(this.processor);
            this.processor.connect(mute);
            mute.connect(this.ctx.destination);
            this.detector = new SpeechDetector({ sampleRate: this.ctx.sampleRate });
            this.processor.onaudioprocess = (event) => this._onBlock(event.inputBuffer.getChannelData(0));
        }

        _onBlock(channelData) {
            if (this.paused) return;
            const state = this.detector.feed(Float32Array.from(channelData));
            this.onLevelState(state);
            if (state === "done") {
                this.paused = true; // stop listening while MIA thinks and answers
                const samples = downsample(this.detector.takeUtterance(), this.ctx.sampleRate);
                this.onUtterance(encodeWav(samples));
            }
        }

        listen() {
            if (this.detector) this.detector.reset();
            this.paused = false;
        }

        pause() {
            this.paused = true;
        }

        stop() {
            this.paused = true;
            if (this.processor) this.processor.disconnect();
            if (this.stream) this.stream.getTracks().forEach((t) => t.stop());
            if (this.ctx) this.ctx.close();
            this.processor = this.stream = this.ctx = null;
        }
    }

    const api = { TARGET_RATE, downsample, encodeWav, rms, SpeechDetector, Microphone };
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    else root.MIAVoice = api;
})(typeof window !== "undefined" ? window : globalThis);
