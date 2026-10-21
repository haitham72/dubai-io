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
        let price = (try? values.decode(Double.self, forKey: .priceAed))
            ?? Double(try values.decode(String.self, forKey: .priceAed))
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
