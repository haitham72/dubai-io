import DubaiIOCore
import Foundation
import Observation
import SwiftUI
import WebKit

/// Sandboxed provider mini-app host. The mini-app runs in a WKWebView with a
/// non-persistent data store (no shared cookies), JavaScript only, navigation
/// locked to the widget origin, and a single allowlisted bridge channel.
///
/// Protocol (same as web): mini-app posts `{v:1, kind:'app.ready'}` → host
/// answers `{v:1, kind:'host.context', payload:{area, lang}}`. The mini-app can
/// only ask: `{v:1, kind:'order.request', payload:{items, slot/summary}}`.
/// Anything else gets `{v:1, kind:'host.error', payload:{reason:'scope_denied'}}`.
/// The host rebuilds items/total from the server catalog via prepare; widget
/// prices are dropped. Nothing is sent until the user approves the exact snapshot.
struct MiniAppHost: UIViewRepresentable {
    let url: URL
    let onOrderRequest: ([String: Any]) -> Void
    let onLoadFailure: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onOrderRequest: onOrderRequest, onLoadFailure: onLoadFailure) }

    func makeUIView(context: Context) -> WKWebView {
        let store = WKWebsiteDataStore.nonPersistent()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = store
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "dubaiio")
        config.userContentController = controller
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = context.coordinator
        context.coordinator.host = view
        context.coordinator.allowedHost = url.host
        view.load(URLRequest(url: url))
        return view
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    static func dismantleUIView(_ uiView: WKWebView, coordinator: Coordinator) {
        uiView.configuration.userContentController.removeScriptMessageHandler(forName: "dubaiio")
        uiView.stopLoading()
    }

    final class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        weak var host: WKWebView?
        var allowedHost: String?
        let onOrderRequest: ([String: Any]) -> Void
        let onLoadFailure: () -> Void
        private var announcedReady = false

        init(onOrderRequest: @escaping ([String: Any]) -> Void, onLoadFailure: @escaping () -> Void) {
            self.onOrderRequest = onOrderRequest
            self.onLoadFailure = onLoadFailure
        }

        func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == "dubaiio",
                  let body = message.body as? [String: Any],
                  (body["v"] as? Int) == 1,
                  let kind = body["kind"] as? String else { return }
            switch kind {
            case "app.ready":
                answer(["v": 1, "kind": "host.context", "payload": ["area": "Dubai Marina", "lang": "en"]])
            case "order.request":
                if let payload = body["payload"] as? [String: Any] { onOrderRequest(payload) }
                else { answer(["v": 1, "kind": "host.error", "payload": ["reason": "bad_payload"]]) }
            default:
                answer(["v": 1, "kind": "host.error", "payload": ["reason": "scope_denied", "kind": kind]])
            }
        }

        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction) async -> WKNavigationActionPolicy {
            guard let url = action.request.url else { return .cancel }
            if url.host == allowedHost { return .allow }
            return .cancel
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            onLoadFailure()
        }

        private func answer(_ message: [String: Any]) {
            guard let data = try? JSONSerialization.data(withJSONObject: message),
                  let json = String(data: data, encoding: .utf8) else { return }
            host?.evaluateJavaScript("window.postMessage(\(json),'*')", completionHandler: nil)
        }
    }
}

struct MiniAppSheet: View {
    let title: String
    let url: URL
    let providerID: String
    let client: APIClient
    let onOrdered: (ActionDetail) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var failed = false
    @State private var review: OrderReviewState?
    @State private var area = "Dubai Marina"
    @State private var deadline = ""

    var body: some View {
        NavigationStack {
            ZStack {
                MiniAppHost(url: url, onOrderRequest: { payload in
                    review = OrderReviewState(providerID: providerID, payload: payload)
                }, onLoadFailure: { failed = true })
                .ignoresSafeArea(edges: .bottom)
                if failed {
                    ContentUnavailableView("Mini-app unavailable", systemImage: "wifi.exclamationmark",
                        description: Text("This provider mini-app could not load. The published list still works."))
                }
            }
            .navigationTitle(title).navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } }
            }
            .sheet(item: $review) { state in
                OrderReviewView(state: state, client: client, area: area, deadline: deadline,
                    areaChanged: { area = $0 }, deadlineChanged: { deadline = $0 }) { sent in
                    onOrdered(sent)
                    review = nil
                    dismiss()
                }
            }
        }
    }
}

struct OrderReviewState: Identifiable {
    let id = UUID()
    let providerID: String
    let payload: [String: Any]
}

/// Order review: area + deadline form, server prepare (host rebuilds prices),
/// the exact snapshot to approve, then live status. "No payment taken."
struct OrderReviewView: View {
    let state: OrderReviewState
    let client: APIClient
    var area: String
    var deadline: String
    let areaChanged: (String) -> Void
    let deadlineChanged: (String) -> Void
    let onSent: (ActionDetail) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var draft: ActionDetail?
    @State private var error: String?
    @State private var preparing = false
    @State private var approving = false
    @State private var idempotencyKey = UUID().uuidString
    @State private var sent: ActionDetail?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if let sent {
                        OrderStatusView(action: sent, client: client)
                    } else if let draft {
                        decisionCard(draft)
                    } else {
                        TextField("Area", text: Binding(get: { area }, set: areaChanged))
                            .textFieldStyle(.roundedBorder)
                        TextField("Needed by, e.g. Tomorrow 09:00 (optional)", text: Binding(get: { deadline }, set: deadlineChanged))
                            .textFieldStyle(.roundedBorder)
                        if preparing { ProgressView("Checking the merchant’s published prices…") }
                        if let error { Text(error).font(.footnote).foregroundStyle(.red) }
                        Notice(text: "Nothing is sent until you approve. No payment is taken.")
                    }
                }.padding(20)
            }
            .navigationTitle("Send order?").navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .task(id: "\(area)|\(deadline)") { await prepare() }
        }
    }

    private func decisionCard(_ action: ActionDetail) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Fixed-price order · sandbox merchant").font(.caption.weight(.semibold))
                .padding(.horizontal, 10).padding(.vertical, 6).background(Theme.soft, in: .capsule)
            if let total = action.order?.totalAed {
                Text(total.formatted(.currency(code: "AED"))).font(.title.bold())
            }
            Text(action.status == "AWAITING_APPROVAL"
                 ? "Send this order to \(shopName(action))?"
                 : "Add \(action.missing?.joined(separator: ", ") ?? "details") to continue")
                .font(.headline)
            if let order = action.order {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Will be shared:").font(.caption.weight(.semibold))
                    Text("\(order.lines?.map { "\($0.qty ?? 0)× \($0.name ?? "item")" }.joined(separator: ", ") ?? "") · total\(order.slot.map { " · pickup \($0)" } ?? "")")
                        .font(.caption)
                    ForEach(action.sharedKeys.filter { $0 != "order" }, id: \.self) { key in
                        Text("• \(key): \(action.fields?[key]?.value ?? "")").font(.caption)
                    }
                    Text("Never shared: your name · phone number · profile and anything noticed · other orders.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            Text("Nothing is sent until you approve. The shop accepts or declines; the price can’t change.")
                .font(.caption).foregroundStyle(.secondary)
            if let provenance = action.order?.provenance {
                Text("Prices from the shop’s published list (\(provenance.replacingOccurrences(of: "_", with: " "))).")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if action.status != "AWAITING_APPROVAL", let reason = action.blockedReason {
                Notice(text: reason)
            }
            HStack {
                Button("Approve and send") { approve(action) }
                    .buttonStyle(.borderedProminent).disabled(approving || action.status != "AWAITING_APPROVAL")
                Button("Not now") { notNow(action) }.buttonStyle(.bordered).disabled(approving)
                Button("Discard draft", role: .destructive) { discard(action) }.buttonStyle(.bordered).disabled(approving)
            }.font(.subheadline)
            if let error { Text(error).font(.footnote).foregroundStyle(.red) }
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 22))
    }

    private func shopName(_ action: ActionDetail) -> String {
        (action.recipient ?? "the shop").replacingOccurrences(of: " (sandbox merchant)", with: "")
    }

    private var items: [PrepareOrderLine] {
        let raw = state.payload["items"] as? [[String: Any]] ?? []
        return raw.prefix(20).compactMap { item in
            guard let qty = item["qty"] as? Int else { return nil }
            return PrepareOrderLine(id: item["id"] as? String, name: (item["name"] as? String)?.prefix(80).description, qty: max(1, min(20, qty)))
        }
    }

    private var slot: String? {
        if let slot = state.payload["slot"] as? String { return slot }
        let summary = state.payload["summary"] as? String ?? ""
        let parts = summary.split(separator: "·").map { $0.trimmingCharacters(in: .whitespaces) }
        return parts.count > 1 ? String(parts[1]) : nil
    }

    private func prepare() async {
        preparing = true
        defer { preparing = false }
        var fields: [String: PrepareField] = ["area": PrepareField(value: area.isEmpty ? "Dubai Marina" : area)]
        if !deadline.isEmpty { fields["deadline"] = PrepareField(value: deadline) }
        do {
            draft = try await client.prepareAction(PrepareInput(
                capabilityID: "order.request", fields: fields,
                order: PrepareOrder(providerID: state.providerID, items: items, slot: slot),
                draftID: draft?.id))
        } catch { self.error = error.localizedDescription }
    }

    private func approve(_ action: ActionDetail) {
        approving = true
        Task {
            do {
                let done = try await client.approveAction(
                    id: action.id, revision: action.revision,
                    snapshotHash: action.snapshotHash ?? "", idempotencyKey: idempotencyKey)
                onSent(done)
                sent = done
            } catch let failure as APIError {
                if case .http(409, _) = failure {
                    self.error = "This order changed. Reload it before approving."
                    await prepare()
                } else { self.error = failure.localizedDescription }
            } catch { self.error = error.localizedDescription }
            approving = false
        }
    }

    private func notNow(_ action: ActionDetail) {
        Task {
            do {
                if action.status == "AWAITING_APPROVAL" {
                    _ = try await client.taskFromAction(actionID: action.id)
                }
                dismiss()
            } catch { self.error = error.localizedDescription }
        }
    }

    private func discard(_ action: ActionDetail) {
        Task {
            do {
                _ = try await client.cancelAction(id: action.id)
                dismiss()
            } catch { self.error = error.localizedDescription }
        }
    }
}

/// Live order status: SSE change feed first, polling takes over if it breaks.
/// Every status comes from a merchant tap or the engine — never model text.
struct OrderStatusView: View {
    let action: ActionDetail
    let client: APIClient
    @State private var current: ActionDetail
    @State private var streamFailed = false

    init(action: ActionDetail, client: APIClient) {
        self.action = action
        self.client = client
        self._current = State(initialValue: action)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Order status").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Text(stepLabel).font(.headline)
            if let ref = current.evidence?.reference {
                Text("Reference \(ref)").font(.caption).foregroundStyle(.secondary)
            }
            Text("No payment taken. \(current.evidence?.provenance == "provider_confirmed" ? "Confirmed by the merchant." : "Waiting for the merchant — not confirmed.")")
                .font(.caption).foregroundStyle(.secondary)
            if let ready = current.readyAt {
                Text("Ready \(ready)").font(.caption).foregroundStyle(.secondary)
            }
            if current.status == "ACCEPTED" {
                Button("Remind me when it's ready") { remind() }.buttonStyle(.bordered).font(.caption)
            }
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 22))
        .task { await watch() }
    }

    private var stepLabel: String {
        switch current.status {
        case "SUBMITTED": return "Sent to the merchant inbox."
        case "DISPATCHING": return "Sending to the merchant…"
        case "ACCEPTED": return "Merchant accepted at the fixed price."
        case "READY": return "Merchant marked it ready."
        case "COMPLETED": return "Merchant marked it done."
        case "DECLINED": return "Merchant declined."
        case "CANCELLED": return "Discarded — nothing was sent."
        default: return "Unknown status — check before retrying."
        }
    }

    private func remind() {
        Task {
            do { _ = try await client.remindWhenReady(actionID: current.id) }
            catch { /* surface stays honest without the reminder */ }
        }
    }

    private func watch() async {
        if await followStream() { return }
        streamFailed = true
        for _ in 0..<20 {
            try? await Task.sleep(for: .seconds(5))
            if Task.isCancelled { return }
            guard let fresh = try? await client.action(id: action.id) else { continue }
            current = fresh
            if ["READY", "COMPLETED", "DECLINED", "CANCELLED"].contains(fresh.status) { return }
        }
    }

    /// Reads the SSE change feed until a terminal status or 60 s, then yields to polling.
    private func followStream() async -> Bool {
        let request = client.actionStreamRequest(id: action.id)
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForResource = 60
        guard let (bytes, response) = try? await URLSession(configuration: config).bytes(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200 else { return false }
        var buffer = Data()
        let deadline = Date().addingTimeInterval(60)
        do {
            for try await byte in bytes {
                if Task.isCancelled { return true }
                buffer.append(byte)
                if Date() > deadline { return false }
                while let range = buffer.range(of: Data("\n\n".utf8)) {
                    let frame = buffer.subdata(in: buffer.startIndex..<range.lowerBound)
                    buffer.removeSubrange(buffer.startIndex..<range.upperBound)
                    for payload in SSEParser.events(from: frame) {
                        guard payload.hasPrefix("{"),
                              let data = payload.data(using: .utf8),
                              let fresh = try? JSONDecoder().decode(ActionDetail.self, from: data) else { continue }
                        current = fresh
                        if ["READY", "COMPLETED", "DECLINED", "CANCELLED"].contains(fresh.status) { return true }
                    }
                }
            }
        } catch { return false }
        return false
    }
}
