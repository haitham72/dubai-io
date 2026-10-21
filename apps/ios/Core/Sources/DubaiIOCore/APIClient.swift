import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

private struct APIErrorBody: Decodable { let detail: String }

public enum APIError: Error, LocalizedError, Equatable, Sendable {
    case invalidBackend
    case invalidResponse
    case http(Int, String)

    public var errorDescription: String? {
        switch self {
        case .invalidBackend: "Enter an HTTPS API address, or a local development address."
        case .invalidResponse: "The server returned a response this app could not read."
        case .http(let code, let message): "\(message) (\(code))"
        }
    }
}

public struct BackendAddress: Sendable {
    public let url: URL

    public init(_ value: String, allowLocalHTTP: Bool = false) throws {
        guard var components = URLComponents(string: value.trimmingCharacters(in: .whitespacesAndNewlines)),
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil,
              components.query == nil, components.fragment == nil,
              components.path.isEmpty || components.path == "/",
              components.port.map({ (1...65535).contains($0) }) ?? true,
              components.scheme == "https" || (allowLocalHTTP && components.scheme == "http" && Self.isLocal(host))
        else { throw APIError.invalidBackend }
        components.path = ""
        guard let url = components.url else { throw APIError.invalidBackend }
        self.url = url
    }

    private static func isLocal(_ host: String) -> Bool {
        if ["localhost", "127.0.0.1", "::1", "[::1]"].contains(host.lowercased()) || host.lowercased().hasSuffix(".local") { return true }
        let octets = host.split(separator: ".").compactMap { Int($0) }
        guard octets.count == 4, octets.allSatisfy({ (0...255).contains($0) }) else { return false }
        return octets[0] == 10 || (octets[0] == 192 && octets[1] == 168) || (octets[0] == 172 && (16...31).contains(octets[1]))
    }

    public func endpoint(_ path: String, query: [URLQueryItem] = []) -> URL {
        var components = URLComponents(url: url.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty { components.queryItems = query }
        return components.url!
    }
}

public enum WebLink {
    public static func url(_ value: String) -> URL? {
        guard let components = URLComponents(string: value),
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil,
              ["https", "http"].contains(components.scheme?.lowercased() ?? "") else { return nil }
        return components.url
    }
}

public protocol HTTPTransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

public struct URLSessionTransport: HTTPTransport {
    private let session: URLSession

    public init() {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 35
        configuration.timeoutIntervalForResource = 60
        configuration.httpShouldSetCookies = true
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        session = URLSession(configuration: configuration)
    }

    public func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        return (data, response)
    }
}

public actor APIClient {
    public nonisolated let address: BackendAddress
    private let transport: any HTTPTransport
    private var identity: SessionInfo?
    private var openingSession: Task<SessionInfo, Error>?

    public init(address: BackendAddress, transport: any HTTPTransport = URLSessionTransport()) {
        self.address = address
        self.transport = transport
    }

    public func connect() async throws -> SessionInfo {
        if let identity { return identity }
        if let openingSession { return try await openingSession.value }
        let task = Task<SessionInfo, Error> { try await self.request("api/session") }
        openingSession = task
        do {
            let result = try await task.value
            identity = result
            openingSession = nil
            return result
        } catch {
            openingSession = nil
            throw error
        }
    }

    public func health() async throws -> Health { try await request("api/health") }
    public func catalog() async throws -> Catalog { try await request("api/catalog") }

    public func memory() async throws -> SavedMemory {
        _ = try await connect()
        return try await request("api/session/memory")
    }

    public func connections() async throws -> Connections {
        _ = try await connect()
        return try await request("api/auth/connections")
    }

    public func turn(text: String, threadID: String) async throws -> LunaReply {
        _ = try await connect()
        struct Input: Encodable { let text: String; let thread_id: String }
        return try await request("api/luna/turn", body: JSONEncoder().encode(Input(text: text, thread_id: threadID)))
    }

    public func places(query: String) async throws -> PlaceResults {
        struct Input: Encodable { let query: String }
        return try await request("api/places/search", body: JSONEncoder().encode(Input(query: query)))
    }

    public nonisolated func mapURL(places: [Place], center: (Double, Double) = (25.0805, 55.1403)) -> URL {
        let pins = places.prefix(9).compactMap { place -> String? in
            guard let lat = place.lat, let lng = place.lng else { return nil }
            return "\(lat),\(lng)"
        }.joined(separator: "|")
        return address.endpoint("api/staticmap", query: [
            URLQueryItem(name: "c", value: "\(center.0),\(center.1)"),
            URLQueryItem(name: "m", value: pins), URLQueryItem(name: "s", value: "wide")
        ])
    }

    private func request<Output: Decodable & Sendable>(_ path: String, body: Data? = nil) async throws -> Output {
        try Task.checkCancellation()
        var request = URLRequest(url: address.endpoint(path))
        request.httpMethod = body == nil ? "GET" : "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await transport.data(for: request)
        try Task.checkCancellation()
        guard (200..<300).contains(response.statusCode) else {
            let message = (try? JSONDecoder().decode(APIErrorBody.self, from: data).detail) ?? "The request did not complete. Try again."
            throw APIError.http(response.statusCode, String(message.prefix(300)))
        }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        do { return try decoder.decode(Output.self, from: data) }
        catch { throw APIError.invalidResponse }
    }
}
