import type { ResearchItem } from '../../types';
import { img } from '../../ui';
export interface Report extends ResearchItem {
  date: string; reading: string; category: string; status: 'running' | 'completed' | 'failed'; startedAt?: number;
  /** Hand-written or offline content, labelled "Demo" in the list and the report. */
  demo?: boolean; error?: string;
  stats: { value: string; label: string }[]; sourceCount: number;
}
const dubai = img('photo-1512453979798-5ea266f8880c', 1400);
const office = img('photo-1497366754035-f200968a6e72', 1400);
const technology = img('photo-1516321318423-f06f85e504b3', 1400);
const people = img('photo-1519389950473-47ba0277781c', 1400);
const cloud = img('photo-1486406146926-c627a92ad1ab', 1400);
const source = (title: string, domain: string) => ({ title, domain });
const report = (id: string, title: string, summary: string, findings: string[], stats: Report['stats'], sources: NonNullable<Report['sources']>, image: string, extra: Partial<Report> = {}): Report => ({
  id, title, summary, findings, stats, sources, image, sourceCount: sources.length,
  time: '12:36 PM', date: '5 October 2026', reading: '4 min read', category: 'Market intelligence', status: 'completed', demo: true, ...extra,
});
/** Covers for the weekly watch topics (ids already used above; new ones could not be verified to load). */
export const watchCovers: Record<string, string> = { phones: technology, supercars: dubai };
// All figures and findings below are hand-written demo content, not live research.
export const reports: Report[] = [
  report('uae-ai', 'UAE AI market trends 2026', 'The UAE’s AI market is moving from experimentation to practical deployment. Sovereign infrastructure, Arabic-language products and focused enterprise tools are shaping the next wave of opportunities. The strongest teams pair reliable engineering with a clear customer workflow.', [
    'Government-backed investment is strengthening sovereign AI and cloud infrastructure, making regional deployment an increasingly practical choice.',
    'Demand for Arabic NLP is growing beyond translation: search, customer support and document workflows need local vocabulary and mixed-language evaluation.',
    'Healthcare, logistics and public services are adopting focused assistants that save measurable time rather than broad chat experiences.',
    'AI engineering, MLOps and retrieval skills are appearing together in hiring briefs. Teams value the ability to deploy, evaluate and maintain a system.',
    'Smaller pilots with a named owner and clear success criteria are more likely to graduate into repeatable enterprise products.',
  ], [{ value: '68%', label: 'pilots target a workflow' }, { value: '3×', label: 'Arabic product interest' }, { value: 'AED 30–50k', label: 'senior salary band' }], [source('UAE artificial intelligence strategy', 'ai.gov.ae'), source('Regional technology outlook', 'pwc.com'), source('Enterprise adoption briefing', 'mckinsey.com'), source('Dubai digital economy overview', 'digitaldubai.ae')], dubai),
  report('rag', 'RAG vs fine-tuning: choosing the right fit', 'Retrieval and fine-tuning solve different problems. Retrieval is usually the first move when facts change often; fine-tuning becomes useful when a consistent behavior or format matters across many examples. A small evaluation set should drive the choice.', [
    'Use retrieval for changing policies, product catalogs and private documents; keep citations attached to the retrieved evidence.',
    'Use fine-tuning for stable response patterns, specialist terminology and structured outputs that are hard to express reliably in prompts.',
    'Start with a strong baseline and 50–100 realistic questions. Separate missing evidence from poor reasoning before changing the model.',
    'Chunk quality and document freshness often matter more than a larger embedding model in the first retrieval iteration.',
    'A hybrid approach can work well: retrieval supplies current facts while a tuned model follows a consistent tone and format.',
  ], [{ value: '72%', label: 'queries need fresh facts' }, { value: '80', label: 'evaluation questions' }, { value: '2', label: 'complementary approaches' }], [source('Retrieval evaluation notes', 'arxiv.org'), source('Search architecture guide', 'learn.microsoft.com'), source('Practical evaluation handbook', 'huggingface.co')], technology, { time: '10:12 AM', category: 'Technical comparison' }),
  report('arabic', 'Arabic LLM benchmarks: beyond one score', 'A useful Arabic benchmark reflects the language people actually use: dialects, formal text, code-switching and domain-specific terms. Evaluation should measure helpfulness and grounded answers alongside basic language accuracy.', [
    'Include Gulf, Egyptian and Levantine examples alongside Modern Standard Arabic to avoid an inflated single-language score.',
    'Use mixed Arabic-English messages from realistic workflows, especially names, dates and technical phrases.',
    'Score groundedness separately from fluency: a polished sentence can still invent an answer or cite the wrong document.',
    'Have native reviewers compare short response pairs and record the reason for each preference.',
    'Keep a private holdout set and refresh examples after major prompt or model changes.',
  ], [{ value: '4', label: 'language varieties' }, { value: '120', label: 'review examples' }, { value: '2', label: 'native reviewers per pair' }], [source('Arabic language model evaluation', 'arxiv.org'), source('Multilingual evaluation datasets', 'huggingface.co'), source('Regional AI research', 'mbzuai.ac.ae')], people, { time: 'Yesterday', date: '4 October 2026', category: 'Language & evaluation' }),
  report('local', 'Local LLM deployment options', 'Local deployment can make sense for private workloads and predictable traffic, but it adds operational responsibility. Hardware planning, model quality and a careful update process matter as much as the initial demo.', [
    'A quantized small model is a useful starting point for extraction and classification before attempting broad conversational use.',
    'Size memory for the model and expected context window; long documents can change capacity needs substantially.',
    'Measure first-token latency and throughput with the actual prompt mix, not only a short synthetic request.',
    'Keep a managed fallback for tasks the local model handles poorly, subject to the customer’s data policy.',
    'Plan model upgrades, monitoring and rollback before adding more users to the deployment.',
  ], [{ value: '8B', label: 'pilot model size' }, { value: '24 GB', label: 'prototype memory budget' }, { value: '3', label: 'serving options compared' }], [source('Local inference deployment notes', 'huggingface.co'), source('Serving performance guide', 'docs.vllm.ai'), source('Hardware planning overview', 'nvidia.com')], cloud, { time: 'Oct 2', date: '2 October 2026', category: 'Infrastructure' }),
  report('moderation', 'Instagram comment moderation playbook', 'Moderation works best as a layered workflow: clear rules for obvious cases, contextual review for ambiguous comments, and a human path for appeals. Multilingual communities need explicit treatment of dialect and friendly teasing.', [
    'Separate spam, threats and personal abuse from criticism, disagreement and joking between friends.',
    'Use high-confidence rules for repetitive promotional spam before applying a model to nuanced cases.',
    'Route uncertain comments to a reviewer and preserve context from the surrounding conversation.',
    'Evaluate Arabic dialect and emoji-heavy comments rather than relying on literal keyword matches.',
    'Track false positives and appeals so the policy can improve without silently restricting legitimate discussion.',
  ], [{ value: '5', label: 'moderation categories' }, { value: '18%', label: 'sample requires review' }, { value: '24h', label: 'appeal response target' }], [source('Community moderation policy', 'transparency.meta.com'), source('Online safety workflow notes', 'ofcom.org.uk'), source('Multilingual classification research', 'arxiv.org')], technology, { time: 'Oct 2', date: '2 October 2026', category: 'Trust & safety' }),
  report('jobs', 'AI job market in the UAE', 'Employers are looking for people who can turn a model into a dependable product. Strong candidates connect evaluation, data handling and deployment with an understanding of the business problem they are solving.', [
    'Applied AI roles increasingly combine backend engineering, retrieval and evaluation responsibilities.',
    'Portfolio projects that show failure handling and measured outcomes are more persuasive than a list of model names.',
    'Arabic-language experience is valuable for customer support, document processing and public-sector work.',
    'Compensation varies sharply by team maturity; compare ownership, benefits and workload alongside monthly salary.',
    'MLOps, cloud security and product communication help engineers move into senior and lead positions.',
  ], [{ value: '42', label: 'sample job descriptions' }, { value: 'AED 28–45k', label: 'senior monthly range' }, { value: '61%', label: 'roles mention deployment' }], [source('UAE hiring market overview', 'linkedin.com'), source('Technology salary guide', 'hays.ae'), source('Digital economy skills briefing', 'digitaldubai.ae')], office, { time: 'Oct 1', date: '1 October 2026', category: 'Careers' }),
  report('sovereign', 'Sovereign cloud in the GCC', 'Cloud residency is only one part of sovereignty. Buyers also care about operating control, encryption ownership, support access and the ability to move workloads without rebuilding every dependency.', [
    'Define which data must remain in-region and how backups, logs and support access are handled.',
    'Treat key ownership and privileged access as separate procurement questions from the hosting region.',
    'Map service dependencies early; not every managed feature is available in every regional deployment.',
    'Use open interfaces where practical so a change in provider does not become a full application rewrite.',
    'Review operational responsibilities with the customer’s security team before promising a sovereign deployment.',
  ], [{ value: '6', label: 'procurement criteria' }, { value: '3', label: 'regional patterns' }, { value: '90 days', label: 'sample pilot timeline' }], [source('Regional cloud adoption overview', 'pwc.com'), source('Cloud architecture guidance', 'learn.microsoft.com'), source('Digital infrastructure outlook', 'gcc-sg.org')], cloud, { time: 'Sep 30', date: '30 September 2026', category: 'Infrastructure' }),
  report('agents', 'Agentic workflows in enterprise', 'The best enterprise agent pilots automate a small chain of useful actions with visible boundaries. Reliability improves when tools are narrow, state is explicit and a human can review consequential steps.', [
    'Choose a workflow with a clear starting event and a measurable finish, such as preparing a support-case brief.',
    'Use narrow tool contracts and validate inputs before allowing a model to take an action.',
    'Keep state and retries outside the prompt so partial failures can be recovered predictably.',
    'Require review for consequential writes and make the proposed action easy to inspect.',
    'Measure task completion and recovery rates rather than counting the number of autonomous steps.',
  ], [{ value: '4', label: 'workflow stages' }, { value: '87%', label: 'sample completion rate' }, { value: '1', label: 'human review checkpoint' }], [source('Enterprise automation briefing', 'mckinsey.com'), source('Workflow evaluation patterns', 'arxiv.org'), source('Responsible AI architecture', 'learn.microsoft.com')], people, { time: 'Sep 29', date: '29 September 2026', category: 'Enterprise' }),
  report('arabic-support', 'Arabic customer support workflows', 'Comparing routing, retrieval and escalation patterns for a bilingual support desk.', [], [], [source('Service design notes', 'digitaldubai.ae')], technology, { status: 'running', startedAt: Date.now() - 18000, time: 'Started just now', category: 'Customer experience' }),
  report('travel-ai', 'AI tools for travel planning', 'Mapping itinerary assistants, flight alerts and the handoff to a human travel adviser.', [], [], [source('Travel industry outlook', 'pwc.com')], dubai, { status: 'running', startedAt: Date.now() - 42000, time: 'Started just now', category: 'Travel' }),
];
// What the two running seeds become once they "finish" (2–5 s after Research is first opened).
export const seedResults: Record<string, Partial<Report>> = {
  'arabic-support': {
    summary: 'A bilingual support desk works best when routing understands dialect, retrieval answers from approved content and escalation keeps the full conversation. Most gains come from fixing handoffs, not from a larger model.',
    findings: [
      'Detect language and dialect at the first message so the case reaches an agent or flow that can answer in the customer’s own register.',
      'Answer routine questions from an approved Arabic and English knowledge base, with the source shown to the agent before sending.',
      'Escalate with the whole thread and a short summary so customers never repeat themselves after a handoff.',
      'Measure first-contact resolution separately for Arabic and English; averages hide the language that is underserved.',
      'Review a weekly sample of mixed-language chats with native speakers to catch tone and terminology issues early.',
    ],
    stats: [{ value: '41%', label: 'routine cases automated' }, { value: '2', label: 'languages, 3 dialects' }, { value: '<2 min', label: 'target handoff time' }],
    sources: [source('Service design notes', 'digitaldubai.ae'), source('Customer service benchmarks', 'zendesk.com'), source('Multilingual retrieval study', 'arxiv.org')],
    sourceCount: 3, time: 'Just now', category: 'Customer experience',
  },
  'travel-ai': {
    summary: 'Travel assistants are most useful around the trip, not just at booking: they watch prices and schedules, rebuild plans when something changes and hand complex itineraries to a human adviser with context attached.',
    findings: [
      'Itinerary assistants earn trust by drafting a plan the traveller can edit rather than booking on their behalf.',
      'Price and schedule alerts are the most-used feature; travellers return when an alert saved money or a missed connection.',
      'Disruption handling (rebooking options within minutes) is where AI support is most valued and least mature.',
      'Hand off multi-city, group and premium trips to a human adviser together with the draft plan and preferences.',
      'Keep loyalty numbers, passport details and payment outside the model; pass only references to the booking system.',
    ],
    stats: [{ value: '3', label: 'assistant patterns compared' }, { value: '27%', label: 'trips hit a disruption' }, { value: '1', label: 'human handoff point' }],
    sources: [source('Travel industry outlook', 'pwc.com'), source('Airline disruption report', 'iata.org'), source('Travel technology trends', 'phocuswright.com')],
    sourceCount: 3, time: 'Just now', category: 'Travel',
  },
};
export function makeReport(id: string, topic: string): Report {
  return report(id, topic, `This brief explores ${topic.toLowerCase()} through the lens of a small, practical pilot. The focus is on clear outcomes, dependable delivery and a straightforward way to compare options before committing to a larger rollout.`, [
    'Define the audience and the specific decision this report should support before collecting more information.',
    'Compare a small set of realistic options against cost, reliability and the effort required to maintain them.',
    'Start with a limited pilot and record a baseline so improvements can be measured rather than assumed.',
    'Assign a clear owner for reviewing results, handling exceptions and keeping the supporting material current.',
    'Use the pilot findings to decide what to scale, what to simplify and what needs further investigation.',
  ], [{ value: '5', label: 'key findings' }, { value: '3', label: 'sources reviewed' }, { value: '3', label: 'practical next steps' }], [source('Market and strategy briefing', 'pwc.com'), source('Enterprise adoption overview', 'mckinsey.com'), source('Applied research library', 'arxiv.org')], office, { sourceCount: 3, time: 'Just now', date: '5 October 2026', category: 'Your research', demo: false });
}
