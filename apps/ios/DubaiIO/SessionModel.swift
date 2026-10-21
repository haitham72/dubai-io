import DubaiIOCore
import Foundation
import Observation

@MainActor @Observable
final class SessionModel {
    var baseAddress: String
    private(set) var client: APIClient?
    private(set) var info: SessionInfo?
    private(set) var health: Health?
    private(set) var revision = UUID()
    private(set) var isConnecting = false
    var error: String?

    init() {
        baseAddress = UserDefaults.standard.string(forKey: "apiAddress") ?? ""
    }

    func connect(to value: String) async {
        guard !isConnecting else { return }
        isConnecting = true
        defer { isConnecting = false }
        error = nil
        do {
            #if DEBUG
            let address = try BackendAddress(value, allowLocalHTTP: true)
            #else
            let address = try BackendAddress(value)
            #endif
            let candidate = APIClient(address: address)
            let identity = try await candidate.connect()
            let health = try await candidate.health()
            if baseAddress != address.url.absoluteString || info?.userId != identity.userId { revision = UUID() }
            baseAddress = address.url.absoluteString
            UserDefaults.standard.set(baseAddress, forKey: "apiAddress")
            client = candidate
            info = identity
            self.health = health
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct ChatEntry: Identifiable {
    let id = UUID()
    let isUser: Bool
    let text: String
    var reply: LunaReply?
}

@MainActor @Observable
final class ChatModel {
    var draft = ""
    private(set) var entries: [ChatEntry] = []
    private(set) var isSending = false
    var error: String?
    private var threadID = UUID().uuidString
    private var generation = UUID()

    func reset() {
        generation = UUID()
        threadID = UUID().uuidString
        entries = []
        error = nil
        isSending = false
    }

    func send(using client: APIClient?) async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !isSending, !text.isEmpty else { return }
        guard let client else { error = "Connect your API in Me first."; return }
        let currentGeneration = generation
        isSending = true
        error = nil
        draft = ""
        entries.append(ChatEntry(isUser: true, text: text))
        defer { if generation == currentGeneration { isSending = false } }
        do {
            let reply = try await client.turn(text: text, threadID: threadID)
            guard generation == currentGeneration else { return }
            entries.append(ChatEntry(isUser: false, text: reply.displayText, reply: reply))
        } catch {
            guard generation == currentGeneration else { return }
            self.error = error.localizedDescription
            if draft.isEmpty { draft = text }
        }
    }
}
