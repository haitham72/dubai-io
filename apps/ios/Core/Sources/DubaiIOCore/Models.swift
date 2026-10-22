import Foundation

public struct SessionInfo: Decodable, Sendable {
    public let userId: String
    public let mode: String
}

public struct Health: Decodable, Sendable {
    public let ok: Bool
    public let openaiKey: Bool
    public let googleKey: Bool
}

public struct Catalog: Decodable, Sendable {
    public let provenance: String
    public let asOf: String
    public let providers: [Provider]
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

    private enum CodingKeys: String, CodingKey { case id, name, priceAed }

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
}

public struct PlaceResults: Decodable, Sendable {
    public let places: [Place]
    public let attribution: String
    public let asOf: String
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
}

public struct ResearchSource: Decodable, Identifiable, Sendable {
    public var id: String { url }
    public let title: String
    public let url: String
    public let asOf: String?
}

public struct Product: Decodable, Identifiable, Sendable {
    public var id: String { link }
    public let title: String
    public let link: String
    public let price: String?
    public let thumbnail: String?
    public let asOf: String?
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
    public let snapshotHash: String?
    public let amountAed: Double?
    public let earlierTarget: String?

    private enum CodingKeys: String, CodingKey {
        case kind, title, detail, actionID = "actionId", revision, snapshotHash, amountAed, earlierTarget
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        kind = try values.decode(String.self, forKey: .kind)
        title = try values.decode(String.self, forKey: .title)
        detail = try values.decodeIfPresent(String.self, forKey: .detail)
        actionID = try values.decode(String.self, forKey: .actionID)
        revision = try values.decode(Int.self, forKey: .revision)
        snapshotHash = try values.decodeIfPresent(String.self, forKey: .snapshotHash)
        amountAed = try decodeMoney(values, key: .amountAed)
        earlierTarget = try values.decodeIfPresent(String.self, forKey: .earlierTarget)
    }
}

public struct TodayTask: Decodable, Sendable {
    public let id: String
    public let title: String
    public let lane: String?
    public let status: String?
    public let revision: Int
    public let checkBackAt: String?
    public let decision: TaskDecision?
}

public struct TodayCounts: Decodable, Sendable {
    public let needsYou: Int
    public let running: Int
    public let onList: Int
    public let paused: Int
}

public struct TodayLane: Decodable, Sendable {
    public let tasks: [TodayTask]
}

public struct TodaySnapshot: Decodable, Sendable {
    public let needsYou: TodayLane
    public let scheduled: TodayLane?
    public let counts: TodayCounts
}

public struct TaskDetail: Decodable, Sendable {
    public let id: String
    public let title: String
    public let status: String
    public let revision: Int
    public let lane: String?
    public let checkBackAt: String?
}

public struct TaskList: Decodable, Sendable {
    public let tasks: [TaskDetail]
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

public struct ActionDetail: Decodable, Sendable {
    public let id: String
    public let title: String
    public let revision: Int
    public let snapshotHash: String?
    public let amountAed: Double?
    public let context: String?
    public let note: String?
    public let sharedFields: [String]?
    public let status: String

    private enum CodingKeys: String, CodingKey {
        case id, title, revision, snapshotHash, amountAed, context, note, sharedFields, status
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decode(String.self, forKey: .id)
        title = try values.decode(String.self, forKey: .title)
        revision = try values.decode(Int.self, forKey: .revision)
        snapshotHash = try values.decodeIfPresent(String.self, forKey: .snapshotHash)
        amountAed = try decodeMoney(values, key: .amountAed)
        context = try values.decodeIfPresent(String.self, forKey: .context)
        note = try values.decodeIfPresent(String.self, forKey: .note)
        sharedFields = try values.decodeIfPresent([String].self, forKey: .sharedFields)
        status = (try? values.decodeIfPresent(String.self, forKey: .status)) ?? "unknown"
    }
}

public struct Reminder: Decodable, Sendable {
    public let id: String
    public let taskID: String?
    public let checkBackAt: String?
    public let text: String?

    private enum CodingKeys: String, CodingKey {
        case id, taskID = "taskId", checkBackAt, text
    }
}

public struct ReminderList: Decodable, Sendable {
    public let reminders: [Reminder]
}

// MARK: - Outbox messages / follow-up mode / brief (deterministic, never model text)

public struct OutboxMessage: Decodable, Sendable {
    public let id: String
    public let kind: String
    public let text: String?
    public let taskID: String?
    public let dedupeKey: String?
    public let createdAt: String?

    private enum CodingKeys: String, CodingKey {
        case id, kind, text, taskID = "taskId", dedupeKey, createdAt
    }
}

public struct OutboxList: Decodable, Sendable {
    public let messages: [OutboxMessage]
}

public struct AssistState: Decodable, Sendable {
    public let mode: String
    public let offerAuto: Bool?
}

public struct BriefLine: Decodable, Sendable {
    public let chip: String
    public let text: String
}

public struct Brief: Decodable, Sendable {
    public let moving: Int
    public let needsYou: Int
    public let lines: [BriefLine]
}

// MARK: - Community / feed / chat (untrusted content; provenance stays visible)

public struct Community: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let memberCount: Int?
    public let joined: Bool?
    public let provenance: String?
}

public struct CommunityList: Decodable, Sendable {
    public let communities: [Community]
}

public struct FeedPost: Decodable, Identifiable, Sendable {
    public let id: String
    public let communityID: String?
    public let author: String?
    public let body: String
    public let provenance: String?
    public let asOf: String?
    public let commentCount: Int?

    private enum CodingKeys: String, CodingKey {
        case id, communityID = "communityId", author, body, provenance, asOf, commentCount
    }
}

public struct FeedList: Decodable, Sendable {
    public let posts: [FeedPost]
}

public struct PostComment: Decodable, Identifiable, Sendable {
    public let id: String
    public let author: String?
    public let body: String
    public let provenance: String?
}

public struct CommentList: Decodable, Sendable {
    public let comments: [PostComment]
}

public struct HiddenPost: Decodable, Sendable {
    public let id: String
    public let hidden: Bool
}

public struct ChatThread: Decodable, Identifiable, Sendable {
    public let id: String
    public let title: String?
    public let unread: Bool?
    public let lastMessage: String?
}

public struct ChatList: Decodable, Sendable {
    public let chats: [ChatThread]
}

public struct ChatMessage: Decodable, Identifiable, Sendable {
    public let id: String
    public let sender: String?
    public let body: String
    public let createdAt: String?
}

public struct ChatMessages: Decodable, Sendable {
    public let messages: [ChatMessage]
}

public struct Contact: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let phone: String?
}

public struct ContactList: Decodable, Sendable {
    public let contacts: [Contact]
}

public struct CallEntry: Decodable, Identifiable, Sendable {
    public let id: String
    public let contact: String?
    public let direction: String?
    public let startedAt: String?
    public let durationS: Int?
}

public struct CallList: Decodable, Sendable {
    public let calls: [CallEntry]
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
