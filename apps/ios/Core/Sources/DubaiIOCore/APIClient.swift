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
        let parts = host.split(separator: ".")
        guard parts.count == 4 else { return false }
        let octets = parts.compactMap { Int($0) }
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

    // MARK: - Today / tasks (plan FIN-08)

    public func today() async throws -> TodaySnapshot {
        _ = try await connect()
        return try await request("api/today")
    }

    public func lane(_ lane: String) async throws -> TodayLane {
        _ = try await connect()
        return try await request("api/today/lanes/\(lane)")
    }

    public func tasks() async throws -> TaskList {
        _ = try await connect()
        return try await request("api/tasks")
    }

    /// `GET /api/tasks/{id}` answers `{task, linked_item, ...activity}`; only `task` is modelled.
    public func task(id: String) async throws -> TaskResponse {
        _ = try await connect()
        return try await request("api/tasks/\(id)")
    }

    public func sendCommand(_ command: TaskCommand, taskID: String) async throws -> TaskResponse {
        _ = try await connect()
        return try await request(
            "api/tasks/\(taskID)/commands", body: JSONEncoder().encode(command))
    }

    /// Not-now / keep-on-Today for a decision: tracks the action's task.
    public func taskFromAction(actionID: String) async throws -> TaskResponse {
        _ = try await connect()
        struct Input: Encodable { let action_id: String }
        return try await request(
            "api/tasks/from-action", body: JSONEncoder().encode(Input(action_id: actionID)))
    }

    // MARK: - Decisions / orders

    public func action(id: String) async throws -> ActionDetail {
        _ = try await connect()
        return try await request("api/actions/\(id)")
    }

    public func prepareAction(_ input: PrepareInput) async throws -> ActionDetail {
        _ = try await connect()
        return try await request("api/actions/prepare", body: JSONEncoder().encode(input))
    }

    public func approveAction(
        id: String, revision: Int, snapshotHash: String, idempotencyKey: String
    ) async throws -> ActionDetail {
        _ = try await connect()
        struct Input: Encodable { let snapshot_hash: String; let revision: Int }
        return try await request(
            "api/actions/\(id)/approve",
            headers: ["Idempotency-Key": idempotencyKey],
            body: JSONEncoder().encode(Input(snapshot_hash: snapshotHash, revision: revision)))
    }

    public func cancelAction(id: String) async throws -> ActionDetail {
        _ = try await connect()
        return try await request("api/actions/\(id)/cancel", method: "POST")
    }

    public func requestEarlier(id: String, target: String) async throws -> ActionDetail {
        _ = try await connect()
        struct Input: Encodable { let target: String }
        return try await request(
            "api/actions/\(id)/request-earlier", body: JSONEncoder().encode(Input(target: target)))
    }

    /// SSE change feed for one action; the App layer reads it with `SSEStream`.
    /// A 409 from the shown revision means reload — approving a stale revision is refused.
    public nonisolated func actionStreamRequest(id: String) -> URLRequest {
        var request = URLRequest(url: address.endpoint("api/actions/\(id)/stream"))
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        return request
    }

    /// `POST /api/reminders` ("Remind me when it's ready"); the tap is the consent.
    public func remindWhenReady(actionID: String) async throws -> ReadyReminder {
        _ = try await connect()
        struct Input: Encodable { let action_id: String }
        return try await request(
            "api/reminders", body: JSONEncoder().encode(Input(action_id: actionID)))
    }

    // MARK: - Outbox / follow-up mode / morning brief

    public func messages() async throws -> OutboxList {
        _ = try await connect()
        return try await request("api/messages")
    }

    public func assist() async throws -> AssistState {
        _ = try await connect()
        return try await request("api/assist")
    }

    public func updateAssist(mode: String, dismissOffer: Bool = false) async throws -> AssistState {
        _ = try await connect()
        struct Input: Encodable { let mode: String; let dismiss_offer: Bool }
        return try await request(
            "api/assist", method: "PUT", body: JSONEncoder().encode(Input(mode: mode, dismiss_offer: dismissOffer)))
    }

    public func briefRoutine() async throws -> BriefRoutine {
        _ = try await connect()
        return try await request("api/routines/brief")
    }

    public func updateBriefRoutine(active: Bool, atTime: String = "08:00") async throws -> BriefRoutine {
        _ = try await connect()
        struct Input: Encodable { let active: Bool; let at_time: String }
        return try await request(
            "api/routines/brief", method: "PUT", body: JSONEncoder().encode(Input(active: active, at_time: atTime)))
    }

    // MARK: - Community / feed / stories / chat

    public func communities() async throws -> CommunityList {
        _ = try await connect()
        return try await request("api/communities")
    }

    /// Join/leave answer the full community list; joining carries through to Chat.
    public func joinCommunity(id: String) async throws -> CommunityList {
        _ = try await connect()
        return try await request("api/communities/\(id)/join", method: "POST")
    }

    public func leaveCommunity(id: String) async throws -> CommunityList {
        _ = try await connect()
        return try await request("api/communities/\(id)/leave", method: "POST")
    }

    public func communityPosts(id: String) async throws -> FeedResponse {
        _ = try await connect()
        return try await request("api/communities/\(id)/posts")
    }

    public func feed() async throws -> FeedResponse {
        _ = try await connect()
        return try await request("api/feed")
    }

    public func stories(communityID: String) async throws -> StoryFrames {
        _ = try await connect()
        return try await request("api/communities/\(communityID)/stories")
    }

    public func post(id: String) async throws -> SinglePost {
        _ = try await connect()
        return try await request("api/posts/\(id)")
    }

    public func createPost(communityID: String, text: String, requestID: String = UUID().uuidString) async throws -> SocialReceipt {
        _ = try await connect()
        struct Input: Encodable { let text: String; let request_id: String }
        return try await request(
            "api/communities/\(communityID)/posts",
            body: JSONEncoder().encode(Input(text: text, request_id: requestID)))
    }

    public func comments(postID: String) async throws -> CommentList {
        _ = try await connect()
        return try await request("api/posts/\(postID)/comments")
    }

    public func addComment(postID: String, text: String, parentID: String? = nil, requestID: String = UUID().uuidString) async throws -> SocialReceipt {
        _ = try await connect()
        struct Input: Encodable { let text: String; let parent_id: String?; let request_id: String }
        return try await request(
            "api/posts/\(postID)/comments",
            body: JSONEncoder().encode(Input(text: text, parent_id: parentID, request_id: requestID)))
    }

    public func hidePost(postID: String, reason: String? = nil) async throws -> HiddenPost {
        _ = try await connect()
        struct Input: Encodable { let reason: String? }
        return try await request(
            "api/posts/\(postID)/hide", method: "POST", body: JSONEncoder().encode(Input(reason: reason)))
    }

    public func chats(filter: String = "all") async throws -> ChatList {
        _ = try await connect()
        let valid = ["all", "unread", "groups", "communities"].contains(filter) ? filter : "all"
        var components = URLComponents(url: address.endpoint("api/chats"), resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "filter", value: valid)]
        return try await request(url: components.url!)
    }

    public func chatMessages(id: String) async throws -> ChatMessages {
        _ = try await connect()
        return try await request("api/chats/\(id)/messages")
    }

    public func sendChatMessage(threadID: String, text: String, requestID: String = UUID().uuidString) async throws -> SocialReceipt {
        _ = try await connect()
        struct Input: Encodable { let text: String; let request_id: String }
        return try await request(
            "api/chats/\(threadID)/messages",
            body: JSONEncoder().encode(Input(text: text, request_id: requestID)))
    }

    public func contacts() async throws -> ContactList {
        _ = try await connect()
        return try await request("api/contacts")
    }

    public func addContact(name: String, phone: String) async throws -> Contact {
        _ = try await connect()
        struct Input: Encodable { let name: String; let phone: String }
        return try await request(
            "api/contacts", body: JSONEncoder().encode(Input(name: name, phone: phone)))
    }

    public func deleteContact(id: String) async throws -> DeletedRef {
        _ = try await connect()
        return try await request("api/contacts/\(id)", method: "DELETE")
    }

    public func calls() async throws -> CallList {
        _ = try await connect()
        return try await request("api/calls")
    }

    /// Logs that the user started a call; answers the `tel:` handoff. Never a connection claim.
    public func logCall(contactID: String) async throws -> CallHandoff {
        _ = try await connect()
        struct Input: Encodable { let contact_id: String }
        return try await request(
            "api/calls", body: JSONEncoder().encode(Input(contact_id: contactID)))
    }

    public func clearCalls() async throws -> DeletedRef {
        _ = try await connect()
        struct Input: Decodable { let cleared: Bool }
        let answer: Input = try await request("api/calls", method: "DELETE")
        return DeletedRef(deleted: answer.cleared ? "cleared" : "")
    }

    // MARK: - Reading / discovery / maps config

    public func reading(topic: String = "for_you") async throws -> ReadingResponse {
        _ = try await connect()
        var components = URLComponents(url: address.endpoint("api/reading"), resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "topic", value: topic)]
        return try await request(url: components.url!)
    }

    public func discover(_ input: DiscoveryInput) async throws -> DiscoveryResponse {
        _ = try await connect()
        return try await request("api/discovery/places", body: JSONEncoder().encode(input))
    }

    public func mapsConfig() async throws -> MapsConfig {
        _ = try await connect()
        return try await request("api/maps/config")
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

    private func request<Output: Decodable & Sendable>(
        _ path: String, method: String? = nil, headers: [String: String] = [:], body: Data? = nil
    ) async throws -> Output {
        try await request(url: address.endpoint(path), method: method, headers: headers, body: body)
    }

    private func request<Output: Decodable & Sendable>(
        url: URL, method: String? = nil, headers: [String: String] = [:], body: Data? = nil
    ) async throws -> Output {
        try Task.checkCancellation()
        var request = URLRequest(url: url)
        request.httpMethod = method ?? (body == nil ? "GET" : "POST")
        for (field, value) in headers { request.setValue(value, forHTTPHeaderField: field) }
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
        // Explicit snake_case CodingKeys on every multi-word type; no key
        // strategy, so a key mismatch fails loudly instead of decoding nil.
        do { return try decoder.decode(Output.self, from: data) }
        catch { throw APIError.invalidResponse }
    }
}
