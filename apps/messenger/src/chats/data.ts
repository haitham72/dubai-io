import type { Chat, Contact, Message } from "../types";
import { avatar, img } from "../ui";

export const me: Contact = { id: "me", name: "Haitham", avatar: avatar(12), online: true };

const c = (id: string, name: string, n: number, online = false): Contact => ({ id, name, avatar: avatar(n), online });

export const contacts = {
  arif: c("arif", "Arif Khan", 15, true),
  sara: c("sara", "Sara Ali", 47),
  travel: { id: "travel", name: "Travel Buddies", avatar: img("photo-1507525428034-b723cf961d3e", 120) },
  mazen: c("mazen", "Mazen", 53),
  family: { id: "family", name: "Family", avatar: img("photo-1511895426328-dc8714191300", 120) },
  gaming: { id: "gaming", name: "Gaming Squad", avatar: img("photo-1542751371-adc38448a05e", 120) },
  lina: c("lina", "Lina", 44),
  omar: c("omar", "Omar", 59),
  hana: c("hana", "Hana", 32),
  study: { id: "study", name: "Study Group", avatar: img("photo-1522202176988-66273c2fd55f", 120) },
  // Near-namesakes on purpose: voice commands must never send to the wrong one (agents/ eval: wrong-recipient count).
  sarah: c("sarah", "Sarah Malik", 25),
  omer: c("omer", "Omer Farooq", 5),
  lena: c("lena", "Lena Haddad", 9),
} satisfies Record<string, Contact>;

export const chats: Chat[] = [
  { id: "arif", contact: contacts.arif, preview: "Also heard the Grand Egyptian Museum is fully open now", time: "4:16 PM", unread: 2 },
  { id: "sara", contact: contacts.sara, preview: "That's amazing! 😍", time: "6:28 PM", unread: 1 },
  { id: "travel", contact: contacts.travel, preview: "Omar: Bali itinerary 🌴", time: "5:17 PM", unread: 4 },
  { id: "mazen", contact: contacts.mazen, preview: "Haha good one!", time: "3:50 PM", unread: 0, muted: true },
  { id: "family", contact: contacts.family, preview: "Mom: Dinner is ready! 🍲", time: "2:03 PM", unread: 3 },
  { id: "gaming", contact: contacts.gaming, preview: "Rashid: Let's play later tonight?", time: "12:21 PM", unread: 0, muted: true },
  { id: "lina", contact: contacts.lina, preview: "Okay, see you tomorrow!", time: "Yesterday", unread: 0 },
  { id: "omar", contact: contacts.omar, preview: "Thanks! 🙏", time: "Yesterday", unread: 1 },
  { id: "hana", contact: contacts.hana, preview: "This is awesome!", time: "Mon", unread: 0 },
  { id: "study", contact: contacts.study, preview: "Adam: New notes are up", time: "Mon", unread: 6 },
  { id: "sarah", contact: contacts.sarah, preview: "Sent you the slides 📎", time: "Sun", unread: 0 },
  { id: "omer", contact: contacts.omer, preview: "Padel at 8?", time: "Sun", unread: 0 },
  { id: "lena", contact: contacts.lena, preview: "Welcome back to Dubai!", time: "Sat", unread: 0 },
];

/** Offline stand-ins for "@messenger create image about this" when image generation is not live (ids already used in the app). */
export const demoImagePool: { url: string; tags: string[] }[] = [
  { url: img("photo-1436491865332-7a61a109cc05", 1200), tags: ["trip", "travel", "flight", "egypt", "january"] },
  { url: img("photo-1507525428034-b723cf961d3e", 1200), tags: ["beach", "weekend", "trip", "travel", "sea"] },
  { url: img("photo-1512453979798-5ea266f8880c", 1200), tags: ["dubai", "city", "travel", "uae"] },
  { url: img("photo-1537996194471-e657df975ab4", 1200), tags: ["bali", "villa", "trip", "holiday"] },
  { url: img("photo-1498837167922-ddd27525d352", 1200), tags: ["food", "dinner", "lunch"] },
  { url: img("photo-1486406146926-c627a92ad1ab", 1200), tags: ["work", "office", "city"] },
];

const m = (id: string, chatId: string, fromMe: boolean, time: string, body: Message["body"]): Message =>
  ({ id, chatId, fromMe, time, body });

export const seedMessages: Message[] = [
  /* ---------------- Arif Khan (25) — beach weekend plan ---------------- */
  m("a1", "arif", true, "Yesterday", { kind: "text", text: "Long day 😮‍💨 finally home" }),
  m("a2", "arif", false, "Yesterday", { kind: "text", text: "Same here. Work was nonstop today" }),
  m("a3", "arif", true, "Yesterday", { kind: "text", text: "We should do something this weekend. Beach? 🏖️" }),
  m("a4", "arif", false, "Yesterday", { kind: "text", text: "Yes please. Kite Beach on Saturday?" }),
  m("a5", "arif", true, "Yesterday", { kind: "text", text: "Saturday works. Morning or sunset?" }),
  m("a6", "arif", false, "Yesterday", { kind: "text", text: "Sunset, obviously. Better light for photos 😎" }),
  m("a7", "arif", true, "Yesterday", { kind: "text", text: "Haha deal. I'll bring snacks" }),
  m("a8", "arif", false, "Yesterday", { kind: "text", text: "And I'll bring the speaker 🎶" }),
  m("a9", "arif", true, "Yesterday", { kind: "text", text: "Perfect combo. Let's confirm Friday" }),
  m("a10", "arif", false, "Yesterday", { kind: "text", text: "👍 night!" }),
  m("a11", "arif", true, "Yesterday", { kind: "text", text: "Good night!" }),
  m("a12", "arif", false, "9:41 AM", { kind: "text", text: "Morning! Still on for Saturday?" }),
  m("a13", "arif", true, "9:55 AM", { kind: "text", text: "Morning! Yes, 100% ✔️" }),
  m("a14", "arif", false, "10:02 AM", { kind: "text", text: "Nice. Should we invite Sara and Omar?" }),
  m("a15", "arif", true, "10:05 AM", { kind: "text", text: "Sure, the more the merrier" }),
  m("a16", "arif", false, "10:07 AM", { kind: "text", text: "I'll ask them in the group" }),
  m("a17", "arif", true, "2:14 PM", { kind: "text", text: "Hey! Are you free this weekend? We could go to the beach or something." }),
  m("a18", "arif", false, "2:14 PM", { kind: "text", text: "Sounds great! See you soon." }),
  m("a19", "arif", true, "2:18 PM", { kind: "text", text: "Yeah! That sounds perfect. Let's do it! 🏝️" }),
  m("a20", "arif", false, "3:03 PM", { kind: "image", url: img("photo-1512453979798-5ea266f8880c", 1200) }),
  m("a21", "arif", false, "3:03 PM", { kind: "text", text: "This place looks amazing 😍" }),
  m("a22", "arif", true, "3:16 PM", { kind: "text", text: "Wow! That looks incredible. I wish I was there already 😅" }),
  m("a23", "arif", false, "3:20 PM", { kind: "text", text: "Haha same! We should plan it soon." }),
  m("a24", "arif", false, "3:44 PM", { kind: "voice", seconds: 18 }),
  m("a25", "arif", true, "3:47 PM", { kind: "text", text: "Definitely! I'll check the dates and let you know. 😊" }),
  /* Egypt trip idea — the context for "@messenger is this true", "create sticker/image of this", "setup plan for this" */
  m("a26", "arif", false, "4:02 PM", { kind: "text", text: "Random idea… Egypt in January? 🇪🇬" }),
  m("a27", "arif", true, "4:03 PM", { kind: "text", text: "I'm in! I've wanted to see the pyramids for years" }),
  m("a28", "arif", false, "4:05 PM", { kind: "text", text: "Omar and Hana said they're taking leave in January too" }),
  m("a29", "arif", true, "4:06 PM", { kind: "text", text: "Nice, let's make it a group trip. 10–12 days?" }),
  m("a30", "arif", false, "4:08 PM", { kind: "text", text: "Yes, but I only have 8 days of leave left 😅" }),
  m("a31", "arif", true, "4:09 PM", { kind: "text", text: "Then we stretch it around the weekends" }),
  m("a32", "arif", false, "4:12 PM", { kind: "text", text: "Budget-wise I'm thinking around 1500 AED spending money each" }),
  m("a33", "arif", false, "4:14 PM", { kind: "text", text: "Cairo + a Nile day trip. Flights from DXB are short, under 4 hours" }),
  m("a34", "arif", false, "4:16 PM", { kind: "text", text: "Also heard the Grand Egyptian Museum is fully open now" }),

  /* ---------------- Sara Ali (14) — promotion + dinner ---------------- */
  m("s1", "sara", true, "Yesterday", { kind: "text", text: "Guess who got promoted?? 🎉" }),
  m("s2", "sara", false, "Yesterday", { kind: "text", text: "NO WAY. Congrats!!! 🎉🎉" }),
  m("s3", "sara", true, "Yesterday", { kind: "text", text: "Thank you!! Still can't believe it" }),
  m("s4", "sara", false, "Yesterday", { kind: "text", text: "We need to celebrate. Dinner this week?" }),
  m("s5", "sara", true, "Yesterday", { kind: "text", text: "Yes! Thursday? That new Italian place?" }),
  m("s6", "sara", false, "Yesterday", { kind: "text", text: "Perfect. I'll book for 7:30" }),
  m("s7", "sara", true, "6:10 PM", { kind: "image", url: img("photo-1495616811223-4d98c6e9c869", 1200), caption: "Sunset from my balcony tonight 🌅" }),
  m("s8", "sara", false, "6:12 PM", { kind: "text", text: "Okay that's gorgeous 😍" }),
  m("s9", "sara", true, "6:13 PM", { kind: "text", text: "Right?? No filter needed" }),
  m("s10", "sara", false, "6:15 PM", { kind: "text", text: "Send me the full-res one, new wallpaper 😄" }),
  m("s11", "sara", false, "6:16 PM", { kind: "voice", seconds: 25 }),
  m("s12", "sara", true, "6:20 PM", { kind: "text", text: "Haha love the excitement 😂 sending it now" }),
  m("s13", "sara", true, "6:25 PM", { kind: "text", text: "They have burrata with figs on the menu btw 🤤" }),
  m("s14", "sara", false, "6:28 PM", { kind: "text", text: "That's amazing! 😍" }),

  /* ---------------- Travel Buddies (20) — Bali planning ---------------- */
  m("t1", "travel", true, "Yesterday", { kind: "text", text: "Bali in November — are we actually doing this? ✈️" }),
  m("t2", "travel", false, "Yesterday", { kind: "text", text: "Omar: YES. I've already checked flights 👀" }),
  m("t3", "travel", false, "Yesterday", { kind: "text", text: "Layla: I'm in if we keep it under AED 4k each" }),
  m("t4", "travel", false, "Yesterday", { kind: "text", text: "Karim: 5 days enough? I can't take more leave" }),
  m("t5", "travel", true, "Yesterday", { kind: "text", text: "5 days works. Ubud + Uluwatu split?" }),
  m("t6", "travel", false, "Yesterday", { kind: "text", text: "Omar: 2 nights Ubud, 3 nights Canggu. Trust me" }),
  m("t7", "travel", false, "Yesterday", { kind: "text", text: "Layla: Canggu for surf? I can't surf 😅" }),
  m("t8", "travel", false, "Yesterday", { kind: "text", text: "Karim: You'll learn. Or just do beach clubs 😄" }),
  m("t9", "travel", true, "Yesterday", { kind: "image", url: img("photo-1555400038-63f5ba517a47", 1200), caption: "Tegalalang terraces — adding this to day 2 🌾" }),
  m("t10", "travel", false, "Yesterday", { kind: "text", text: "Layla: Okay WOW. I'm sold 🌾" }),
  m("t11", "travel", false, "Yesterday", { kind: "text", text: "Omar: Visa on arrival, 30 days. Easy" }),
  m("t12", "travel", true, "Yesterday", { kind: "text", text: "I'll make a doc with the plan tonight" }),
  m("t13", "travel", false, "Yesterday", { kind: "text", text: "Karim: Booked my seat. Window, obviously 🪟" }),
  m("t14", "travel", false, "Yesterday", { kind: "text", text: "Layla: That was fast 😂" }),
  m("t15", "travel", true, "4:30 PM", { kind: "card", title: "Bali on a budget", subtitle: "7 days under AED 3,500 — stays, food, scooter", icon: "research" }),
  m("t16", "travel", false, "4:45 PM", { kind: "text", text: "Omar: That scooter price can't be real 😂" }),
  m("t17", "travel", true, "4:50 PM", { kind: "text", text: "It is! I checked three rental shops" }),
  m("t18", "travel", false, "5:05 PM", { kind: "text", text: "Layla: Fine, I'm booking tonight 💳" }),
  m("t19", "travel", false, "5:10 PM", { kind: "text", text: "Karim: Same. No backing out now" }),
  m("t20", "travel", false, "5:17 PM", { kind: "image", url: img("photo-1537996194471-e657df975ab4", 1200), caption: "Omar: Bali itinerary 🌴" }),

  /* ---------------- Mazen (12) — match + jokes ---------------- */
  m("z1", "mazen", true, "Yesterday", { kind: "text", text: "Did you watch the match last night? ⚽" }),
  m("z2", "mazen", false, "Yesterday", { kind: "text", text: "That last-minute goal was unreal" }),
  m("z3", "mazen", true, "Yesterday", { kind: "text", text: "I screamed so loud the neighbors knocked 😂" }),
  m("z4", "mazen", false, "Yesterday", { kind: "text", text: "Hahaha worth it" }),
  m("z5", "mazen", true, "Yesterday", { kind: "text", text: "Rematch this weekend? My place?" }),
  m("z6", "mazen", false, "Yesterday", { kind: "text", text: "Bringing snacks. Loser cooks 🍳" }),
  m("z7", "mazen", true, "Yesterday", { kind: "text", text: "Deal. You're going down" }),
  m("z8", "mazen", false, "Yesterday", { kind: "text", text: "Famous last words 😌" }),
  m("z9", "mazen", true, "3:45 PM", { kind: "text", text: "Why did the footballer bring string? To tie the score! 😂" }),
  m("z10", "mazen", false, "3:47 PM", { kind: "text", text: "That was terrible 😭" }),
  m("z11", "mazen", true, "3:48 PM", { kind: "text", text: "Terribly good, you mean" }),
  m("z12", "mazen", false, "3:50 PM", { kind: "text", text: "Haha good one!" }),

  /* ---------------- Family (18) — Saturday lunch ---------------- */
  m("f1", "family", false, "Yesterday", { kind: "text", text: "Mom: Good morning everyone ☀️" }),
  m("f2", "family", true, "Yesterday", { kind: "text", text: "Morning mama!" }),
  m("f3", "family", false, "Yesterday", { kind: "text", text: "Noor: Morning! Anyone free Saturday?" }),
  m("f4", "family", false, "Yesterday", { kind: "text", text: "Dad: I'm free after 4" }),
  m("f5", "family", false, "Yesterday", { kind: "text", text: "Mom: Come for lunch then. I'm cooking 🍲" }),
  m("f6", "family", true, "Yesterday", { kind: "text", text: "Yes please! What are you making?" }),
  m("f7", "family", false, "Yesterday", { kind: "text", text: "Mom: Ouzi + salad. Your favorite" }),
  m("f8", "family", false, "Yesterday", { kind: "text", text: "Noor: Save me a plate, I'll be late 🙏" }),
  m("f9", "family", false, "Yesterday", { kind: "text", text: "Dad: There's always leftovers for you" }),
  m("f10", "family", false, "Yesterday", { kind: "image", url: img("photo-1504674900247-0877df9cc836", 1200), caption: "Mom: Taste-test approved ✅" }),
  m("f11", "family", true, "Yesterday", { kind: "text", text: "That looks incredible 😍" }),
  m("f12", "family", false, "Yesterday", { kind: "text", text: "Noor: MOM. I'm at work, this is torture 😭" }),
  m("f13", "family", false, "Yesterday", { kind: "text", text: "Mom: Haha, there will be plenty habibti" }),
  m("f14", "family", false, "Yesterday", { kind: "voice", seconds: 42 }),
  m("f15", "family", false, "Yesterday", { kind: "text", text: "Noor: Dad that voice note made my day 😂" }),
  m("f16", "family", true, "Yesterday", { kind: "text", text: "See you all Saturday ❤️" }),
  m("f17", "family", false, "1:58 PM", { kind: "text", text: "Mom: Bring kunafa if you pass by the shop!" }),
  m("f18", "family", false, "2:03 PM", { kind: "text", text: "Mom: Dinner is ready! 🍲" }),

  /* ---------------- Gaming Squad (16) — ranked + arcade ---------------- */
  m("g1", "gaming", false, "Yesterday", { kind: "text", text: "Fahad: Ranked tonight? I'm warmed up 🔥" }),
  m("g2", "gaming", false, "Yesterday", { kind: "text", text: "Rashid: Give me 20 mins, eating" }),
  m("g3", "gaming", true, "Yesterday", { kind: "text", text: "Same, queue at 7:30?" }),
  m("g4", "gaming", false, "Yesterday", { kind: "text", text: "Fahad: 7:30 sharp. No Rashid time ⏰" }),
  m("g5", "gaming", false, "Yesterday", { kind: "text", text: "Rashid: Rude. But fair 😅" }),
  m("g6", "gaming", true, "Yesterday", { kind: "text", text: "GGs! That last round was insane" }),
  m("g7", "gaming", false, "Yesterday", { kind: "text", text: "Fahad: That clutch though 🔥🔥" }),
  m("g8", "gaming", false, "Yesterday", { kind: "text", text: "Rashid: I carried, admit it" }),
  m("g9", "gaming", true, "Yesterday", { kind: "text", text: "Sure you did 😌" }),
  m("g10", "gaming", false, "Yesterday", { kind: "image", url: img("photo-1511512578047-dfb367046420", 1200), caption: "Fahad: New arcade high score 🎮" }),
  m("g11", "gaming", false, "Yesterday", { kind: "text", text: "Rashid: 850k?! Okay that's actually impressive" }),
  m("g12", "gaming", true, "Yesterday", { kind: "text", text: "Rematch tomorrow? Same time" }),
  m("g13", "gaming", false, "Yesterday", { kind: "text", text: "Fahad: You're on" }),
  m("g14", "gaming", false, "11:30 AM", { kind: "text", text: "Rashid: Might be late tonight, family dinner 😢" }),
  m("g15", "gaming", true, "12:15 PM", { kind: "text", text: "No worries, raincheck?" }),
  m("g16", "gaming", false, "12:21 PM", { kind: "text", text: "Rashid: Let's play later tonight?" }),

  /* ---------------- Lina (12) — coffee plans ---------------- */
  m("l1", "lina", true, "Yesterday", { kind: "text", text: "Coffee this week? ☕" }),
  m("l2", "lina", false, "Yesterday", { kind: "text", text: "Yes please! I need a break from deadlines" }),
  m("l3", "lina", true, "Yesterday", { kind: "text", text: "Thursday after work? That place in JLT?" }),
  m("l4", "lina", false, "Yesterday", { kind: "text", text: "The one with the pistachio latte? 😍" }),
  m("l5", "lina", true, "Yesterday", { kind: "text", text: "That's the one" }),
  m("l6", "lina", false, "Yesterday", { kind: "text", text: "Perfect. 6pm?" }),
  m("l7", "lina", true, "Yesterday", { kind: "text", text: "6 works. See you there!" }),
  m("l8", "lina", false, "Yesterday", { kind: "text", text: "Running 10 mins late, sorry! 🙏" }),
  m("l9", "lina", true, "Yesterday", { kind: "text", text: "No rush, I just got here" }),
  m("l10", "lina", false, "Yesterday", { kind: "text", text: "That latte lived up to the hype ☕" }),
  m("l11", "lina", true, "Yesterday", { kind: "text", text: "Lunch tomorrow instead? Same place?" }),
  m("l12", "lina", false, "Yesterday", { kind: "text", text: "Okay, see you tomorrow!" }),

  /* ---------------- Omar (12) — Riyadh flights ---------------- */
  m("o1", "omar", true, "Yesterday", { kind: "text", text: "Booked our flights! ✈️" }),
  m("o2", "omar", false, "Yesterday", { kind: "text", text: "Already? That was fast 😄" }),
  m("o3", "omar", true, "Yesterday", { kind: "card", title: "DXB → RUH · SV 103", subtitle: "Fri, 24 Oct · 9:40 AM · Terminal 1", icon: "flight" }),
  m("o4", "omar", false, "Yesterday", { kind: "text", text: "Window seat for me, I called it 🪟" }),
  m("o5", "omar", true, "Yesterday", { kind: "text", text: "Haha fine, I'll take the aisle" }),
  m("o6", "omar", false, "Yesterday", { kind: "text", text: "Hotel next. Near the venue?" }),
  m("o7", "omar", true, "Yesterday", { kind: "text", text: "Looking now. Budget ~AED 400/night?" }),
  m("o8", "omar", false, "Yesterday", { kind: "text", text: "Sounds good. Split as usual?" }),
  m("o9", "omar", true, "Yesterday", { kind: "text", text: "Yep, 50/50" }),
  m("o10", "omar", false, "Yesterday", { kind: "text", text: "Passport check: valid till 2028 ✅" }),
  m("o11", "omar", true, "Yesterday", { kind: "text", text: "Mine too. We're all set 🛂" }),
  m("o12", "omar", false, "Yesterday", { kind: "text", text: "Thanks! 🙏" }),

  /* ---------------- Hana (12) — AI beach image ---------------- */
  m("h1", "hana", true, "Mon", { kind: "text", text: "Look what Messenger made for my post 👀" }),
  m("h2", "hana", true, "Mon", { kind: "image", url: img("photo-1519046904884-53103b34b206", 1200), caption: "Dubai beach at golden hour 🏖️" }),
  m("h3", "hana", false, "Mon", { kind: "text", text: "WAIT. That's AI?? 😱" }),
  m("h4", "hana", true, "Mon", { kind: "text", text: "Yep! Typed one sentence, got this" }),
  m("h5", "hana", false, "Mon", { kind: "text", text: "Okay I need this for my bakery page 🧁" }),
  m("h6", "hana", true, "Mon", { kind: "text", text: "Send me what you need, I'll generate a few" }),
  m("h7", "hana", false, "Mon", { kind: "text", text: "Croissants on marble, morning light 🤤" }),
  m("h8", "hana", true, "Mon", { kind: "text", text: "On it. Give me 2 mins" }),
  m("h9", "hana", true, "Mon", { kind: "text", text: "Sent! Check your email 📧" }),
  m("h10", "hana", false, "Mon", { kind: "text", text: "JUST SAW. These are perfect!!" }),
  m("h11", "hana", true, "Mon", { kind: "text", text: "Told you 😎 coffee on you next time" }),
  m("h12", "hana", false, "Mon", { kind: "text", text: "This is awesome!" }),

  /* ---------------- Sarah Malik, Omer Farooq, Lena Haddad (2 each) ---------------- */
  m("sm1", "sarah", true, "Sun", { kind: "text", text: "Can you share the deck from Thursday?" }),
  m("sm2", "sarah", false, "Sun", { kind: "text", text: "Sent you the slides 📎" }),
  m("of1", "omer", false, "Sun", { kind: "text", text: "Court is booked" }),
  m("of2", "omer", false, "Sun", { kind: "text", text: "Padel at 8?" }),
  m("lh1", "lena", true, "Sat", { kind: "text", text: "Landed! 🛬" }),
  m("lh2", "lena", false, "Sat", { kind: "text", text: "Welcome back to Dubai!" }),

  /* ---------------- Study Group (18) — exam prep ---------------- */
  m("d1", "study", false, "Sun", { kind: "text", text: "Adam: Exam in 10 days. Panic mode? 😅" }),
  m("d2", "study", false, "Sun", { kind: "text", text: "Reem: Only 10?? I thought we had two weeks" }),
  m("d3", "study", true, "Sun", { kind: "text", text: "It's on the 14th. We need a plan" }),
  m("d4", "study", false, "Sun", { kind: "text", text: "Adam: Library tomorrow? 10am?" }),
  m("d5", "study", false, "Sun", { kind: "text", text: "Reem: I'll bring the past papers 📄" }),
  m("d6", "study", true, "Sun", { kind: "text", text: "I'll bring coffee. Large ones ☕" }),
  m("d7", "study", false, "Sun", { kind: "text", text: "Adam: Chapters 4-6 first, they're the hardest" }),
  m("d8", "study", false, "Sun", { kind: "text", text: "Reem: Agreed. I made flashcards for ch.5" }),
  m("d9", "study", true, "Mon", { kind: "image", url: img("photo-1434030216411-0b793f4b4173", 1200), caption: "Chapter 5 notes are done 📝" }),
  m("d10", "study", false, "Mon", { kind: "text", text: "Adam: Send me those after 🙏" }),
  m("d11", "study", true, "Mon", { kind: "text", text: "Already shared in the drive" }),
  m("d12", "study", false, "Mon", { kind: "text", text: "Reem: You're a lifesaver ❤️" }),
  m("d13", "study", false, "Mon", { kind: "text", text: "Adam: Quiz each other at 8pm?" }),
  m("d14", "study", true, "Mon", { kind: "text", text: "I'm in. Loser buys coffee 😄" }),
  m("d15", "study", false, "Mon", { kind: "text", text: "Reem: Deal!" }),
  m("d16", "study", false, "Mon", { kind: "text", text: "Adam: Running late, start without me" }),
  m("d17", "study", false, "Mon", { kind: "text", text: "Reem: We'll do ch.6 first then" }),
  m("d18", "study", false, "Mon", { kind: "text", text: "Adam: New notes are up" }),
];

/* ---------------- emoji (the media panel's Emoji tab) ----------------
   Telegram's categories; each entry is "emoji search words". Shown with the system emoji font; an animated Noto
   version is used where public/emoji/animated has one. */
const EMOJI_SOURCE: Record<string, string> = {
  Smileys: "😀 grin happy|😃 smile happy|😄 laugh smile|😁 beam grin|😆 laugh squint|😅 sweat relief|🤣 rofl laugh|😂 joy tears laugh|🙂 slight smile|😉 wink|😊 blush smile|😇 angel innocent|🥰 love hearts|😍 heart eyes love|🤩 star struck wow|😘 kiss|😋 yum tasty|😛 tongue|😜 wink tongue crazy|🤪 zany crazy|🤗 hug|🤭 oops giggle|🤫 shush quiet|🤔 think hmm|😐 neutral|😑 expressionless|😏 smirk|😒 unamused|🙄 eye roll|😬 grimace awkward|😌 relieved calm|😔 pensive sad|😪 sleepy|😴 sleep tired|😷 mask sick|🤒 sick fever|🥵 hot heat|🥶 cold freezing|😵 dizzy|🤯 mind blown|🥳 party celebrate|😎 cool sunglasses|🤓 nerd|🧐 monocle curious|😕 confused|😟 worried|😮 wow surprised|😲 astonished shock|🥺 pleading puppy eyes|😢 cry sad|😭 sob crying|😱 scream fear|😤 triumph huff|😡 angry rage|🤬 swearing angry|😈 devil|💀 skull dead|🤡 clown|👻 ghost|🤖 robot|🙃 upside down|🫠 melting|😗 kissing|☺️ smiling|😚 kissing closed eyes eye|😙 kissing smiling eyes eye|🥲 smiling tear|😝 squinting tongue|🤑 money mouth|🫢 open eyes eye hand over mouth|🫣 peeking eye|🫡 saluting|🤐 zipper mouth|🤨 raised eyebrow|😶 without mouth|🫥 dotted line|😶‍🌫️ clouds cloud|😮‍💨 exhaling|🤥 lying|🫨 shaking|🙂‍↔️ head shaking horizontally|🙂‍↕️ head shaking vertically|🤤 drooling|🤕 head bandage|🤢 nauseated|🤮 vomiting|🤧 sneezing|🥴 woozy|😵‍💫 spiral eyes eye|🤠 cowboy hat|🥸 disguised|🫤 diagonal mouth|🙁 slightly frowning|☹️ frowning|😯 hushed|😳 flushed|🥹 holding back tears tear|😦 frowning open mouth|😧 anguished|😨 fearful|😰 anxious sweat|😥 sad but relieved|😖 confounded|😣 persevering|😞 disappointed|😓 downcast sweat|😩 weary|😫 tired|🥱 yawning|😠 angry|👿 angry horns horn|☠️ skull crossbones crossbone|💩 pile poo|👹 ogre|👺 goblin|👽 alien|👾 alien monster|😺 grinning cat|😸 grinning cat smiling eyes eye|😹 cat tears tear joy|😻 smiling cat heart eyes eye|😼 cat wry smile|😽 kissing cat|🙀 weary cat|😿 crying cat|😾 pouting cat|🙉 hear no evil monkey|🙊 speak no evil monkey|💌 love letter|💘 heart arrow|💝 heart ribbon|💖 sparkling heart|💗 growing heart|💓 beating heart|💞 revolving hearts heart|💟 heart decoration|❣️ heart exclamation|❤️‍🔥 heart fire|❤️‍🩹 mending heart|🩷 pink heart|🩵 light blue heart|🤎 brown heart|🩶 grey heart|💋 kiss mark|💢 anger|💦 sweat droplets droplet|💨 dashing away|🕳️ hole|👁️‍🗨️ eye speech bubble|🗨️ left speech bubble|🗯️ right anger bubble|💤 zzz",
  People: "👋 wave hello bye|🤚 raised hand|✋ hand stop|👌 ok perfect|🤌 pinched italian|✌️ peace victory|🤞 fingers crossed luck|🤟 love you|🤘 rock|👈 left point|👉 right point|👆 up point|👇 down point|👍 thumbs up yes like|👎 thumbs down no|✊ fist|👊 punch|👏 clap applause|🙌 raise hands hooray|🫶 heart hands|🤝 handshake deal|🙏 pray please thanks|💪 strong muscle|🧠 brain smart|👀 eyes look|👶 baby|🧒 child|👦 boy|👧 girl|🧑 person|👨 man|👩 woman|🧔 beard man|👵 grandma|👴 grandpa|👮 police|👷 builder|🧑‍💻 developer coder|🧑‍🍳 cook chef|🧑‍✈️ pilot|🤷 shrug|🙋 raise hand|🙆 ok gesture|🙅 no gesture|💁 tipping hand|🤦 facepalm|🧕 headscarf|👳 turban|🕺 dance man|💃 dance woman|🏃 run|🚶 walk|🖐️ hand fingers finger splayed|🖖 vulcan salute|🫱 rightwards rightward hand|🫲 leftwards leftward hand|🫳 palm down hand|🫴 palm up hand|🫷 leftwards leftward pushing hand|🫸 rightwards rightward pushing hand|🤏 pinching hand|🫰 hand index finger thumb crossed|🤙 call me hand|🖕 middle finger|☝️ index pointing up|🫵 index pointing at viewer|🤛 left facing fist|🤜 right facing fist|👐 open hands hand|🤲 palms palm up together|✍️ writing hand|💅 nail polish|🤳 selfie|🦾 mechanical arm|🦿 mechanical leg|🦵 leg|🦶 foot|👂 ear|🦻 ear hearing aid|👃 nose|🫀 anatomical heart|🫁 lungs lung|🦷 tooth|🦴 bone|👁️ eye|👅 tongue|👄 mouth|🫦 biting lip|👱 person blond hair|🧔‍♂️ man beard|🧔‍♀️ woman beard|👨‍🦰 man red hair|👨‍🦱 man curly hair|👨‍🦳 man white hair|👨‍🦲 man bald|👩‍🦰 woman red hair|🧑‍🦰 person red hair|👩‍🦱 woman curly hair|🧑‍🦱 person curly hair|👩‍🦳 woman white hair|🧑‍🦳 person white hair|👩‍🦲 woman bald|🧑‍🦲 person bald|👱‍♀️ woman blond hair|👱‍♂️ man blond hair|🧓 older person|🙍 person frowning|🙍‍♂️ man frowning|🙍‍♀️ woman frowning|🙎 person pouting|🙎‍♂️ man pouting|🙎‍♀️ woman pouting|🙅‍♂️ man gesturing no|🙅‍♀️ woman gesturing no|🙆‍♂️ man gesturing ok|🙆‍♀️ woman gesturing ok|💁‍♂️ man tipping hand|💁‍♀️ woman tipping hand|🙋‍♂️ man raising hand|🙋‍♀️ woman raising hand|🧏 deaf person|🧏‍♂️ deaf man|🧏‍♀️ deaf woman|🙇 person bowing|🙇‍♂️ man bowing|🙇‍♀️ woman bowing|🤦‍♂️ man facepalming|🤦‍♀️ woman facepalming|🤷‍♂️ man shrugging|🤷‍♀️ woman shrugging|🧑‍⚕️ health worker|👨‍⚕️ man health worker|👩‍⚕️ woman health worker|🧑‍🎓 student|👨‍🎓 man student|👩‍🎓 woman student|🧑‍🏫 teacher|👨‍🏫 man teacher|👩‍🏫 woman teacher|🧑‍⚖️ judge|👨‍⚖️ man judge|👩‍⚖️ woman judge|🧑‍🌾 farmer|👨‍🌾 man farmer|👩‍🌾 woman farmer|👨‍🍳 man cook|👩‍🍳 woman cook|🧑‍🔧 mechanic|👨‍🔧 man mechanic|👩‍🔧 woman mechanic|🧑‍🏭 factory worker|👨‍🏭 man factory worker|👩‍🏭 woman factory worker|🧑‍💼 office worker|👨‍💼 man office worker|👩‍💼 woman office worker|🧑‍🔬 scientist|👨‍🔬 man scientist|👩‍🔬 woman scientist|👨‍💻 man technologist|👩‍💻 woman technologist|🧑‍🎤 singer|👨‍🎤 man singer|👩‍🎤 woman singer|🧑‍🎨 artist|👨‍🎨 man artist|👩‍🎨 woman artist|👨‍✈️ man pilot|👩‍✈️ woman pilot|🧑‍🚀 astronaut|👨‍🚀 man astronaut|👩‍🚀 woman astronaut|🧑‍🚒 firefighter|👨‍🚒 man firefighter|👩‍🚒 woman firefighter|👮‍♂️ man police officer|👮‍♀️ woman police officer|🕵️ detective|🕵️‍♂️ man detective|🕵️‍♀️ woman detective|💂 guard|💂‍♂️ man guard|💂‍♀️ woman guard|🥷 ninja|👷‍♂️ man construction worker|👷‍♀️ woman construction worker|🫅 person crown|🤴 prince|👸 princess|👳‍♂️ man wearing turban|👳‍♀️ woman wearing turban|👲 person skullcap|🤵 person tuxedo|🤵‍♂️ man tuxedo|🤵‍♀️ woman tuxedo|👰 person veil|👰‍♂️ man veil|👰‍♀️ woman veil|🤰 pregnant woman|🫃 pregnant man|🫄 pregnant person|🤱 breast feeding|👩‍🍼 woman feeding baby|👨‍🍼 man feeding baby|🧑‍🍼 person feeding baby|👼 baby angel|🎅 santa claus|🤶 mrs claus|🧑‍🎄 mx claus|🦸 superhero|🦸‍♂️ man superhero|🦸‍♀️ woman superhero|🦹 supervillain|🦹‍♂️ man supervillain|🦹‍♀️ woman supervillain|🧙 mage|🧙‍♂️ man mage|🧙‍♀️ woman mage|🧚 fairy|🧚‍♂️ man fairy|🧚‍♀️ woman fairy|🧛 vampire|🧛‍♂️ man vampire|🧛‍♀️ woman vampire|🧜 merperson|🧜‍♂️ merman|🧜‍♀️ mermaid|🧝 elf|🧝‍♂️ man elf|🧝‍♀️ woman elf|🧞 genie|🧞‍♂️ man genie|🧞‍♀️ woman genie|🧟 zombie|🧟‍♂️ man zombie|🧟‍♀️ woman zombie|🧌 troll|💆 person getting massage|💆‍♂️ man getting massage|💆‍♀️ woman getting massage|💇 person getting haircut|💇‍♂️ man getting haircut|💇‍♀️ woman getting haircut|🚶‍♂️ man walking|🚶‍♀️ woman walking|🚶‍➡️ person walking facing right|🚶‍♀️‍➡️ woman walking facing right|🚶‍♂️‍➡️ man walking facing right|🧍 person standing|🧍‍♂️ man standing|🧍‍♀️ woman standing|🧎 person kneeling|🧎‍♂️ man kneeling|🧎‍♀️ woman kneeling|🧎‍➡️ person kneeling facing right|🧎‍♀️‍➡️ woman kneeling facing right|🧎‍♂️‍➡️ man kneeling facing right|🧑‍🦯 person white cane|🧑‍🦯‍➡️ person white cane facing right|👨‍🦯 man white cane|👨‍🦯‍➡️ man white cane facing right|👩‍🦯 woman white cane|👩‍🦯‍➡️ woman white cane facing right|🧑‍🦼 person motorized wheelchair|🧑‍🦼‍➡️ person motorized wheelchair facing right|👨‍🦼 man motorized wheelchair|👨‍🦼‍➡️ man motorized wheelchair facing right|👩‍🦼 woman motorized wheelchair|👩‍🦼‍➡️ woman motorized wheelchair facing right|🧑‍🦽 person manual wheelchair|🧑‍🦽‍➡️ person manual wheelchair facing right|👨‍🦽 man manual wheelchair|👨‍🦽‍➡️ man manual wheelchair facing right|👩‍🦽 woman manual wheelchair|👩‍🦽‍➡️ woman manual wheelchair facing right|🏃‍♂️ man running|🏃‍♀️ woman running|🏃‍➡️ person running facing right|🏃‍♀️‍➡️ woman running facing right|🏃‍♂️‍➡️ man running facing right|🕴️ person suit levitating|👯 people bunny ears ear|👯‍♂️ men bunny ears ear|👯‍♀️ women bunny ears ear|🧖 person steamy room|🧖‍♂️ man steamy room|🧖‍♀️ woman steamy room|🧗 person climbing|🧗‍♂️ man climbing|🧗‍♀️ woman climbing|🤺 person fencing|🏇 horse racing|⛷️ skier|🏂 snowboarder|🏌️ person golfing|🏌️‍♂️ man golfing|🏌️‍♀️ woman golfing|🏄‍♂️ man surfing|🏄‍♀️ woman surfing|🚣 person rowing boat|🚣‍♂️ man rowing boat|🚣‍♀️ woman rowing boat|🏊‍♂️ man swimming|🏊‍♀️ woman swimming|⛹️ person bouncing ball|⛹️‍♂️ man bouncing ball|⛹️‍♀️ woman bouncing ball|🏋️‍♂️ man lifting weights weight|🏋️‍♀️ woman lifting weights weight|🚴‍♂️ man biking|🚴‍♀️ woman biking|🚵 person mountain biking|🚵‍♂️ man mountain biking|🚵‍♀️ woman mountain biking|🤸 person cartwheeling|🤸‍♂️ man cartwheeling|🤸‍♀️ woman cartwheeling|🤼 people wrestling|🤼‍♂️ men wrestling|🤼‍♀️ women wrestling|🤽 person playing water polo|🤽‍♂️ man playing water polo|🤽‍♀️ woman playing water polo|🤾 person playing handball|🤾‍♂️ man playing handball|🤾‍♀️ woman playing handball|🤹 person juggling|🤹‍♂️ man juggling|🤹‍♀️ woman juggling|🧘‍♂️ man lotus position|🧘‍♀️ woman lotus position|🛀 person taking bath|🛌 person bed|🧑‍🤝‍🧑 people holding hands hand|👭 women holding hands hand|👫 woman man holding hands hand|👬 men holding hands hand|💏 kiss|👩‍❤️‍💋‍👨 kiss woman man|👨‍❤️‍💋‍👨 kiss man|👩‍❤️‍💋‍👩 kiss woman|💑 couple heart|👩‍❤️‍👨 couple heart woman man|👨‍❤️‍👨 couple heart man|👩‍❤️‍👩 couple heart woman|👨‍👩‍👦 family man woman boy|👨‍👩‍👧 family man woman girl|👨‍👩‍👧‍👦 family man woman girl boy|👨‍👩‍👦‍👦 family man woman boy|👨‍👩‍👧‍👧 family man woman girl|👨‍👨‍👦 family man boy|👨‍👨‍👧 family man girl|👨‍👨‍👧‍👦 family man girl boy|👨‍👨‍👦‍👦 family man boy|👨‍👨‍👧‍👧 family man girl|👩‍👩‍👦 family woman boy|👩‍👩‍👧 family woman girl|👩‍👩‍👧‍👦 family woman girl boy|👩‍👩‍👦‍👦 family woman boy|👩‍👩‍👧‍👧 family woman girl|👨‍👦 family man boy|👨‍👦‍👦 family man boy|👨‍👧 family man girl|👨‍👧‍👦 family man girl boy|👨‍👧‍👧 family man girl|👩‍👦 family woman boy|👩‍👦‍👦 family woman boy|👩‍👧 family woman girl|👩‍👧‍👦 family woman girl boy|👩‍👧‍👧 family woman girl|🗣️ speaking head|👤 bust silhouette|👥 busts bust silhouette|🫂 people hugging|👪 family|🧑‍🧑‍🧒 family adult child|🧑‍🧑‍🧒‍🧒 family adult child|🧑‍🧒 family adult child|🧑‍🧒‍🧒 family adult child|👣 footprints footprint",
  Animals: "🐶 dog puppy|🐱 cat kitten|🐭 mouse|🐹 hamster|🐰 rabbit bunny|🦊 fox|🐻 bear|🐼 panda|🐨 koala|🐯 tiger|🦁 lion|🐮 cow|🐷 pig|🐸 frog|🐵 monkey|🙈 see no evil|🐔 chicken|🐧 penguin|🐦 bird|🦅 eagle|🦉 owl|🦄 unicorn|🐝 bee|🦋 butterfly|🐢 turtle|🐍 snake|🦎 lizard|🐙 octopus|🐬 dolphin|🐳 whale|🦈 shark|🐪 camel|🐫 camels|🦒 giraffe|🐘 elephant|🐎 horse|🦜 parrot|🌵 cactus desert|🌴 palm tree|🌳 tree|🌸 blossom flower|🌹 rose|🌻 sunflower|🍀 clover luck|🐒 monkey|🦍 gorilla|🦧 orangutan|🐕 dog|🦮 guide dog|🐕‍🦺 service dog|🐩 poodle|🐺 wolf|🦝 raccoon|🐈 cat|🐈‍⬛ black cat|🐅 tiger|🐆 leopard|🐴 horse|🫎 moose|🫏 donkey|🦓 zebra|🦌 deer|🦬 bison|🐂 ox|🐃 water buffalo|🐄 cow|🐖 pig|🐗 boar|🐽 pig nose|🐏 ram|🐑 ewe|🐐 goat|🦙 llama|🦣 mammoth|🦏 rhinoceros|🦛 hippopotamus|🐁 mouse|🐀 rat|🐇 rabbit|🐿️ chipmunk|🦫 beaver|🦔 hedgehog|🦇 bat|🐻‍❄️ polar bear|🦥 sloth|🦦 otter|🦨 skunk|🦘 kangaroo|🦡 badger|🐾 paw prints print|🦃 turkey|🐓 rooster|🐣 hatching chick|🐤 baby chick|🐥 front facing baby chick|🕊️ dove|🦆 duck|🦢 swan|🦤 dodo|🪶 feather|🦩 flamingo|🦚 peacock|🪽 wing|🐦‍⬛ black bird|🪿 goose|🐦‍🔥 phoenix|🐊 crocodile|🐲 dragon|🐉 dragon|🦕 sauropod|🦖 rex|🐋 whale|🦭 seal|🐟 fish|🐠 tropical fish|🐡 blowfish|🐚 spiral shell|🪸 coral|🪼 jellyfish|🐌 snail|🐛 bug|🐜 ant|🪲 beetle|🐞 lady beetle|🦗 cricket|🪳 cockroach|🕷️ spider|🕸️ spider web|🦂 scorpion|🦟 mosquito|🪰 fly|🪱 worm|🦠 microbe|💐 bouquet|💮 white flower|🪷 lotus|🏵️ rosette|🥀 wilted flower|🌺 hibiscus|🌼 blossom|🌷 tulip|🪻 hyacinth|🌱 seedling|🪴 potted plant|🌲 evergreen tree|🌾 sheaf rice|🌿 herb|☘️ shamrock|🍁 maple leaf|🍂 fallen leaf|🍃 leaf fluttering wind|🪹 empty nest|🪺 nest eggs egg|🍄 mushroom",
  Food: "🍏 apple green|🍎 apple red|🍊 orange|🍋 lemon|🍌 banana|🍉 watermelon|🍇 grapes|🍓 strawberry|🍒 cherries|🍑 peach|🥭 mango|🍍 pineapple|🥥 coconut|🥑 avocado|🍅 tomato|🌽 corn|🥕 carrot|🥐 croissant|🍞 bread|🧀 cheese|🍳 egg breakfast|🥞 pancakes|🍔 burger|🍟 fries|🍕 pizza|🌭 hotdog|🥙 shawarma wrap|🌮 taco|🍝 pasta|🍜 noodles ramen|🍣 sushi|🍚 rice|🍛 curry|🍦 ice cream|🍩 donut|🍪 cookie|🎂 cake birthday|🍫 chocolate|🍿 popcorn|☕ coffee|🍵 tea|🧃 juice|🥤 drink soda|🫖 teapot karak|🍈 melon|🍋‍🟩 lime|🍐 pear|🫐 blueberries blueberry|🥝 kiwi fruit|🫒 olive|🍆 eggplant|🥔 potato|🌶️ hot pepper|🫑 bell pepper|🥒 cucumber|🥬 leafy green|🥦 broccoli|🧄 garlic|🧅 onion|🥜 peanuts peanut|🫘 beans bean|🌰 chestnut|🫚 ginger root|🫛 pea pod|🍄‍🟫 brown mushroom|🥖 baguette bread|🫓 flatbread|🥨 pretzel|🥯 bagel|🧇 waffle|🍖 meat bone|🍗 poultry leg|🥩 cut meat|🥓 bacon|🥪 sandwich|🌯 burrito|🫔 tamale|🧆 falafel|🥚 egg|🥘 shallow pan food|🍲 pot food|🫕 fondue|🥣 bowl spoon|🥗 green salad|🧈 butter|🧂 salt|🥫 canned food|🍱 bento box|🍘 rice cracker|🍙 rice ball|🍠 roasted sweet potato|🍢 oden|🍤 fried shrimp|🍥 fish cake swirl|🥮 moon cake|🍡 dango|🥟 dumpling|🥠 fortune cookie|🥡 takeout box|🦀 crab|🦞 lobster|🦐 shrimp|🦑 squid|🦪 oyster|🍧 shaved ice|🍨 ice cream|🍰 shortcake|🧁 cupcake|🥧 pie|🍬 candy|🍭 lollipop|🍮 custard|🍯 honey pot|🍼 baby bottle|🥛 glass milk|🍶 sake|🍾 bottle popping cork|🍷 wine glass|🍸 cocktail glass|🍹 tropical drink|🍺 beer mug|🍻 clinking beer mugs mug|🥂 clinking glasses glass|🥃 tumbler glass|🫗 pouring liquid|🧋 bubble tea|🧉 mate|🧊 ice|🥢 chopsticks chopstick|🍽️ fork knife plate|🍴 fork knife|🥄 spoon|🔪 kitchen knife|🫙 jar|🏺 amphora",
  Travel: "🚗 car|🚕 taxi|🚌 bus|🚑 ambulance|🚓 police car|🏎️ race car|🛵 scooter|🚲 bike bicycle|🚂 train|✈️ plane flight|🛫 departure|🛬 arrival|🚀 rocket|🛳️ ship cruise|⛵ sailboat|🗺️ map|🧭 compass|🏖️ beach|🏝️ island|🏜️ desert|🏔️ mountain|🏕️ camping|🏙️ city skyline|🕌 mosque|🕋 kaaba|🏰 castle|🗽 statue liberty|🗼 tower|🌅 sunrise|🌄 sunrise mountain|🌇 sunset city|🌃 night city|🌙 moon|⭐ star|☀️ sun sunny|⛅ cloud sun|🌧️ rain|⛈️ storm|❄️ snow cold|🔥 fire hot|🌊 wave sea|🌈 rainbow|🌍 globe showing europe africa|🌎 globe showing americas america|🌏 globe showing asia australia|🌐 globe meridians meridian|🗾 map japan|⛰️ mountain|🌋 volcano|🗻 mount fuji|🏞️ national park|🏟️ stadium|🏛️ classical building|🏗️ building construction|🧱 brick|🪨 rock|🪵 wood|🛖 hut|🏘️ houses house|🏚️ derelict house|🏠 house|🏡 house garden|🏢 office building|🏣 japanese post office|🏤 post office|🏥 hospital|🏦 bank|🏨 hotel|🏩 love hotel|🏪 convenience store|🏫 school|🏬 department store|🏭 factory|🏯 japanese castle|💒 wedding|⛪ church|🛕 hindu temple|🕍 synagogue|⛩️ shinto shrine|⛲ fountain|⛺ tent|🌁 foggy|🌆 cityscape at dusk|🌉 bridge at night|♨️ hot springs spring|🎠 carousel horse|🛝 playground slide|🎡 ferris wheel|🎢 roller coaster|💈 barber pole|🎪 circus tent|🚃 railway car|🚄 high speed train|🚅 bullet train|🚆 train|🚇 metro|🚈 light rail|🚉 station|🚊 tram|🚝 monorail|🚞 mountain railway|🚋 tram car|🚍 oncoming bus|🚎 trolleybus|🚐 minibus|🚒 fire engine|🚔 oncoming police car|🚖 oncoming taxi|🚘 oncoming automobile|🚙 sport utility vehicle|🛻 pickup truck|🚚 delivery truck|🚛 articulated lorry|🚜 tractor|🏍️ motorcycle|🦽 manual wheelchair|🦼 motorized wheelchair|🛺 auto rickshaw|🛴 kick scooter|🛹 skateboard|🛼 roller skate|🚏 bus stop|🛣️ motorway|🛤️ railway track|🛢️ oil drum|⛽ fuel pump|🛞 wheel|🚨 police car light|🚥 horizontal traffic light|🚦 vertical traffic light|🛑 stop|🚧 construction|⚓ anchor|🛟 ring buoy|🛶 canoe|🚤 speedboat|⛴️ ferry|🛥️ motor boat|🚢 ship|🛩️ small airplane|🪂 parachute|💺 seat|🚁 helicopter|🚟 suspension railway|🚠 mountain cableway|🚡 aerial tramway|🛰️ satellite|🛸 flying saucer|🛎️ bellhop bell|⌛ hourglass done|⏱️ stopwatch|⏲️ timer clock|🕰️ mantelpiece clock|🕛 clock|🕧 thirty|🕐 clock|🕜 thirty|🕑 clock|🕝 thirty|🕒 clock|🕞 thirty|🕓 clock|🕟 thirty|🕔 clock|🕠 thirty|🕕 clock|🕡 thirty|🕖 clock|🕢 thirty|🕗 clock|🕣 thirty|🕘 clock|🕤 thirty|🕙 clock|🕥 thirty|🕚 clock|🕦 thirty|🌑 new moon|🌒 waxing crescent moon|🌓 first quarter moon|🌔 waxing gibbous moon|🌕 full moon|🌖 waning gibbous moon|🌗 last quarter moon|🌘 waning crescent moon|🌚 new moon|🌛 first quarter moon|🌜 last quarter moon|🌡️ thermometer|🌝 full moon|🌞 sun|🪐 ringed planet|🌟 glowing star|🌠 shooting star|🌌 milky way|☁️ cloud|🌤️ sun behind small cloud|🌥️ sun behind large cloud|🌦️ sun behind rain cloud|🌨️ cloud snow|🌩️ cloud lightning|🌪️ tornado|🌫️ fog|🌬️ wind|🌀 cyclone|🌂 closed umbrella|☂️ umbrella|☔ umbrella rain drops drop|⛱️ umbrella ground|⚡ high voltage|☃️ snowman|⛄ snowman without snow|☄️ comet|💧 droplet",
  Activities: "⚽ football soccer|🏀 basketball|🏈 american football|⚾ baseball|🎾 tennis|🏐 volleyball|🏓 ping pong|🏸 badminton|🥊 boxing|🥋 martial arts|⛳ golf|🏊 swim|🏄 surf|🚴 cycling|🏋️ gym weights|🧘 yoga|🏆 trophy win|🥇 gold medal first|🎯 target goal|🎮 game controller gaming|🕹️ joystick|🎲 dice|♟️ chess|🎨 art paint|🎬 movie film|🎤 mic sing karaoke|🎧 headphones music|🎸 guitar|🎹 piano|🥁 drums|🎉 party tada celebrate|🎊 confetti|🎁 gift present|🎈 balloon|🎃 jack lantern|🎄 christmas christma tree|🎆 fireworks firework|🎇 sparkler|🧨 firecracker|🎋 tanabata tree|🎍 pine decoration|🎎 japanese dolls doll|🎏 carp streamer|🎐 wind chime|🎑 moon viewing ceremony|🧧 red envelope|🎀 ribbon|🎗️ reminder ribbon|🎟️ admission tickets ticket|🎫 ticket|🎖️ military medal|🏅 sports sport medal|🥈 2nd place medal|🥉 3rd place medal|🥎 softball|🏉 rugby football|🥏 flying disc|🎳 bowling|🏏 cricket game|🏑 field hockey|🏒 ice hockey|🥍 lacrosse|🥅 goal net|⛸️ ice skate|🎣 fishing pole|🤿 diving mask|🎽 running shirt|🎿 skis|🛷 sled|🥌 curling stone|🪀 yo|🪁 kite|🔫 water pistol|🎱 pool ball|🔮 crystal ball|🪄 magic wand|🎰 slot machine|🧩 puzzle piece|🧸 teddy bear|🪅 pi ata|🪩 mirror ball|🪆 nesting dolls doll|♠️ spade suit|♥️ heart suit|♦️ diamond suit|♣️ club suit|🃏 joker|🀄 mahjong red dragon|🎴 flower playing cards card|🎭 performing arts art|🖼️ framed picture|🧵 thread|🪡 sewing needle|🧶 yarn|🪢 knot",
  Objects: "⌚ watch|📱 phone mobile|💻 laptop|⌨️ keyboard|🖥️ computer|🖨️ printer|📷 camera|🎥 video camera|📺 tv|🔋 battery|🔌 plug|💡 idea bulb|🔦 flashlight|🕯️ candle|💸 money flying|💵 cash dollar|💳 card payment|💎 diamond|⚖️ balance|🔧 wrench|🔨 hammer|🛠️ tools|🔑 key|🔒 lock|🚪 door|🛏️ bed|🛋️ couch|🧳 luggage suitcase|📦 package box|📅 calendar date|📌 pin|📎 paperclip|✂️ scissors|📝 memo note|📚 books|📖 book read|✉️ envelope mail|📧 email|📣 megaphone|🔔 bell notification|⏰ alarm|⏳ hourglass|👓 glasses glass|🕶️ sunglasses sunglass|🥽 goggles goggle|🥼 lab coat|🦺 safety vest|👔 necktie|👕 shirt|👖 jeans jean|🧣 scarf|🧤 gloves glove|🧥 coat|🧦 socks sock|👗 dress|👘 kimono|🥻 sari|🩱 piece swimsuit|🩲 briefs brief|🩳 shorts short|👙 bikini|👚 woman clothes clothe|🪭 folding hand fan|👛 purse|👜 handbag|👝 clutch bag|🛍️ shopping bags bag|🎒 backpack|🩴 thong sandal|👞 man shoe|👟 running shoe|🥾 hiking boot|🥿 flat shoe|👠 high heeled shoe|👡 woman sandal|🩰 ballet shoes shoe|👢 woman boot|🪮 hair pick|👑 crown|👒 woman hat|🎩 top hat|🎓 graduation cap|🧢 billed cap|🪖 military helmet|⛑️ rescue worker helmet|📿 prayer beads bead|💄 lipstick|💍 ring|🔇 muted speaker|🔈 speaker low volume|🔉 speaker medium volume|🔊 speaker high volume|📢 loudspeaker|📯 postal horn|🔕 bell slash|🎼 musical score|🎵 musical note|🎶 musical notes note|🎙️ studio microphone|🎚️ level slider|🎛️ control knobs knob|📻 radio|🎷 saxophone|🪗 accordion|🎺 trumpet|🎻 violin|🪕 banjo|🪘 long drum|🪇 maracas maraca|🪈 flute|📲 mobile phone arrow|☎️ telephone|📞 telephone receiver|📟 pager|📠 fax machine|🪫 low battery|🖱️ computer mouse|🖲️ trackball|💽 computer disk|💾 floppy disk|💿 optical disk|📀 dvd|🧮 abacus|🎞️ film frames frame|📽️ film projector|📸 camera flash|📹 video camera|📼 videocassette|🔍 magnifying glass tilted left|🔎 magnifying glass tilted right|🏮 red paper lantern|🪔 diya lamp|📔 notebook decorative cover|📕 closed book|📗 green book|📘 blue book|📙 orange book|📓 notebook|📒 ledger|📃 page curl|📜 scroll|📄 page facing up|📰 newspaper|🗞️ rolled up newspaper|📑 bookmark tabs tab|🔖 bookmark|🏷️ label|💰 money bag|🪙 coin|💴 yen banknote|💶 euro banknote|💷 pound banknote|🧾 receipt|💹 chart increasing yen|📨 incoming envelope|📩 envelope arrow|📤 outbox tray|📥 inbox tray|📫 closed mailbox raised|📪 closed mailbox lowered|📬 open mailbox raised|📭 open mailbox lowered|📮 postbox|🗳️ ballot box|✏️ pencil|✒️ black nib|🖋️ fountain pen|🖊️ pen|🖌️ paintbrush|🖍️ crayon|💼 briefcase|📁 file folder|📂 open file folder|🗂️ card index dividers divider|📆 tear off calendar|🗒️ spiral notepad|🗓️ spiral calendar|📇 card index|📈 chart increasing|📉 chart decreasing|📊 bar chart|📋 clipboard|📍 round pushpin|🖇️ linked paperclips paperclip|📏 straight ruler|📐 triangular ruler|🗃️ card file box|🗄️ file cabinet|🗑️ wastebasket|🔓 unlocked|🔏 locked pen|🔐 locked key|🗝️ old key|🪓 axe|⛏️ pick|⚒️ hammer pick|🗡️ dagger|⚔️ crossed swords sword|💣 bomb|🪃 boomerang|🏹 bow arrow|🛡️ shield|🪚 carpentry saw|🪛 screwdriver|🔩 nut bolt|⚙️ gear|🗜️ clamp|🦯 white cane|🔗 link|⛓️‍💥 broken chain|⛓️ chains chain|🪝 hook|🧰 toolbox|🧲 magnet|🪜 ladder|⚗️ alembic|🧪 test tube|🧫 petri dish|🧬 dna|🔬 microscope|🔭 telescope|📡 satellite antenna|💉 syringe|🩸 drop blood|💊 pill|🩹 adhesive bandage|🩼 crutch|🩺 stethoscope|🩻 ray|🛗 elevator|🪞 mirror|🪟 window|🪑 chair|🚽 toilet|🪠 plunger|🚿 shower|🛁 bathtub|🪤 mouse trap|🪒 razor|🧴 lotion bottle|🧷 safety pin|🧹 broom|🧺 basket|🧻 roll paper|🪣 bucket|🧼 soap|🫧 bubbles bubble|🪥 toothbrush|🧽 sponge|🧯 fire extinguisher|🛒 shopping cart|🚬 cigarette|⚰️ coffin|🪦 headstone|⚱️ funeral urn|🧿 nazar amulet|🪬 hamsa|🗿 moai|🪧 placard|🪪 identification card",
  Symbols: "❤️ red heart love|🧡 orange heart|💛 yellow heart|💚 green heart|💙 blue heart|💜 purple heart|🖤 black heart|🤍 white heart|💔 broken heart|💕 two hearts|💯 hundred|✅ check yes done|☑️ check box|✔️ check|❌ cross no|⭕ circle|❗ exclamation|❓ question|‼️ double exclamation|⚠️ warning|🚫 prohibited|♻️ recycle|✨ sparkles|💫 dizzy star|💥 boom|💬 speech bubble|💭 thought|🔴 red circle|🟢 green circle|🔵 blue circle|⬆️ up arrow|⬇️ down arrow|➡️ right arrow|⬅️ left arrow|🔄 refresh|➕ plus|➖ minus|🆗 ok|🆕 new|🔝 top|🏧 atm|🚮 litter bin|🚰 potable water|♿ wheelchair|🚹 men room|🚺 women room|🚻 restroom|🚼 baby|🚾 water closet|🛂 passport control|🛃 customs custom|🛄 baggage claim|🛅 left luggage|🚸 children crossing|⛔ no entry|🚳 no bicycles bicycle|🚭 no smoking|🚯 no littering|🚱 non potable water|🚷 no pedestrians pedestrian|📵 no mobile phones phone|🔞 no under eighteen|☢️ radioactive|☣️ biohazard|↗️ up right arrow|↘️ down right arrow|↙️ down left arrow|↖️ up left arrow|↕️ up down arrow|↔️ left right arrow|↩️ right arrow curving left|↪️ left arrow curving right|⤴️ right arrow curving up|⤵️ right arrow curving down|🔃 clockwise vertical arrows arrow|🔙 back arrow|🔚 end arrow|🔛 arrow|🔜 soon arrow|🛐 place worship|⚛️ atom|🕉️ om|✡️ star david|☸️ wheel dharma|☯️ yin yang|✝️ latin cross|☦️ orthodox cross|☪️ star crescent|☮️ peace|🕎 menorah|🔯 dotted pointed star|🪯 khanda|♈ aries ary|♉ taurus|♊ gemini|♋ cancer|♌ leo|♍ virgo|♎ libra|♏ scorpio|♐ sagittarius|♑ capricorn|♒ aquarius|♓ pisces pisce|⛎ ophiuchus|🔀 shuffle tracks track button|🔁 repeat button|🔂 repeat single button|▶️ play button|⏩ fast forward button|⏭️ next track button|⏯️ play pause button|◀️ reverse button|⏪ fast reverse button|⏮️ last track button|🔼 upwards upward button|⏫ fast up button|🔽 downwards downward button|⏬ fast down button|⏸️ pause button|⏹️ stop button|⏺️ record button|⏏️ eject button|🎦 cinema|🔅 dim button|🔆 bright button|📶 antenna bars bar|🛜 wireless|📳 vibration mode|📴 mobile phone off|♀️ female|♂️ male|⚧️ transgender|✖️ multiply|➗ divide|🟰 heavy equals equal|♾️ infinity|⁉️ exclamation question mark|❔ white question mark|❕ white exclamation mark|〰️ wavy dash|💱 currency exchange|💲 heavy dollar|⚕️ medical|⚜️ fleur de lis|🔱 trident emblem|📛 name badge|🔰 japanese beginner|❎ cross mark button|➰ curly loop|➿ double curly loop|〽️ part alternation mark|✳️ spoked asterisk|✴️ pointed star|❇️ sparkle|©️ copyright|®️ registered|™️ trade mark|#️⃣ keycap hash|*️⃣ keycap asterisk|0️⃣ keycap|1️⃣ keycap|2️⃣ keycap|3️⃣ keycap|4️⃣ keycap|5️⃣ keycap|6️⃣ keycap|7️⃣ keycap|8️⃣ keycap|9️⃣ keycap|🔟 10|🔠 input latin uppercase|🔡 input latin lowercase|🔢 input numbers number|🔣 input symbols symbol|🔤 input latin letters letter|🅰️ button blood type|🆎 ab button blood type|🅱️ button blood type|🆑 cl button|🆒 cool button|🆓 free button|ℹ️ information|🆔 id button|Ⓜ️ circled|🆖 ng button|🅾️ button blood type|🅿️ button|🆘 sos button|🆙 up button|🆚 vs button|🈁 japanese here button|🈂️ japanese service charge button|🈷️ japanese monthly amount button|🈶 japanese not free charge button|🈯 japanese reserved button|🉐 japanese bargain button|🈹 japanese discount button|🈚 japanese free charge button|🈲 japanese prohibited button|🉑 japanese acceptable button|🈸 japanese application button|🈴 japanese passing grade button|🈳 japanese vacancy button|㊗️ japanese congratulations congratulation button|㊙️ japanese secret button|🈺 japanese open business button|🈵 japanese no vacancy button|🟠 orange circle|🟡 yellow circle|🟣 purple circle|🟤 brown circle|⚫ black circle|⚪ white circle|🟥 red square|🟧 orange square|🟨 yellow square|🟩 green square|🟦 blue square|🟪 purple square|🟫 brown square|⬛ black large square|⬜ white large square|◼️ black medium square|◻️ white medium square|◾ black medium small square|◽ white medium small square|▪️ black small square|▫️ white small square|🔶 large orange diamond|🔷 large blue diamond|🔸 small orange diamond|🔹 small blue diamond|🔺 red triangle pointed up|🔻 red triangle pointed down|💠 diamond dot|🔘 radio button|🔳 white square button|🔲 black square button",
  Flags: "🇦🇪 uae emirates|🇸🇦 saudi arabia|🇪🇬 egypt|🇯🇴 jordan|🇰🇼 kuwait|🇶🇦 qatar|🇧🇭 bahrain|🇴🇲 oman|🇱🇧 lebanon|🇲🇦 morocco|🇹🇷 turkey|🇬🇧 uk britain|🇺🇸 usa america|🇫🇷 france|🇩🇪 germany|🇮🇹 italy|🇪🇸 spain|🇯🇵 japan|🇮🇳 india|🇵🇰 pakistan|🇮🇩 indonesia bali|🇬🇪 georgia|🏁 checkered race|🏳️ white flag|🏴 black flag|🚩 triangular|🎌 crossed flags flag|🏳️‍🌈 rainbow|🏳️‍⚧️ transgender|🏴‍☠️ pirate|🇦🇨 ascension island|🇦🇩 andorra|🇦🇫 afghanistan|🇦🇬 antigua barbuda|🇦🇮 anguilla|🇦🇱 albania|🇦🇲 armenia|🇦🇴 angola|🇦🇶 antarctica|🇦🇷 argentina|🇦🇸 american samoa|🇦🇹 austria|🇦🇺 australia|🇦🇼 aruba|🇦🇽 land islands island|🇦🇿 azerbaijan|🇧🇦 bosnia herzegovina|🇧🇧 barbados|🇧🇩 bangladesh|🇧🇪 belgium|🇧🇫 burkina faso|🇧🇬 bulgaria|🇧🇮 burundi|🇧🇯 benin|🇧🇱 st barth lemy|🇧🇲 bermuda|🇧🇳 brunei|🇧🇴 bolivia|🇧🇶 caribbean netherlands netherland|🇧🇷 brazil|🇧🇸 bahamas bahama|🇧🇹 bhutan|🇧🇻 bouvet island|🇧🇼 botswana|🇧🇾 belarus|🇧🇿 belize|🇨🇦 canada|🇨🇨 cocos keeling islands island|🇨🇩 congo kinshasa|🇨🇫 central african republic|🇨🇬 congo brazzaville|🇨🇭 switzerland|🇨🇮 te ivoire|🇨🇰 cook islands island|🇨🇱 chile|🇨🇲 cameroon|🇨🇳 china|🇨🇴 colombia|🇨🇵 clipperton island|🇨🇷 costa rica|🇨🇺 cuba|🇨🇻 cape verde|🇨🇼 cura ao|🇨🇽 christmas christma island|🇨🇾 cyprus|🇨🇿 czechia|🇩🇬 diego garcia|🇩🇯 djibouti|🇩🇰 denmark|🇩🇲 dominica|🇩🇴 dominican republic|🇩🇿 algeria|🇪🇦 ceuta melilla|🇪🇨 ecuador|🇪🇪 estonia|🇪🇭 western sahara|🇪🇷 eritrea|🇪🇹 ethiopia|🇪🇺 european union|🇫🇮 finland|🇫🇯 fiji|🇫🇰 falkland islands island|🇫🇲 micronesia|🇫🇴 faroe islands island|🇬🇦 gabon|🇬🇩 grenada|🇬🇫 french guiana|🇬🇬 guernsey|🇬🇭 ghana|🇬🇮 gibraltar|🇬🇱 greenland|🇬🇲 gambia|🇬🇳 guinea|🇬🇵 guadeloupe|🇬🇶 equatorial guinea|🇬🇷 greece|🇬🇸 south georgia sandwich islands island|🇬🇹 guatemala|🇬🇺 guam|🇬🇼 guinea bissau|🇬🇾 guyana|🇭🇰 hong kong sar china|🇭🇲 heard mcdonald islands island|🇭🇳 honduras hondura|🇭🇷 croatia|🇭🇹 haiti|🇭🇺 hungary|🇮🇨 canary islands island|🇮🇪 ireland|🇮🇱 israel|🇮🇲 isle man|🇮🇴 british indian ocean territory|🇮🇶 iraq|🇮🇷 iran|🇮🇸 iceland|🇯🇪 jersey|🇯🇲 jamaica|🇰🇪 kenya|🇰🇬 kyrgyzstan|🇰🇭 cambodia|🇰🇮 kiribati|🇰🇲 comoros|🇰🇳 st kitts kitt nevis|🇰🇵 north korea|🇰🇷 south korea|🇰🇾 cayman islands island|🇰🇿 kazakhstan|🇱🇦 laos|🇱🇨 st lucia|🇱🇮 liechtenstein|🇱🇰 sri lanka|🇱🇷 liberia|🇱🇸 lesotho|🇱🇹 lithuania|🇱🇺 luxembourg|🇱🇻 latvia|🇱🇾 libya|🇲🇨 monaco|🇲🇩 moldova|🇲🇪 montenegro|🇲🇫 st martin|🇲🇬 madagascar|🇲🇭 marshall islands island|🇲🇰 north macedonia|🇲🇱 mali|🇲🇲 myanmar burma|🇲🇳 mongolia|🇲🇴 macao sar china|🇲🇵 northern mariana islands island|🇲🇶 martinique|🇲🇷 mauritania|🇲🇸 montserrat|🇲🇹 malta|🇲🇺 mauritius|🇲🇻 maldives maldive|🇲🇼 malawi|🇲🇽 mexico|🇲🇾 malaysia|🇲🇿 mozambique|🇳🇦 namibia|🇳🇨 new caledonia|🇳🇪 niger|🇳🇫 norfolk island|🇳🇬 nigeria|🇳🇮 nicaragua|🇳🇱 netherlands netherland|🇳🇴 norway|🇳🇵 nepal|🇳🇷 nauru|🇳🇺 niue|🇳🇿 new zealand|🇵🇦 panama|🇵🇪 peru|🇵🇫 french polynesia|🇵🇬 papua new guinea|🇵🇭 philippines philippine|🇵🇱 poland|🇵🇲 st pierre miquelon|🇵🇳 pitcairn islands island|🇵🇷 puerto rico|🇵🇸 palestinian territories territory|🇵🇹 portugal|🇵🇼 palau|🇵🇾 paraguay|🇷🇪 union|🇷🇴 romania|🇷🇸 serbia|🇷🇺 russia|🇷🇼 rwanda|🇸🇧 solomon islands island|🇸🇨 seychelles seychelle|🇸🇩 sudan|🇸🇪 sweden|🇸🇬 singapore|🇸🇭 st helena|🇸🇮 slovenia|🇸🇯 svalbard jan mayen|🇸🇰 slovakia|🇸🇱 sierra leone|🇸🇲 san marino|🇸🇳 senegal|🇸🇴 somalia|🇸🇷 suriname|🇸🇸 south sudan|🇸🇹 tom pr ncipe|🇸🇻 el salvador|🇸🇽 sint maarten|🇸🇾 syria|🇸🇿 eswatini|🇹🇦 tristan da cunha|🇹🇨 turks turk caicos islands island|🇹🇩 chad|🇹🇫 french southern territories territory|🇹🇬 togo|🇹🇭 thailand|🇹🇯 tajikistan|🇹🇰 tokelau|🇹🇱 timor leste|🇹🇲 turkmenistan|🇹🇳 tunisia|🇹🇴 tonga|🇹🇹 trinidad tobago|🇹🇻 tuvalu|🇹🇼 taiwan|🇹🇿 tanzania|🇺🇦 ukraine|🇺🇬 uganda|🇺🇲 outlying islands island|🇺🇳 united nations nation|🇺🇾 uruguay|🇺🇿 uzbekistan|🇻🇦 vatican city|🇻🇨 st vincent grenadines grenadine|🇻🇪 venezuela|🇻🇬 british virgin islands island|🇻🇮 virgin islands island|🇻🇳 vietnam|🇻🇺 vanuatu|🇼🇫 wallis futuna|🇼🇸 samoa|🇽🇰 kosovo|🇾🇪 yemen|🇾🇹 mayotte|🇿🇦 south africa|🇿🇲 zambia|🇿🇼 zimbabwe|🏴󠁧󠁢󠁥󠁮󠁧󠁿 england|🏴󠁧󠁢󠁳󠁣󠁴󠁿 scotland|🏴󠁧󠁢󠁷󠁬󠁳󠁿 wales wale",
};
export interface EmojiItem { e: string; words: string }
export const emojiCategories: { name: string; items: EmojiItem[] }[] = Object.entries(EMOJI_SOURCE).map(([name, src]) => ({
  name, items: src.split("|").map((x) => { const [e, ...w] = x.trim().split(" "); return { e, words: w.join(" ") }; }),
}));
