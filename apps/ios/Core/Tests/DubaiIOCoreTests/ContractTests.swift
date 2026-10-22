import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import Testing
@testable import DubaiIOCore

private actor StubTransport: HTTPTransport {
    private var replies: [(Int, String)]
    private var requests: [URLRequest] = []
    init(_ replies: [(Int, String)]) { self.replies = replies }
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        requests.append(request)
        let (status, json) = replies.removeFirst()
        return (Data(json.utf8), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
    func recorded() -> [URLRequest] { requests }
}

@Test func backendRejectsPublicHTTPAndCredentials() throws {
    #expect(throws: APIError.invalidBackend) { try BackendAddress("http://example.com", allowLocalHTTP: true) }
    #expect(throws: APIError.invalidBackend) { try BackendAddress("https://user:secret@example.com") }
    #expect(throws: APIError.invalidBackend) { try BackendAddress("https://example.com?token=secret") }
    #expect(throws: APIError.invalidBackend) { try BackendAddress("http://10.1.2.3") }
    #expect(throws: APIError.invalidBackend) { try BackendAddress("http://10.bad.1.2.3", allowLocalHTTP: true) }
    #expect(try BackendAddress("http://192.168.1.10:8000", allowLocalHTTP: true).url.host == "192.168.1.10")
}

@Test func linksCannotLaunchScriptsOrSendCredentials() {
    #expect(WebLink.url("javascript:alert(1)") == nil)
    #expect(WebLink.url("file:///private/file") == nil)
    #expect(WebLink.url("https://user:secret@example.com") == nil)
    #expect(WebLink.url("https://www.amazon.ae/dp/example")?.host == "www.amazon.ae")
}

@Test func sessionPrecedesOwnerScopedChatAndCannotSpoofOwner() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"cookie-owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"intent":"greeting","confidence":1,"reply":"Hello","via":"langgraph"}"#),
        (200, #"{"told":[]}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let reply = try await client.turn(text: "Hello", threadID: "thread-1")
    #expect(reply.displayText == "Hello")
    _ = try await client.memory()
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == ["/api/session", "/api/luna/turn", "/api/session/memory"])
    let body = try #require(requests[1].httpBody)
    let json = try #require(JSONSerialization.jsonObject(with: body) as? [String: String])
    #expect(json == ["text": "Hello", "thread_id": "thread-1"])
}

@Test func rejectedSessionDoesNotSendChat() async throws {
    let transport = StubTransport([(503, #"{"detail":"Database unavailable"}"#)])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    await #expect(throws: APIError.http(503, "Database unavailable")) {
        try await client.turn(text: "Hello", threadID: "thread")
    }
    #expect(await transport.recorded().count == 1)
}

@Test func catalogAndPlacesDecodeActualSnakeCaseContracts() async throws {
    let transport = StubTransport([
        (200, #"{"provenance":"demo_fixture","as_of":"2026-10-21","providers":[{"id":"laundry","name":"Demo laundry","service":"laundry","items":[{"id":"shirt","name":"Shirt","price_aed":"6"}],"slots":["Tomorrow 08:30"]}]}"#),
        (200, #"{"attribution":"Google","as_of":"2026-10-21","places":[{"id":"place","name":"Cafe","lat":25.08,"lng":55.14,"open_now":false,"maps_url":"https://maps.google.com/","photo_by":["Photographer"]}]}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let catalog = try await client.catalog()
    #expect(catalog.providers.first?.items.first?.priceAed == 6)
    let results = try await client.places(query: "coffee")
    #expect(results.places.first?.openNow == false)
    #expect(results.places.first?.photoBy == ["Photographer"])
    let map = client.mapURL(places: results.places)
    #expect(URLComponents(url: map, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == "m" })?.value == "25.08,55.14")
}

@Test func petOptionsRetainTheirCategoryContext() {
    #expect(MapCategory.pets.searchQuery(option: "24h", area: "Dubai Marina") == "24-hour veterinary clinic near Dubai Marina")
    #expect(MapCategory.pets.searchQuery(option: "Boarding", area: "Deira") == "pet boarding near Deira")
}

@Test func todayDecodesNeedsYouDecisionCountsAndCheckback() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"needs_you":{"tasks":[{"id":"task-1","title":"Confirm taxi receipt","lane":"needs_you","status":"running","revision":3,"decision":{"kind":"approve","title":"Share receipt with driver","detail":"Trip total AED 42","action_id":"action-7","revision":2,"snapshot_hash":"abc123","amount_aed":"42"}}]},"scheduled":{"tasks":[{"id":"task-2","title":"Check back on visa renewal","lane":"scheduled","status":"paused","revision":1,"check_back_at":"2026-10-24T09:00:00Z"}]},"counts":{"needs_you":1,"running":2,"on_list":0,"paused":1}}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let snapshot = try await client.today()
    let decision = try #require(snapshot.needsYou.tasks.first?.decision)
    #expect(decision.kind == "approve")
    #expect(decision.actionID == "action-7")
    #expect(decision.revision == 2)
    #expect(decision.snapshotHash == "abc123")
    #expect(decision.amountAed == 42)
    #expect(snapshot.counts.needsYou == 1 && snapshot.counts.running == 2)
    #expect(snapshot.counts.onList == 0 && snapshot.counts.paused == 1)
    #expect(snapshot.scheduled?.tasks.first?.checkBackAt == "2026-10-24T09:00:00Z")
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == ["/api/session", "/api/today"])
}

@Test func taskCommandAlwaysSendsRevisionAndCommandKey() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"id":"task-1","title":"Confirm taxi receipt","status":"running","revision":4}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let updated = try await client.sendCommand(
        TaskCommand(kind: "check_back", expectedRevision: 3, commandKey: "key-1", at: "2026-10-24T09:00:00Z"),
        taskID: "task-1")
    #expect(updated.revision == 4)
    let requests = await transport.recorded()
    #expect(requests[1].url!.path == "/api/tasks/task-1/commands")
    #expect(requests[1].httpMethod == "POST")
    let json = try #require(JSONSerialization.jsonObject(with: requests[1].httpBody!) as? [String: Any])
    #expect(json["kind"] as? String == "check_back")
    #expect(json["expected_revision"] as? Int == 3)
    #expect(json["command_key"] as? String == "key-1")
    #expect(json["at"] as? String == "2026-10-24T09:00:00Z")
}

@Test func decisionApproveSendsExactRevisionAndSurfacesConflict() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"id":"action-7","title":"Share receipt with driver","revision":2,"snapshot_hash":"abc123","amount_aed":42,"context":"Taxi receipt","note":"Only the total is shared","shared_fields":["total_aed"],"status":"awaiting_approval"}"#),
        (200, #"{"id":"action-7","title":"Share receipt with driver","revision":2,"snapshot_hash":"abc123","amount_aed":42,"context":"Taxi receipt","note":"Only the total is shared","shared_fields":["total_aed"],"status":"approved"}"#),
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (409, #"{"detail":"Revision mismatch; reload the decision"}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let action = try await client.action(id: "action-7")
    #expect(action.snapshotHash == "abc123")
    #expect(action.sharedFields == ["total_aed"])
    let approved = try await client.approveAction(
        id: action.id, revision: action.revision,
        snapshotHash: action.snapshotHash ?? "", idempotencyKey: "idem-1")
    _ = approved
    let requests = await transport.recorded()
    #expect(requests[1].url!.path == "/api/actions/action-7")
    #expect(requests[2].url!.path == "/api/actions/action-7/approve")
    #expect(requests[2].value(forHTTPHeaderField: "Idempotency-Key") == "idem-1")
    let json = try #require(JSONSerialization.jsonObject(with: requests[2].httpBody!) as? [String: Any])
    #expect(json["revision"] as? Int == 2)
    #expect(json["snapshot_hash"] as? String == "abc123")
    let stale = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    await #expect(throws: APIError.http(409, "Revision mismatch; reload the decision")) {
        try await stale.approveAction(id: "action-7", revision: 1, snapshotHash: "old", idempotencyKey: "idem-2")
    }
}

@Test func outboxAssistAndBriefDecodeDeterministicContracts() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"messages":[{"id":"msg-1","kind":"task_checkback","text":"Check back: visa renewal","task_id":"task-2","dedupe_key":"checkback:task-2:1","created_at":"2026-10-23T09:00:00Z"}]}"#),
        (200, #"{"mode":"learn","offer_auto":true}"#),
        (200, #"{"mode":"auto","offer_auto":false}"#),
        (200, #"{"moving":2,"needs_you":1,"lines":[{"chip":"Needs you","text":"Confirm taxi receipt"},{"chip":"Moving","text":"Visa renewal paused"}]}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let outbox = try await client.messages()
    #expect(outbox.messages.first?.taskID == "task-2")
    #expect(outbox.messages.first?.dedupeKey == "checkback:task-2:1")
    let assist = try await client.assist()
    #expect(assist.mode == "learn" && assist.offerAuto == true)
    let updated = try await client.updateAssist(mode: "auto")
    #expect(updated.mode == "auto")
    let brief = try await client.brief()
    #expect(brief.moving == 2 && brief.needsYou == 1)
    #expect(brief.lines.first?.chip == "Needs you")
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == ["/api/session", "/api/messages", "/api/assist", "/api/assist", "/api/routines/brief"])
    #expect(requests[3].httpMethod == "PUT")
    let json = try #require(JSONSerialization.jsonObject(with: requests[3].httpBody!) as? [String: String])
    #expect(json == ["mode": "auto"])
}

@Test func communityFeedAndChatKeepProvenanceAndUntrustedBodies() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"communities":[{"id":"com-1","name":"Marina runners","member_count":120,"joined":false,"provenance":"demo_fixture"}]}"#),
        (200, #"{"id":"com-1","name":"Marina runners","member_count":121,"joined":true,"provenance":"demo_fixture"}"#),
        (200, #"{"posts":[{"id":"post-1","community_id":"com-1","author":"Persona A","body":"Morning run, anyone?","provenance":"demo_fixture","as_of":"2026-10-20","comment_count":2}]}"#),
        (200, #"{"comments":[{"id":"c-1","author":"Persona B","body":"Count me in","provenance":"ai_demo"}]}"#),
        (200, #"{"id":"post-1","hidden":true}"#),
        (200, #"{"chats":[{"id":"chat-1","title":"Driver thread","unread":true,"last_message":"On my way"}]}"#),
        (200, #"{"messages":[{"id":"m-1","sender":"driver","body":"On my way","created_at":"2026-10-23T08:00:00Z"}]}"#),
        (200, #"{"contacts":[{"id":"ct-1","name":"Ahmed","phone":"+971500000000"}]}"#),
        (200, #"{"calls":[{"id":"call-1","contact":"Ahmed","direction":"outgoing","started_at":"2026-10-23T08:05:00Z","duration_s":60}]}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let communities = try await client.communities()
    #expect(communities.communities.first?.provenance == "demo_fixture")
    let joined = try await client.joinCommunity(id: "com-1")
    #expect(joined.joined == true)
    let feed = try await client.feed()
    let post = try #require(feed.posts.first)
    #expect(post.provenance == "demo_fixture")
    #expect(post.body == "Morning run, anyone?")
    let commentList = try await client.comments(postID: "post-1")
    #expect(commentList.comments.first?.provenance == "ai_demo")
    let hidden = try await client.hidePost(postID: "post-1")
    #expect(hidden.hidden == true)
    let chats = try await client.chats()
    #expect(chats.chats.first?.unread == true)
    let chatMessages = try await client.chatMessages(id: "chat-1")
    #expect(chatMessages.messages.first?.body == "On my way")
    let contacts = try await client.contacts()
    #expect(contacts.contacts.first?.phone == "+971500000000")
    let calls = try await client.calls()
    #expect(calls.calls.first?.durationS == 60)
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == [
        "/api/session", "/api/communities", "/api/communities/com-1/join", "/api/feed",
        "/api/posts/post-1/comments", "/api/posts/post-1/hide", "/api/chats",
        "/api/chats/chat-1/messages", "/api/contacts", "/api/calls"
    ])
    #expect(requests[2].httpMethod == "POST")
    #expect(requests[5].httpMethod == "POST")
}

@Test func researchAnswerIsDisplayedWithoutClaimingAnOrder() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"intent":"info_question","confidence":1,"reply":"I checked.","answer":"Provider-sourced answer","sources":[{"title":"Official source","url":"https://example.com","as_of":"2026-10-21"}],"via":"langgraph"}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let reply = try await client.turn(text: "Question", threadID: "thread")
    #expect(reply.displayText == "Provider-sourced answer")
    #expect(reply.sources?.first?.title == "Official source")
}
