globalThis.window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }) };
globalThis.document = { documentElement: { dataset: {}, style: { setProperty() {} } }, querySelector: () => ({ style: { setProperty() {} } }) };
globalThis.localStorage = { _s: {}, getItem(k) { return this._s[k] ?? null; }, setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; } };
globalThis.location = { href: "http://localhost:5173/", origin: "http://localhost:5173" };

const mod = await import("./bundle.mjs");
const { photoQuestionUrl, actions, getState } = mod;
const fail = (m) => { console.log("FAIL:", m); process.exit(1); };
const text = (t) => ({ kind: "text", text: t });

// Scenario: the seeded Arif photo sits several messages back (the reported repro).
const before = getState().messages.filter((m) => m.chatId === "arif");
const seedPhoto = [...before].reverse().find((m) => m.body.kind === "image");
if (!seedPhoto) fail("no seeded arif photo");
for (let i = 1; i <= 5; i++) actions.sendToChat(text(`filler ${i}`), "arif");
const q1 = "@messenger what is he doing in this image";
actions.sendToChat(text(q1), "arif");
const got1 = photoQuestionUrl("arif", q1);
if (got1 !== seedPhoto.body.url) fail(`old-photo question: want seed photo, got ${got1}`);
console.log("PASS old photo found 6 back:", String(got1).slice(0, 60));

// Bare question with an old photo must still NOT match (no caption-guessing widening).
const got2 = photoQuestionUrl("arif", "what is he doing");
if (got2 !== null) fail(`bare question should be null, got ${got2}`);
console.log("PASS bare question stays tight: null");

// Tight window preserved: latest message IS the photo.
actions.sendToChat({ kind: "image", url: "https://x.test/new.jpg" }, "arif");
const got3 = photoQuestionUrl("arif", "what is he doing");
if (got3 !== "https://x.test/new.jpg") fail(`latest-photo question: got ${got3}`);
console.log("PASS latest photo still matches");

// Non-questions never match ("tell …" counts as a question word by design, so use a plain statement).
if (photoQuestionUrl("arif", "good morning arif") !== null) fail("statement matched");
console.log("PASS statement: null");
console.log("ALL PHOTO-WINDOW CHECKS PASSED");
