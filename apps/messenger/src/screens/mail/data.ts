import { avatar, img } from '../../ui';

export const categories = ['All', 'Primary', 'Social', 'Updates', 'Promotions'] as const;
export type Category = typeof categories[number];
export const folders = ['Inbox', 'Drafts', 'Sent', 'Deleted'] as const;
export type Folder = typeof folders[number];
export interface Email {
  /** Inbox when absent. Drafts come from the store (any screen can save one). */
  folder?: Exclude<Folder, 'Drafts'>; draftId?: string; draftBy?: 'messenger';
  id: string; sender: string; address: string; category: Exclude<Category, 'All'>;
  subject: string; preview: string; time: string; date: string; unread: boolean; starred: boolean;
  initials: string; face?: string; tone: 'blue' | 'purple' | 'red' | 'green';
  paragraphs: string[]; summary: string; website: string; phone: string; location: string;
  attachments: { name: string; size: string }[]; hero?: string; flight?: boolean;
}
const flightPhoto = img('photo-1436491865332-7a61a109cc05', 1200);
const dubai = img('photo-1512453979798-5ea266f8880c', 1200);
const food = img('photo-1498837167922-ddd27525d352', 1000);
const email = (id: string, sender: string, subject: string, category: Email['category'], time: string,
  paragraphs: string[], extra: Partial<Email> = {}): Email => ({
  id, sender, subject, category, time, paragraphs, preview: paragraphs[0], date: 'Monday, 5 October 2026',
  address: `hello@${sender.toLowerCase().replace(/[^a-z]/g, '')}.com`, unread: false, starred: false,
  initials: sender.slice(0, 2), tone: 'blue', website: `${sender.toLowerCase().replace(/[^a-z]/g, '')}.com`,
  phone: '+971 4 555 0100', location: 'Dubai, UAE', attachments: [],
  summary: paragraphs.slice(0, 2).join(' '), ...extra,
});
export const emails: Email[] = [
  email('emirates', 'Emirates', 'Your booking is confirmed', 'Updates', '9:14 AM', [
    'Hello Haitham, your next journey is all set. We look forward to welcoming you on board flight EK007 from Dubai to London on Thursday, 15 October.',
    'Your booking reference is EK429H. Online check-in opens 48 hours before departure. Please arrive at Dubai International, Terminal 3, at least three hours before your flight.',
    'Your Economy fare includes one checked bag up to 25 kg and a 7 kg cabin bag. You can choose your seat and meal preference before check-in.',
    'Thank you for flying with Emirates. A little planning now means a more relaxed journey later.',
  ], { unread: true, starred: true, tone: 'red', address: 'noreply@emirates.com', website: 'emirates.com', phone: '+971 600 555 555', location: 'Emirates Group HQ, Dubai', hero: flightPhoto, flight: true,
    attachments: [{ name: 'EK429H_Itinerary.pdf', size: '328 KB' }, { name: 'Baggage_Information.pdf', size: '214 KB' }],
    summary: 'Dubai → London, EK007, Thursday 15 October. Departure 10:30 from Terminal 3; arrival 14:55. Booking EK429H, one passenger, Economy, 25 kg checked baggage. Check in online 48 hours before departure.' }),
  email('booking', 'Booking.com', 'Your London stay is confirmed', 'Updates', '8:47 AM', [
    'Hi Haitham, you are booked at The Hoxton, Holborn from 15–18 October. Your room is a Cosy Double for one guest, with breakfast included.',
    'Check-in starts at 2 PM. The hotel can keep your bags if you arrive early. Your total is AED 2,180, payable at the property.',
    'Free cancellation is available until 12 October at 6 PM local time. The booking number is 4819 2057. Have a wonderful stay in London.',
  ], { unread: true, address: 'bookings@booking.com', website: 'booking.com', attachments: [{ name: 'Hotel_Confirmation.pdf', size: '186 KB' }] }),
  email('messenger', 'Team Messenger', 'Weekly product update', 'Primary', 'Yesterday', [
    'This week we polished the Flights workspace and made Messenger Updates easier to scan. The new details now stay in context while you keep chatting.',
    'Please review the desktop demo before Wednesday. We especially want feedback on mail reading, quick research, and the transition back into a chat.',
    'Add screenshots and one sentence about what felt confusing. Thanks for helping us make the demo feel calm and useful.',
  ], { unread: true, tone: 'purple', address: 'team@messenger.app', website: 'messenger.app', attachments: [{ name: 'Demo_Checklist.pdf', size: '92 KB' }] }),
  email('linkedin', 'LinkedIn', '5 new job recommendations', 'Social', 'Yesterday', [
    'Your experience in AI products matches five new roles in the UAE, including Senior AI Engineer, Applied ML Lead, and Solutions Architect.',
    'Two roles offer hybrid schedules and three are based in Dubai. The listed salary bands range from AED 28,000 to AED 45,000 per month.',
    'Update your preferred location and notice period to make the next batch more relevant. You can save roles and review them when you have time.',
  ], { unread: true, initials: 'in', address: 'jobs-noreply@linkedin.com', website: 'linkedin.com' }),
  email('hadeel', 'Hadeel Eitsalat', 'Re: Project roadmap', 'Primary', 'Yesterday', [
    'Hi Haitham, thanks for sharing the revised roadmap. The first milestone looks achievable if we keep the demo scope tight.',
    'Let’s move the user walkthrough to Thursday morning and reserve Friday for fixes. I added comments beside the onboarding and research items.',
    'Could you send the final screen list by tomorrow afternoon? I’ll consolidate the review notes before our call. Best, Hadeel.',
  ], { face: avatar(44), starred: true, address: 'hadeel@studio.example', website: 'studio.example', attachments: [{ name: 'Roadmap_Comments.pdf', size: '420 KB' }] }),
  email('idc', 'IDC Technologies', 'QA Automation · Arabic speaker', 'Primary', 'Mon', [
    'Hello Haitham, we are hiring an Arabic-speaking QA Automation Engineer for a Dubai client. The team tests mobile messaging and customer-service workflows.',
    'The role uses Playwright, API testing, and CI pipelines. Interviews include a short practical exercise followed by a conversation with the engineering lead.',
    'If this sounds interesting, reply with a current CV and your availability this week. We can also share the full job description first.',
  ], { address: 'careers@idctechnologies.com', website: 'idctechnologies.com' }),
  email('openai', 'OpenAI', 'Your September API usage report', 'Updates', 'Mon', [
    'Your September usage report is ready. The workspace processed 1,284 text requests across development and evaluation projects.',
    'Your demo project accounted for most requests. We recommend separating production and development projects so usage is easier to review.',
    'The attached statement contains your daily totals and model breakdown. Your billing settings and spending limit remain unchanged.',
  ], { initials: 'AI', address: 'billing@openai.com', website: 'openai.com', attachments: [{ name: 'September_Statement.pdf', size: '156 KB' }] }),
  email('neowell', 'NeoHealth', 'Partnership opportunity', 'Primary', 'Mon', [
    'Hi Haitham, we enjoyed your product demo and would love to discuss how a private messaging workspace could support our care coordinators.',
    'Our first use case is appointment reminders and document sharing. We are looking for a simple pilot with a small team, rather than a full integration.',
    'Would you be available for a 20-minute call next Tuesday? I can send a short outline of the workflow beforehand.',
  ], { tone: 'green', website: 'neohealth.example', address: 'partnerships@neohealth.example' }),
  email('hypersolutions', 'HyperSolutions', 'AI Team Lead · Next steps', 'Primary', 'Sun', [
    'Thanks for the great conversation, Haitham. The team enjoyed hearing how you approach evaluation and shipping small, useful AI features.',
    'The next stage is a 45-minute discussion about a multilingual support assistant. There is no take-home assignment; we will work through trade-offs together.',
    'Please share two time slots for Wednesday or Thursday. We will send the agenda and panel names with the calendar invitation.',
  ], { unread: true, attachments: [{ name: 'Interview_Agenda.pdf', size: '78 KB' }], address: 'talent@hypersolutions.example', website: 'hypersolutions.example' }),
  email('github', 'GitHub', '[Messenger] 3 new notifications', 'Updates', 'Sun', [
    'You have two pull requests awaiting review and one comment on the desktop layout issue.',
    'The Flights date formatting change is ready for review. The second pull request adds retry handling for completed-generation cards.',
    'Your notification preferences are unchanged. Review the small changes first so the remaining branches can merge cleanly.',
  ], { initials: 'GH', address: 'notifications@github.com', website: 'github.com' }),
  email('careem', 'Careem', 'Your ride receipt · Downtown Dubai', 'Updates', 'Sat', [
    'Thanks for riding with us, Haitham. Your trip from Business Bay to Downtown Dubai was completed at 7:42 PM.',
    'The fare was AED 34.50, including VAT, paid with your card ending in 2048. The ride took 18 minutes.',
    'Your receipt is attached for your records. We hope to see you again soon.',
  ], { tone: 'green', address: 'receipts@careem.com', website: 'careem.com', attachments: [{ name: 'Ride_Receipt.pdf', size: '62 KB' }] }),
  email('noon', 'noon', 'A little weekend upgrade', 'Promotions', 'Sat', [
    'Your saved wireless headphones are back in stock. This weekend’s offer includes next-day delivery within Dubai.',
    'The price is AED 299 and the offer ends Sunday evening. You can review the delivery estimate and return policy before checkout.',
    'Looking for something else? Your saved list is still right where you left it.',
  ], { tone: 'purple', address: 'offers@noon.com', website: 'noon.com' }),
  email('etisalat', 'Etisalat', 'Your October bill is ready', 'Updates', 'Fri', [
    'Hello Haitham, your mobile bill for October is AED 210 including VAT. Payment is due on 20 October.',
    'Your plan includes 20 GB of data and unlimited local minutes. You used 14.2 GB during the last billing cycle.',
    'The detailed bill is attached. Auto-pay remains active, so no action is needed unless you would like to review the charges.',
  ], { tone: 'green', address: 'billing@etisalat.ae', website: 'etisalat.ae', attachments: [{ name: 'October_Bill.pdf', size: '204 KB' }] }),
  email('sara', 'Sara Ali', 'Dinner on Thursday?', 'Primary', 'Fri', [
    'Hey Haitham! I found a little Italian place in Jumeirah that looks perfect for our celebration dinner.',
    'They have burrata, handmade pasta, and a terrace. I can book for 7:30 on Thursday if that works for you.',
    'Bring your appetite. I’ve already looked at the dessert menu twice 😄',
  ], { face: avatar(47), hero: food, address: 'sara@friends.example', website: 'friends.example', starred: true }),
  email('figma', 'Figma', 'Your team’s latest design notes', 'Social', 'Thu', [
    'There are four new comments on the Messenger desktop exploration. The latest frames include mail context cards and a quieter research reader.',
    'Lina suggested keeping the header height consistent across workspaces. Omar left a note about making the report’s source list easier to scan.',
    'The prototype is ready for another walkthrough whenever you are. All comments are grouped by frame.',
  ], { tone: 'purple', address: 'notifications@figma.com', website: 'figma.com' }),
  email('omar', 'Omar Khalid', 'Bali itinerary · first draft', 'Primary', 'Thu', [
    'Hi Haitham, I put together a relaxed seven-day plan for Bali: three nights in Ubud, then four by the coast.',
    'The draft keeps the first afternoon free after the flight. I added one temple visit, a rice-terrace walk, and a few good local places to eat.',
    'Have a look at the attached itinerary and tell me what you would swap. We can book the stays after everyone has weighed in.',
  ], { face: avatar(59), address: 'omar@friends.example', website: 'friends.example', attachments: [{ name: 'Bali_Seven_Days.pdf', size: '512 KB' }] }),
  email('visitdubai', 'Visit Dubai', 'A quieter side of the city', 'Promotions', 'Wed', [
    'Find a slower weekend in Dubai with a sunrise walk along the creek, a gallery visit in Alserkal Avenue, and coffee by the water.',
    'Our October guide brings together small exhibitions, outdoor markets, and places to sit for a while without a packed itinerary.',
    'Save a few favorites and make a day of it when the weather cools down.',
  ], { hero: dubai, address: 'newsletter@visitdubai.com', website: 'visitdubai.com' }),
  email('mazen', 'Mazen', 'The spreadsheet survived', 'Primary', 'Tue', [
    'Good news: I fixed the budget sheet. Bad news: it turns out the numbers were correct and I really do order that much coffee.',
    'I added a small tab for our London spending so we can stop doing mental currency conversions in the queue.',
    'Check the hotel line when you get a minute. Everything else looks sensible, which is suspicious for a plan made by us.',
  ], { face: avatar(53), address: 'mazen@friends.example', website: 'friends.example', attachments: [{ name: 'London_Budget.pdf', size: '144 KB' }] }),
];
