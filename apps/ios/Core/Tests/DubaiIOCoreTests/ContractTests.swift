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
        (200, #"{"needs_you":{"tasks":[{"id":"task-1","outcome":"Confirm taxi receipt","status":"WAITING_USER","revision":3,"source_status":"AWAITING_APPROVAL","decision":{"kind":"approve","title":"Approve and send","detail":"Fixed published price. Nothing is sent until you approve.","action_id":"action-7","revision":2,"source_status":"AWAITING_APPROVAL","snapshot_hash":"abc123","amount_aed":"42"}}],"has_more":false},"scheduled":{"tasks":[{"id":"task-2","outcome":"Check back on visa renewal","status":"WAITING_USER","revision":1,"check_back_at":"2026-10-24T09:00:00Z"}],"has_more":false},"counts":{"needs_you":1,"running":2,"on_list":0,"paused":1},"as_of":"2026-10-23T09:00:00Z"}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let snapshot = try await client.today()
    let task = try #require(snapshot.needsYou?.tasks.first)
    #expect(task.displayTitle == "Confirm taxi receipt")
    let decision = try #require(task.decision)
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
        (200, #"{"task":{"id":"task-1","outcome":"Confirm taxi receipt","status":"WAITING_USER","revision":4},"replayed":false}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let updated = try await client.sendCommand(
        TaskCommand(kind: "check_back", expectedRevision: 3, commandKey: "key-1", at: "2026-10-24T09:00:00Z"),
        taskID: "task-1")
    #expect(updated.task.revision == 4)
    #expect(updated.task.displayTitle == "Confirm taxi receipt")
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
        (200, #"{"id":"action-7","capability_id":"order.request","recipient":"Demo laundry (sandbox merchant)","effect":"Send these details only; no payment or booking","fixed_total_aed":"42.00","fields":{"total_aed":{"value":"42.00","provenance":"user_supplied"}},"revision":2,"snapshot_hash":"abc123","status":"AWAITING_APPROVAL","execution_available":true}"#),
        (200, #"{"id":"action-7","capability_id":"order.request","recipient":"Demo laundry (sandbox merchant)","revision":2,"snapshot_hash":"abc123","status":"SUBMITTED","evidence":{"reference":"sandbox-ref-1","provenance":"provider_confirmed"}}"#),
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (409, #"{"detail":"Revision mismatch; reload the decision"}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let action = try await client.action(id: "action-7")
    #expect(action.snapshotHash == "abc123")
    #expect(action.sharedKeys == ["total_aed"])
    #expect(action.status == "AWAITING_APPROVAL")
    let approved = try await client.approveAction(
        id: action.id, revision: action.revision,
        snapshotHash: action.snapshotHash ?? "", idempotencyKey: "idem-1")
    #expect(approved.status == "SUBMITTED")
    #expect(approved.evidence?.provenance == "provider_confirmed")
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

@Test func outboxAssistAndBriefRoutineDecodeDeterministicContracts() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"messages":[{"id":"msg-1","kind":"task_checkback","text":"Check back: visa renewal","trigger_source":"user_reminder","delivered_at":"2026-10-23T09:00:00Z","dedupe_key":"checkback:task-2:1","task_id":"task-2"}]}"#),
        (200, #"{"mode":"learn","manual_reminders":2,"offer_auto":true}"#),
        (200, #"{"mode":"auto","manual_reminders":3,"offer_auto":false}"#),
        (200, #"{"kind":"morning_brief","at_time":"08:00","active":true,"expires_at":"2026-11-22T00:00:00Z"}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let outbox = try await client.messages()
    #expect(outbox.messages.first?.taskID == "task-2")
    #expect(outbox.messages.first?.dedupeKey == "checkback:task-2:1")
    let assist = try await client.assist()
    #expect(assist.mode == "learn" && assist.offerAuto == true)
    let updated = try await client.updateAssist(mode: "auto")
    #expect(updated.mode == "auto")
    let routine = try await client.briefRoutine()
    #expect(routine.active == true && routine.atTime == "08:00")
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == ["/api/session", "/api/messages", "/api/assist", "/api/assist", "/api/routines/brief"])
    #expect(requests[3].httpMethod == "PUT")
    let json = try #require(JSONSerialization.jsonObject(with: requests[3].httpBody!) as? [String: Any])
    #expect(json["mode"] as? String == "auto")
}

@Test func communityFeedAndChatKeepProvenanceAndUntrustedBodies() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"communities":[{"id":"com-1","name":"Marina runners","handle":"marinarunners","topic":"Fitness","about":"Runs","image":"media/marina.jpg","members":120,"joined":false,"provenance":"demo_fixture"}]}"#),
        (200, #"{"communities":[{"id":"com-1","name":"Marina runners","handle":"marinarunners","topic":"Fitness","about":"Runs","image":"media/marina.jpg","members":121,"joined":true,"provenance":"demo_fixture"}]}"#),
        (200, #"{"posts":[{"id":"post-1","community":{"id":"com-1","name":"Marina runners","handle":"marinarunners","joined":true},"author":{"name":"Persona A","handle":"persona-a","emoji":"🏃","persona_id":"p02","avatar":null},"mine":false,"kind":"post","text":"Morning run, anyone?","image":null,"likes":3,"comments":2,"created_at":"2026-10-20T08:00:00Z","provenance":"demo_fixture"}],"stories":[]}"#),
        (200, #"{"comments":[{"id":"c-1","author":{"name":"Persona B","handle":"persona-b","emoji":"🙂","persona_id":"p01","avatar":null},"text":"Count me in","created_at":"2026-10-20T09:00:00Z","likes":1,"provenance":"ai_demo","mine":false,"parent_id":null,"model":"demo-model"}]}"#),
        (200, #"{"hidden":"post-1"}"#),
        (200, #"{"threads":[{"id":"group:building","kind":"group","title":"Building 7 neighbours","community_id":null,"last":"Water is back","last_author":"Maya","at":"2026-10-23T08:00:00Z","unread":2}],"unread":2}"#),
        (200, #"{"thread":{"id":"group:building","kind":"group","title":"Building 7 neighbours","community_id":null},"messages":[{"id":"m-1","author":"Maya","mine":false,"text":"Water is back","at":"2026-10-23T08:00:00Z","provenance":"demo_fixture","persona_id":null,"avatar":null,"model":null}]}"#),
        (200, #"{"contacts":[{"id":"ct-1","name":"Ahmed","phone":"+971500000000","created_at":"2026-10-23T07:00:00Z"}]}"#),
        (200, #"{"calls":[{"id":"call-1","contact_id":"ct-1","name":"Ahmed","phone":"+971500000000","at":"2026-10-23T08:05:00Z","source":"started_in_dubai_io"}]}"#),
        (200, #"{"tel":"tel:+971500000000"}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let communities = try await client.communities()
    #expect(communities.communities.first?.provenance == "demo_fixture")
    #expect(communities.communities.first?.members == 120)
    let joined = try await client.joinCommunity(id: "com-1")
    #expect(joined.communities.first?.joined == true)
    let feed = try await client.feed()
    let post = try #require(feed.posts.first)
    #expect(post.provenance == "demo_fixture")
    #expect(post.text == "Morning run, anyone?")
    #expect(post.author?.personaID == "p02")
    let commentList = try await client.comments(postID: "post-1")
    let comment = try #require(commentList.comments.first)
    #expect(comment.provenance == "ai_demo")
    #expect(comment.parentID == nil)
    let hidden = try await client.hidePost(postID: "post-1")
    #expect(hidden.hiddenPostID == "post-1")
    let chats = try await client.chats(filter: "groups")
    let thread = try #require(chats.threads.first)
    #expect(thread.unread == 2)
    #expect(chats.unread == 2)
    let chatMessages = try await client.chatMessages(id: "group:building")
    #expect(chatMessages.messages.first?.text == "Water is back")
    #expect(chatMessages.messages.first?.mine == false)
    let contacts = try await client.contacts()
    #expect(contacts.contacts.first?.phone == "+971500000000")
    let calls = try await client.calls()
    #expect(calls.calls.first?.source == "started_in_dubai_io")
    let handoff = try await client.logCall(contactID: "ct-1")
    #expect(handoff.tel == "tel:+971500000000")
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == [
        "/api/session", "/api/communities", "/api/communities/com-1/join", "/api/feed",
        "/api/posts/post-1/comments", "/api/posts/post-1/hide", "/api/chats",
        "/api/chats/group:building/messages", "/api/contacts", "/api/calls", "/api/calls"
    ])
    #expect(requests[2].httpMethod == "POST")
    #expect(requests[5].httpMethod == "POST")
    #expect(requests[6].url!.query?.contains("filter=groups") == true)
    #expect(requests[10].httpMethod == "POST")
}

@Test func storiesReadingMapsAndDiscoveryDecode() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"community":{"id":"com-1","name":"Marina runners"},"frames":[{"id":"com-1-story-0","author":"Omar","emoji":"🏃","text":"Sunrise over the lakes","image":"media/marina.jpg","created_at":"2026-10-23T04:00:00Z","provenance":"demo_fixture"}]}"#),
        (200, #"{"articles":[{"id":"abc123","title":"Metro hours extended","url":"https://publisher.example/metro","source":"Gulf News","published_at":"2026-10-23","checked_at":"2026-10-23T09:00:00Z","provenance":"provider_confirmed","thumbnail":{"url":"/api/reading/thumbnails/abc123","credit":"Gulf News"}}],"status":"ready","topic":"for_you","topics":{"for_you":"For you","official":"Official updates"},"reason":"Your saved interests","provenance":"user_supplied","checked_at":"2026-10-23T09:00:00Z","attribution":"Headlines via Tavily. Read the full story at its publisher.","polling":false}"#),
        (200, #"{"key":"BROWSER-KEY","source":"browser_key"}"#),
        (200, #"{"places":[{"id":"place-1","name":"Cafe","rating":4.4,"lat":25.08,"lng":55.14,"short_address":"Marina Walk","maps_url":"https://maps.google.com/","open_now":true,"distance_km":0.42,"provenance":"provider_confirmed"}],"as_of":"2026-10-23T09:00:00Z","attribution":"Google","sort":"recommended","notice":null}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let frames = try await client.stories(communityID: "com-1")
    #expect(frames.frames.first?.text == "Sunrise over the lakes")
    #expect(frames.frames.first?.provenance == "demo_fixture")
    let news = try await client.reading()
    let article = try #require(news.articles.first)
    #expect(article.source == "Gulf News")
    #expect(article.thumbnail?.credit == "Gulf News")
    #expect(news.status == "ready")
    let config = try await client.mapsConfig()
    #expect(config.key == "BROWSER-KEY")
    let found = try await client.discover(DiscoveryInput(category: "food", query: "lasagna near Dubai Marina"))
    #expect(found.places.first?.distanceKm == 0.42)
    #expect(found.attribution == "Google")
    let requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == [
        "/api/session", "/api/communities/com-1/stories", "/api/reading", "/api/maps/config", "/api/discovery/places"
    ])
    #expect(requests[2].url!.query?.contains("topic=for_you") == true)
    let discoveryBody = try #require(JSONSerialization.jsonObject(with: requests[4].httpBody!) as? [String: Any])
    #expect(discoveryBody["category"] as? String == "food")
    #expect(discoveryBody["session_id"] as? String != nil)
}

@Test func notNowTracksTaskPrepareAndRemind() async throws {
    let transport = StubTransport([
        (200, #"{"user_id":"owner","mode":"anonymous_lab_session"}"#),
        (200, #"{"task":{"id":"task-9","outcome":"Follow up with Demo laundry","status":"WAITING_USER","revision":1},"replayed":false}"#),
        (200, #"{"id":"action-9","capability_id":"order.request","recipient":"Demo laundry (sandbox merchant)","revision":1,"snapshot_hash":"def456","status":"AWAITING_APPROVAL","execution_available":true}"#),
        (200, #"{"id":"action-9","capability_id":"order.request","revision":1,"snapshot_hash":"def456","status":"CANCELLED"}"#),
        (200, #"{"scheduled_for":"2026-10-24T10:00:00+04:00","created":true,"offer_auto":false}"#),
        (200, #"{"id":"post-2","generation":{"status":"completed","reply_count":2,"model":"test-model"}}"#)
    ])
    let client = APIClient(address: try BackendAddress("https://example.com"), transport: transport)
    let tracked = try await client.taskFromAction(actionID: "action-9")
    #expect(tracked.task.displayTitle == "Follow up with Demo laundry")
    var requests = await transport.recorded()
    let fromActionBody = try #require(JSONSerialization.jsonObject(with: requests[1].httpBody!) as? [String: String])
    #expect(fromActionBody == ["action_id": "action-9"])
    let prepared = try await client.prepareAction(PrepareInput(
        capabilityID: "order.request",
        fields: ["deadline": PrepareField(value: "Tomorrow 09:00")],
        order: PrepareOrder(providerID: "laundry", items: [PrepareOrderLine(id: "shirt", qty: 2)], slot: "Tomorrow 08:30")))
    #expect(prepared.status == "AWAITING_APPROVAL")
    requests = await transport.recorded()
    let prepareBody = try #require(JSONSerialization.jsonObject(with: requests[2].httpBody!) as? [String: Any])
    #expect(prepareBody["capability_id"] as? String == "order.request")
    #expect((prepareBody["order"] as? [String: Any])?["provider_id"] as? String == "laundry")
    let cancelled = try await client.cancelAction(id: "action-9")
    #expect(cancelled.status == "CANCELLED")
    let reminder = try await client.remindWhenReady(actionID: "action-9")
    #expect(reminder.created == true)
    let receipt = try await client.createPost(communityID: "com-1", text: "Hello neighbours")
    #expect(receipt.generation?.status == "completed")
    requests = await transport.recorded()
    #expect(requests.map { $0.url!.path } == [
        "/api/session", "/api/tasks/from-action", "/api/actions/prepare",
        "/api/actions/action-9/cancel", "/api/reminders", "/api/communities/com-1/posts"
    ])
}

@Test func sseParserSplitsDataFrames() {
    let text = """
        event: ping
        data: {"status":"DISPATCHING"}

        data: {"status":"SUBMITTED"}
        data: {"reference":"sandbox-ref-1"}

        """
    let frames = SSEParser.events(from: Data(text.utf8))
    #expect(frames == ["{\"status\":\"DISPATCHING\"}", "{\"status\":\"SUBMITTED\"}\n{\"reference\":\"sandbox-ref-1\"}"])
    #expect(SSEParser.events(from: Data(":keep-alive\n\n".utf8)) == [])
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
