// Node harness for server/static/voice.js — driven by tests/test_phone_voice_js.py.
const path = require("path");
const voice = require(path.join(__dirname, "..", "..", "server", "static", "voice.js"));

const RATE = 48000;
const BLOCK = 4096;

function tone(ms, amplitude) {
    const n = Math.round((RATE * ms) / 1000);
    const out = new Float32Array(n);
    for (let i = 0; i < n; i++) out[i] = amplitude * Math.sin((2 * Math.PI * 220 * i) / RATE);
    return out;
}

function concat(parts) {
    const total = parts.reduce((n, p) => n + p.length, 0);
    const out = new Float32Array(total);
    let o = 0;
    for (const p of parts) { out.set(p, o); o += p.length; }
    return out;
}

function run(signal, options = {}) {
    const d = new voice.SpeechDetector(Object.assign({ sampleRate: RATE }, options));
    const states = [];
    for (let i = 0; i < signal.length; i += BLOCK) {
        const s = d.feed(signal.subarray(i, i + BLOCK));
        states.push(s);
        if (s === "done") return { states, utteranceSamples: d.takeUtterance().length };
    }
    return { states, utteranceSamples: null };
}

const scenario = process.argv[2];
let result;
if (scenario === "wav") {
    const samples = voice.downsample(tone(1000, 0.5), RATE);
    result = { base64: Buffer.from(voice.encodeWav(samples)).toString("base64"), samples: samples.length };
} else if (scenario === "speech") {
    result = run(concat([tone(1000, 0.002), tone(1500, 0.3), tone(1500, 0.002)]));
} else if (scenario === "cough") {
    result = run(concat([tone(1000, 0.002), tone(150, 0.3), tone(2000, 0.002)]));
} else if (scenario === "max") {
    result = run(concat([tone(500, 0.002), tone(5000, 0.3)]), { maxUtteranceMs: 2000 });
} else if (scenario === "noisy") {
    // Loud steady background (road noise) then clearly louder speech.
    result = run(concat([tone(2000, 0.05), tone(1500, 0.4), tone(1500, 0.05)]));
} else {
    throw new Error(`unknown scenario ${scenario}`);
}
process.stdout.write(JSON.stringify(result));
