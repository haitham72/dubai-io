import Foundation

public struct SessionInfo: Decodable, Sendable {
    public let userId: String
    public let mode: String

    private enum CodingKeys: String, CodingKey { case userId = "user_id", mode }
}

public struct Health: Decodable, Sendable {
    public let ok: Bool
    public let openaiKey: Bool
    public let googleKey: Bool
    /// Widget-origin port for sandboxed provider mini-apps; absent when disabled.
    public let widgetPort: Int?

    private enum CodingKeys: String, CodingKey { case ok, openaiKey = "openai_key", googleKey = "google_key", widgetPort = "widget_port" }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        ok = (try? values.decode(Bool.self, forKey: .ok)) ?? false
        openaiKey = (try? values.decode(Bool.self, forKey: .openaiKey)) ?? false
        googleKey = (try? values.decode(Bool.self, forKey: .googleKey)) ?? false
        widgetPort = try values.decodeIfPresent(Int.self, forKey: .widgetPort)
    }
}

public struct Catalog: Decodable, Sendable {
    public let provenance: String
    public let asOf: String
    public let providers: [Provider]

    private enum CodingKeys: String, CodingKey { case provenance, asOf = "as_of", providers }
}

public struct Provider: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let service: String
    public let items: [PublishedItem]
    public let slots: [String]
}

public struct PublishedItem: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let priceAed: Double

    private enum CodingKeys: String, CodingKey { case id, name, priceAed = "price_aed" }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decode(String.self, forKey: .id)
        name = try values.decode(String.self, forKey: .name)
        // The host catalog publishes fixed decimal prices as JSON strings.
        let price: Double?
        if let numeric = try? values.decode(Double.self, forKey: .priceAed) {
            price = numeric
        } else {
            price = Double(try values.decode(String.self, forKey: .priceAed))
        }
        guard let price, price.isFinite, price >= 0 else {
            throw DecodingError.dataCorruptedError(forKey: .priceAed, in: values, debugDescription: "Invalid published price")
        }
        priceAed = price
    }
}

public struct SavedFact: Decodable, Identifiable, Sendable {
    public var id: String { key }
    public let key: String
    public let value: String
    public let provenance: String
    public let asOf: String?

    private enum CodingKeys: String, CodingKey { case key, value, provenance, asOf = "as_of" }
}

public struct SavedMemory: Decodable, Sendable {
    public let told: [SavedFact]
}

public struct Connections: Decodable, Sendable {
    public let providers: [AccountConnection]
}

public struct AccountConnection: Decodable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let status: String
    public let accountLabel: String?

    private enum CodingKeys: String, CodingKey { case id, label, status, accountLabel = "account_label" }
}

public struct PlaceResults: Decodable, Sendable {
    public let places: [Place]
    public let attribution: String
    public let asOf: String

    private enum CodingKeys: String, CodingKey { case places, attribution, asOf = "as_of" }
}

public struct Place: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let rating: Double?
    public let ratings: Int?
    public let lat: Double?
    public let lng: Double?
    public let address: String?
    public let shortAddress: String?
    public let mapsUrl: String?
    public let website: String?
    public let phone: String?
    public let openNow: Bool?
    public let photo: String?
    public let photoBy: [String]?
    public let distanceKm: Double?
    public let provenance: String?

    private enum CodingKeys: String, CodingKey {
        case id, name, rating, ratings, lat, lng, address, shortAddress = "short_address",
             mapsUrl = "maps_url", website, phone, openNow = "open_now", photo, photoBy = "photo_by",
             distanceKm = "distance_km", provenance
    }
}

public struct ResearchSource: Decodable, Identifiable, Sendable {
    public var id: String { url }
    public let title: String
    public let url: String
    public let asOf: String?

    private enum CodingKeys: String, CodingKey { case title, url, asOf = "as_of" }
}

public struct Product: Decodable, Identifiable, Sendable {
    public var id: String { link }
    public let title: String
    public let link: String
    public let price: String?
    public let thumbnail: String?
    public let asOf: String?

    private enum CodingKeys: String, CodingKey { case title, link, price, thumbnail, asOf = "as_of" }
}

public struct LunaReply: Decodable, Sendable {
    public let intent: String
    public let confidence: Double
    public let reply: String
    public let clarify: String?
    public let answer: String?
    public let service: String?
    public let category: String?
    public let subcategory: String?
    public let sources: [ResearchSource]?
    public let products: [Product]?
    public let via: String

    public var displayText: String {
        if let answer, !answer.isEmpty { return answer }
        if intent == "unclear", let clarify, !clarify.isEmpty { return clarify }
        return reply
    }
}

// MARK: - Today / tasks (plan FIN-08: needs_you decisions, counts, check-backs)

/// Tolerant AED amount: the host catalog publishes fixed prices as JSON
/// strings while other endpoints use numbers. Accepts either; null/absent is nil.
private func decodeMoney<CodingKeys: CodingKey>(
    _ values: KeyedDecodingContainer<CodingKeys>, key: CodingKeys
) throws -> Double? {
    if values.contains(key) == false { return nil }
    if (try? values.decodeNil(forKey: key)) == true { return nil }
    if let amount = try? values.decode(Double.self, forKey: key) { return amount }
    guard let raw = try? values.decode(String.self, forKey: key),
          let amount = Double(raw), amount.isFinite, amount >= 0
    else {
        throw DecodingError.dataCorruptedError(
            forKey: key, in: values, debugDescription: "Invalid AED amount")
    }
    return amount
}

public struct TaskDecision: Decodable, Sendable {
    public let kind: String
    public let title: String
    public let detail: String?
    public let actionID: String
    public let revision: Int
    public let sourceStatus: String?
    public let snapshotHash: String?
    public let amountAed: Double?
    public let earlierTarget: String?

    private enum CodingKeys: String, CodingKey {
        case kind, title, detail, actionID = "action_id", revision, sourceStatus = "source_status",
             snapshotHash = "snapshot_hash", amountAed = "amount_aed", earlierTarget = "earlier_target"
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        kind = try values.decode(String.self, forKey: .kind)
        title = try values.decode(String.self, forKey: .title)
        detail = try values.decodeIfPresent(String.self, forKey: .detail)
        actionID = try values.decode(String.self, forKey: .actionID)
        revision = try values.decode(Int.self, forKey: .revision)
        sourceStatus = try values.decodeIfPresent(String.self, forKey: .sourceStatus)
        snapshotHash = try values.decodeIfPresent(String.self, forKey: .snapshotHash)
        amountAed = try decodeMoney(values, key: .amountAed)
        earlierTarget = try values.decodeIfPresent(String.self, forKey: .earlierTarget)
    }
}

/// A task record as `present()` serves it. `outcome` is the display title;
/// `title` is never a backend key.
public struct TodayTask: Decodable, Sendable {
    public let id: String
    public let outcome: String?
    public let details: String?
    public let nextStep: String?
    public let dueAt: String?
    public let status: String?
    public let revision: Int
    public let dueState: String?
    public let checkBackAt: String?
    public let sourceStatus: String?
    public let decision: TaskDecision?

    private enum CodingKeys: String, CodingKey {
        case id, outcome, details, nextStep = "next_step", dueAt = "due_at", status, revision,
             dueState = "due_state", checkBackAt = "check_back_at", sourceStatus = "source_status", decision
    }

    public var displayTitle: String { outcome ?? "Untitled task" }
}

public struct TodayCounts: Decodable, Sendable {
    public let needsYou: Int
    public let running: Int
    public let onList: Int
    public let paused: Int

    private enum CodingKeys: String, CodingKey {
        case needsYou = "needs_you", running, onList = "on_list", paused
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        needsYou = (try? values.decode(Int.self, forKey: .needsYou)) ?? 0
        running = (try? values.decode(Int.self, forKey: .running)) ?? 0
        onList = (try? values.decode(Int.self, forKey: .onList)) ?? 0
        paused = (try? values.decode(Int.self, forKey: .paused)) ?? 0
    }
}

public struct TodayLane: Decodable, Sendable {
    public let tasks: [TodayTask]
    public let hasMore: Bool?
    public let count: Int?

    private enum CodingKeys: String, CodingKey { case tasks, hasMore = "has_more", count }
}

/// `/api/today`: source-backed lanes only; each task appears in one lane.
public struct TodaySnapshot: Decodable, Sendable {
    public let needsYou: TodayLane?
    public let running: TodayLane?
    public let onList: TodayLane?
    public let paused: TodayLane?
    public let scheduled: TodayLane?
    public let completed: TodayLane?
    public let counts: TodayCounts
    public let asOf: String?

    private enum CodingKeys: String, CodingKey {
        case needsYou = "needs_you", running, onList = "on_list", paused, scheduled, completed,
             counts, asOf = "as_of"
    }
}

public struct TaskDetail: Decodable, Sendable {
    public let id: String
    public let outcome: String?
    public let details: String?
    public let nextStep: String?
    public let dueAt: String?
    public let status: String
    public let revision: Int
    public let mode: String?
    public let provenance: String?
    public let checkBackAt: String?
    public let result: String?
    public let dueState: String?

    private enum CodingKeys: String, CodingKey {
        case id, outcome, details, nextStep = "next_step", dueAt = "due_at", status, revision, mode,
             provenance, checkBackAt = "check_back_at", result, dueState = "due_state"
    }

    public var displayTitle: String { outcome ?? "Untitled task" }
}

/// Task endpoints answer `{task, replayed}`; a replayed write returns current state.
public struct TaskResponse: Decodable, Sendable {
    public let task: TaskDetail
    public let replayed: Bool?

    private enum CodingKeys: String, CodingKey { case task, replayed }
}

public struct TaskList: Decodable, Sendable {
    public let tasks: [TaskDetail]
    public let nextOffset: Int?

    private enum CodingKeys: String, CodingKey { case tasks, nextOffset = "next_offset" }
}

/// Wire body for `POST /api/tasks/{id}/commands`. The backend requires
/// `expected_revision` + `command_key` on every command; this type makes
/// them unskippable at the call site.
public struct TaskCommand: Encodable, Sendable {
    public let kind: String
    public let expectedRevision: Int
    public let commandKey: String
    public let at: String?

    private enum CodingKeys: String, CodingKey {
        case kind, expectedRevision = "expected_revision", commandKey = "command_key", at
    }

    public init(kind: String, expectedRevision: Int, commandKey: String, at: String? = nil) {
        self.kind = kind
        self.expectedRevision = expectedRevision
        self.commandKey = commandKey
        self.at = at
    }
}

// MARK: - Decisions / orders (approval before any send or share)

/// A user-supplied field on a prepared action. Only these keys may be shared.
public struct ActionField: Decodable, Sendable {
    public let value: String
    public let provenance: String?
}

public struct OrderLine: Decodable, Sendable {
    public let id: String?
    public let name: String?
    public let qty: Int?
    public let priceAed: Double?

    private enum CodingKeys: String, CodingKey { case id, name, qty, priceAed = "price_aed" }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decodeIfPresent(String.self, forKey: .id)
        name = try values.decodeIfPresent(String.self, forKey: .name)
        qty = try values.decodeIfPresent(Int.self, forKey: .qty)
        priceAed = try decodeMoney(values, key: .priceAed)
    }
}

public struct OrderSummary: Decodable, Sendable {
    public let provider: String?
    public let service: String?
    public let totalAed: Double?
    public let lines: [OrderLine]?

    private enum CodingKeys: String, CodingKey {
        case provider, service, totalAed = "total_aed", lines
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        provider = try values.decodeIfPresent(String.self, forKey: .provider)
        service = try values.decodeIfPresent(String.self, forKey: .service)
        totalAed = try decodeMoney(values, key: .totalAed)
        lines = try values.decodeIfPresent([OrderLine].self, forKey: .lines)
    }
}

public struct ActionEvidence: Decodable, Sendable {
    public let reference: String?
    public let provenance: String?
}

/// The canonical Action record. Status changes only on authoritative events;
/// model text never flips it. Unknown stays `UNKNOWN_STATUS`.
public struct ActionDetail: Decodable, Sendable {
    public let id: String
    public let capabilityID: String?
    public let recipient: String?
    public let effect: String?
    public let fixedTotalAed: Double?
    public let fields: [String: ActionField]?
    public let order: OrderSummary?
    public let missing: [String]?
    public let status: String
    public let executionAvailable: Bool?
    public let blockedReason: String?
    public let evidence: ActionEvidence?
    public let revision: Int
    public let snapshotHash: String?
    public let readyAt: String?
    public let title: String?

    private enum CodingKeys: String, CodingKey {
        case id, capabilityID = "capability_id", recipient, effect, fixedTotalAed = "fixed_total_aed",
             fields, order, missing, status, executionAvailable = "execution_available",
             blockedReason = "blocked_reason", evidence, revision, snapshotHash = "snapshot_hash",
             readyAt = "ready_at", title
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decode(String.self, forKey: .id)
        capabilityID = try values.decodeIfPresent(String.self, forKey: .capabilityID)
        recipient = try values.decodeIfPresent(String.self, forKey: .recipient)
        effect = try values.decodeIfPresent(String.self, forKey: .effect)
        fixedTotalAed = try decodeMoney(values, key: .fixedTotalAed)
        fields = try values.decodeIfPresent([String: ActionField].self, forKey: .fields)
        order = try values.decodeIfPresent(OrderSummary.self, forKey: .order)
        missing = try values.decodeIfPresent([String].self, forKey: .missing)
        revision = try values.decode(Int.self, forKey: .revision)
        snapshotHash = try values.decodeIfPresent(String.self, forKey: .snapshotHash)
        status = (try? values.decodeIfPresent(String.self, forKey: .status)) ?? "UNKNOWN_STATUS"
        executionAvailable = try values.decodeIfPresent(Bool.self, forKey: .executionAvailable)
        blockedReason = try values.decodeIfPresent(String.self, forKey: .blockedReason)
        evidence = try values.decodeIfPresent(ActionEvidence.self, forKey: .evidence)
        readyAt = try values.decodeIfPresent(String.self, forKey: .readyAt)
        title = try values.decodeIfPresent(String.self, forKey: .title)
    }

    /// Keys the user explicitly approved for sharing on this revision.
    public var sharedKeys: [String] { fields.map { Array($0.keys).sorted() } ?? [] }
}

/// `POST /api/actions/prepare`: the host rebuilds items/total from its catalog.
public struct PrepareField: Encodable, Sendable {
    public let value: String
    public let provenance: String

    public init(value: String, provenance: String = "user_supplied") {
        self.value = value
        self.provenance = provenance
    }
}

public struct PrepareOrderLine: Encodable, Sendable {
    public let id: String?
    public let name: String?
    public let qty: Int

    public init(id: String? = nil, name: String? = nil, qty: Int) {
        self.id = id
        self.name = name
        self.qty = qty
    }
}

public struct PrepareOrder: Encodable, Sendable {
    public let providerID: String
    public let items: [PrepareOrderLine]
    public let slot: String?

    private enum CodingKeys: String, CodingKey { case providerID = "provider_id", items, slot }

    public init(providerID: String, items: [PrepareOrderLine], slot: String? = nil) {
        self.providerID = providerID
        self.items = items
        self.slot = slot
    }
}

public struct PrepareInput: Encodable, Sendable {
    public let capabilityID: String
    public let fields: [String: PrepareField]
    public let order: PrepareOrder?
    public let draftID: String?
    public let preparationKey: String

    private enum CodingKeys: String, CodingKey {
        case capabilityID = "capability_id", fields, order, draftID = "draft_id", preparationKey = "preparation_key"
    }

    public init(capabilityID: String, fields: [String: PrepareField], order: PrepareOrder? = nil, draftID: String? = nil, preparationKey: String = UUID().uuidString) {
        self.capabilityID = capabilityID
        self.fields = fields
        self.order = order
        self.draftID = draftID
        self.preparationKey = preparationKey
    }
}

/// `POST /api/reminders` ("Remind me when it's ready"); the tap is the consent.
public struct ReadyReminder: Decodable, Sendable {
    public let scheduledFor: String?
    public let created: Bool?
    public let offerAuto: Bool?

    private enum CodingKeys: String, CodingKey { case scheduledFor = "scheduled_for", created, offerAuto = "offer_auto" }
}

// MARK: - Outbox messages / follow-up mode / morning brief (deterministic, never model text)

/// A delivered outbox message. Check-backs carry their `task_id`.
public struct OutboxMessage: Decodable, Sendable {
    public let id: String
    public let kind: String
    public let text: String?
    public let triggerSource: String?
    public let deliveredAt: String?
    public let dedupeKey: String?
    public let taskID: String?

    private enum CodingKeys: String, CodingKey {
        case id, kind, text, triggerSource = "trigger_source", deliveredAt = "delivered_at",
             dedupeKey = "dedupe_key", taskID = "task_id"
    }
}

public struct OutboxList: Decodable, Sendable {
    public let messages: [OutboxMessage]
}

public struct AssistState: Decodable, Sendable {
    public let mode: String
    public let manualReminders: Int?
    public let offerAuto: Bool?

    private enum CodingKeys: String, CodingKey { case mode, manualReminders = "manual_reminders", offerAuto = "offer_auto" }
}

/// `GET /api/routines/brief`: the morning-brief routine itself (opt-in 07:00-22:59,
/// 30-day expiry). The brief wording is derived from Today counts, never model text.
public struct BriefRoutine: Decodable, Sendable {
    public let kind: String
    public let atTime: String?
    public let active: Bool
    public let expiresAt: String?

    private enum CodingKeys: String, CodingKey { case kind, atTime = "at_time", active, expiresAt = "expires_at" }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        kind = (try? values.decode(String.self, forKey: .kind)) ?? "morning_brief"
        atTime = try values.decodeIfPresent(String.self, forKey: .atTime)
        active = (try? values.decode(Bool.self, forKey: .active)) ?? false
        expiresAt = try values.decodeIfPresent(String.self, forKey: .expiresAt)
    }
}

// MARK: - Reading / discovery / maps config

public struct ReadingThumbnail: Decodable, Sendable {
    public let url: String
    public let credit: String?
}

public struct ReadingArticle: Decodable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let url: String
    public let source: String?
    public let publishedAt: String?
    public let checkedAt: String?
    public let provenance: String?
    public let thumbnail: ReadingThumbnail?

    private enum CodingKeys: String, CodingKey {
        case id, title, url, source, publishedAt = "published_at", checkedAt = "checked_at", provenance, thumbnail
    }
}

public struct ReadingResponse: Decodable, Sendable {
    public let articles: [ReadingArticle]
    public let status: String
    public let topic: String?
    public let topics: [String]?
    public let reason: String?
    public let provenance: String?
    public let checkedAt: String?
    public let attribution: String?

    private enum CodingKeys: String, CodingKey {
        case articles, status, topic, topics, reason, provenance, checkedAt = "checked_at", attribution
    }
}

public struct RankRow: Decodable, Sendable {
    public let id: String
    public let score: Double?
    public let reason: String?
    public let position: Int?
}

/// `POST /api/discovery/places`: ranked live Google candidates.
public struct DiscoveryInput: Encodable, Sendable {
    public let sessionID: String
    public let category: String
    public let subcategory: String?
    public let lat: Double
    public let lng: Double
    public let radiusKm: Double
    public let openNow: Bool
    public let sort: String
    public let query: String?

    private enum CodingKeys: String, CodingKey {
        case sessionID = "session_id", category, subcategory, lat, lng, radiusKm = "radius_km",
             openNow = "open_now", sort, query
    }

    public init(sessionID: String = UUID().uuidString, category: String, subcategory: String? = nil, lat: Double = 25.0805, lng: Double = 55.1403, radiusKm: Double = 10, openNow: Bool = false, sort: String = "recommended", query: String? = nil) {
        self.sessionID = sessionID
        self.category = category
        self.subcategory = subcategory
        self.lat = lat
        self.lng = lng
        self.radiusKm = radiusKm
        self.openNow = openNow
        self.sort = sort
        self.query = query
    }
}

public struct DiscoveryResponse: Decodable, Sendable {
    public let places: [Place]
    public let asOf: String?
    public let attribution: String?
    public let sort: String?
    public let notice: String?

    private enum CodingKeys: String, CodingKey { case places, asOf = "as_of", attribution, sort, notice }
}

/// `GET /api/maps/config`: browser key for the interactive Google map.
/// The server Places key is never exposed; without a browser key there is no map.
public struct MapsConfig: Decodable, Sendable {
    public let key: String
    public let source: String?
}

// MARK: - Server-sent events (order stream, outbox stream)

/// Minimal SSE frame splitter shared by the order and message streams.
public enum SSEParser {
    public static func events(from data: Data) -> [String] {
        guard let text = String(data: data, encoding: .utf8) else { return [] }
        var payloads: [String] = []
        var current: [String] = []
        for line in text.components(separatedBy: "\n") {
            let stripped = line.hasSuffix("\r") ? String(line.dropLast()) : line
            if stripped.isEmpty {
                let joined = current.joined(separator: "\n")
                if !joined.isEmpty { payloads.append(joined) }
                current = []
            } else if stripped.hasPrefix("data:") {
                current.append(String(stripped.dropFirst(5)).trimmingCharacters(in: .init(charactersIn: " ")))
            }
        }
        let joined = current.joined(separator: "\n")
        if !joined.isEmpty { payloads.append(joined) }
        return payloads
    }
}

// MARK: - Community / feed / chat (untrusted content; provenance stays visible)

/// A person or demo persona reference attached to posts, comments and messages.
/// Display only: never turned into profile facts or assistant instructions.
public struct AuthorRef: Decodable, Sendable {
    public let name: String
    public let handle: String?
    public let emoji: String?
    public let personaID: String?
    public let avatar: String?

    private enum CodingKeys: String, CodingKey { case name, handle, emoji, personaID = "persona_id", avatar }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        name = (try? values.decode(String.self, forKey: .name)) ?? "Someone"
        handle = try values.decodeIfPresent(String.self, forKey: .handle)
        emoji = try values.decodeIfPresent(String.self, forKey: .emoji)
        personaID = try values.decodeIfPresent(String.self, forKey: .personaID)
        avatar = try values.decodeIfPresent(String.self, forKey: .avatar)
    }
}

public struct CommunityRef: Decodable, Sendable {
    public let id: String
    public let name: String
    public let handle: String?
    public let joined: Bool?

    private enum CodingKeys: String, CodingKey { case id, name, handle, joined }
}

public struct Community: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let handle: String?
    public let topic: String?
    public let about: String?
    public let image: String?
    public let members: Int?
    public let joined: Bool?
    public let provenance: String?
}

public struct CommunityList: Decodable, Sendable {
    public let communities: [Community]
}

public struct FeedPost: Decodable, Identifiable, Sendable {
    public let id: String
    public let community: CommunityRef?
    public let author: AuthorRef?
    public let mine: Bool?
    public let kind: String?
    public let text: String
    public let image: String?
    public let likes: Int?
    /// Number of comments on this post.
    public let comments: Int?
    public let createdAt: String?
    public let provenance: String?

    private enum CodingKeys: String, CodingKey {
        case id, community, author, mine, kind, text, image, likes, comments, createdAt = "created_at", provenance
    }
}

/// `/api/feed`: joined communities first, then discovery; hidden posts excluded.
public struct FeedResponse: Decodable, Sendable {
    public let posts: [FeedPost]
    public let stories: [StoryTray]
}

/// One entry in the stories rail: the latest story per community.
public struct StoryTray: Decodable, Sendable {
    public let community: CommunityRef
    public let author: AuthorRef?
    public let image: String?
    public let at: String?
    public let provenance: String?
}

/// One frame of `/api/communities/{id}/stories`.
public struct StoryFrame: Decodable, Identifiable, Sendable {
    public let id: String
    public let author: String
    public let emoji: String?
    public let text: String
    public let image: String?
    public let createdAt: String?
    public let provenance: String?

    private enum CodingKeys: String, CodingKey {
        case id, author, emoji, text, image, createdAt = "created_at", provenance
    }
}

public struct StoryFrames: Decodable, Sendable {
    public let community: CommunityRef
    public let frames: [StoryFrame]
}

public struct PostComment: Decodable, Identifiable, Sendable {
    public let id: String
    public let author: AuthorRef?
    public let text: String
    public let createdAt: String?
    public let likes: Int?
    public let provenance: String?
    public let mine: Bool?
    public let parentID: String?
    public let model: String?

    private enum CodingKeys: String, CodingKey {
        case id, author, text, createdAt = "created_at", likes, provenance, mine, parentID = "parent_id", model
    }
}

public struct CommentList: Decodable, Sendable {
    public let comments: [PostComment]
}

/// `POST /api/posts/{id}/hide` answers `{hidden: post_id}`.
public struct HiddenPost: Decodable, Sendable {
    public let hiddenPostID: String

    private enum CodingKeys: String, CodingKey { case hiddenPostID = "hidden" }
}

public struct SinglePost: Decodable, Sendable {
    public let post: FeedPost
}

/// Receipt for a posted text/comment/chat message. Backend-orchestrated persona
/// replies arrive as new records; this receipt never contains their content.
public struct SocialReceipt: Decodable, Sendable {
    public let id: String
    public let generation: GenerationStatus?

    public struct GenerationStatus: Decodable, Sendable {
        public let status: String?
        public let replyCount: Int?
        public let model: String?

        private enum CodingKeys: String, CodingKey { case status, replyCount = "reply_count", model }
    }
}

public struct ChatThread: Decodable, Identifiable, Sendable {
    public let id: String
    public let kind: String?
    public let title: String?
    public let communityID: String?
    public let last: String?
    public let lastAuthor: String?
    public let at: String?
    public let unread: Int?
    public let personaID: String?
    public let avatar: String?

    private enum CodingKeys: String, CodingKey {
        case id, kind, title, communityID = "community_id", last, lastAuthor = "last_author",
             at, unread, personaID = "persona_id", avatar
    }
}

public struct ChatList: Decodable, Sendable {
    public let threads: [ChatThread]
    public let unread: Int
}

public struct ChatThreadDetail: Decodable, Sendable {
    public let id: String
    public let kind: String?
    public let title: String?
    public let communityID: String?

    private enum CodingKeys: String, CodingKey { case id, kind, title, communityID = "community_id" }
}

public struct ChatMessage: Decodable, Identifiable, Sendable {
    public let id: String
    public let author: String?
    public let mine: Bool?
    public let text: String
    public let at: String?
    public let provenance: String?
    public let personaID: String?
    public let avatar: String?
    public let model: String?

    private enum CodingKeys: String, CodingKey {
        case id, author, mine, text, at, provenance, personaID = "persona_id", avatar, model
    }
}

public struct ChatMessages: Decodable, Sendable {
    public let thread: ChatThreadDetail?
    public let messages: [ChatMessage]
}

public struct Contact: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let phone: String
    public let createdAt: String?

    private enum CodingKeys: String, CodingKey { case id, name, phone, createdAt = "created_at" }
}

public struct ContactList: Decodable, Sendable {
    public let contacts: [Contact]
}

public struct DeletedRef: Decodable, Sendable {
    public let deleted: String
}

/// One entry of the in-app call log: calls the user started from Dubai-io.
/// The phone's dialer places the call; nothing here implies a connection.
public struct CallEntry: Decodable, Identifiable, Sendable {
    public let id: String
    public let contactID: String?
    public let name: String?
    public let phone: String?
    public let at: String?
    public let source: String?

    private enum CodingKeys: String, CodingKey {
        case id, contactID = "contact_id", name, phone, at, source
    }
}

public struct CallList: Decodable, Sendable {
    public let calls: [CallEntry]
}

/// `POST /api/calls` answers the dialer handoff, never a connection claim.
public struct CallHandoff: Decodable, Sendable {
    public let tel: String
}

public enum MapCategory: String, CaseIterable, Identifiable, Sendable {
    case all, pets, food, coffee, barber, homeHelp = "home-help", laundry, clothing, fixIt = "fix-it"
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .all: "All"
        case .pets: "Pets"
        case .food: "Food"
        case .coffee: "Coffee"
        case .barber: "Barber"
        case .homeHelp: "Home help"
        case .laundry: "Laundry"
        case .clothing: "Clothing"
        case .fixIt: "Fix it"
        }
    }
    public var symbol: String {
        switch self {
        case .all: "square.grid.2x2"
        case .pets: "pawprint"
        case .food: "fork.knife"
        case .coffee: "cup.and.saucer"
        case .barber: "scissors"
        case .homeHelp: "house"
        case .laundry: "drop"
        case .clothing: "bag"
        case .fixIt: "wrench.and.screwdriver"
        }
    }
    public var options: [String] {
        switch self {
        case .pets: ["Vet", "24h", "Pet shop", "Boarding", "Grooming", "Photo"]
        case .food: ["Restaurants", "Delivery"]
        case .homeHelp: ["Maid", "Cleaning", "Visa services"]
        case .fixIt: ["AC", "Plumbing", "Electrical"]
        default: []
        }
    }
    public func searchQuery(option: String?, area: String) -> String {
        let term: String
        if self == .pets {
            term = switch option {
            case "24h": "24-hour veterinary clinic"
            case "Vet": "veterinary clinic"
            case "Boarding": "pet boarding"
            case "Grooming": "pet grooming"
            case "Photo": "pet photography"
            default: "pet shops"
            }
        } else if let option {
            term = self == .fixIt && option == "AC" ? "air conditioning repair" : option
        } else {
            term = switch self {
            case .all: "popular places"
            case .food: "restaurants"
            case .homeHelp: "home cleaning services"
            case .fixIt: "home repair services"
            default: label
            }
        }
        return "\(term) near \(area)"
    }
}
