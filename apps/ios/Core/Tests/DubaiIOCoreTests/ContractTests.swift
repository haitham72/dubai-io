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
