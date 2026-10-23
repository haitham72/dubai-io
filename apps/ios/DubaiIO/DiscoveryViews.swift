import DubaiIOCore
import Observation
import SwiftUI

@MainActor @Observable
final class CatalogModel {
    var catalog: Catalog?
    var isLoading = false
    var error: String?
    private var generation = UUID()

    func load(_ client: APIClient) async {
        let current = UUID()
        generation = current
        catalog = nil
        error = nil
        isLoading = true
        defer { if generation == current { isLoading = false } }
        do {
            let result = try await client.catalog()
            try Task.checkCancellation()
            guard generation == current else { return }
            catalog = result
        } catch {
            if !Task.isCancelled, generation == current { self.error = error.localizedDescription }
        }
    }
}

/// Services: 3-column tiles, flat widgets (orders & receipts with "No payment
/// taken", "Explore near you" map card), and sandboxed provider mini-apps with
/// the shared decision card. Prayer times have no backend contract yet and say so.
struct ServicesView: View {
    @Environment(SessionModel.self) private var session
    let active: Bool
    var openMaps: () -> Void = {}
    @State private var model = CatalogModel()
    @State private var sentAction: ActionDetail?

    private let columns = [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        NavigationStack {
            Group {
                if session.client == nil {
                    ContentUnavailableView("Connect your API", systemImage: "network", description: Text("Open Me to connect and see the published service catalog."))
                } else if model.isLoading && model.catalog == nil {
                    ProgressView("Loading services…")
                } else if let error = model.error, model.catalog == nil {
                    FailureView(message: error, retry: reload)
                } else if let catalog = model.catalog, let client = session.client {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 18) {
                            Notice(text: "Sandbox partners · published demo prices · \(catalog.asOf)")
                            OrdersWidget(client: client, latest: sentAction)
                            exploreCard(client: client)
                            prayerCard
                            Text("Providers").font(.title3.bold())
                            LazyVGrid(columns: columns, spacing: 12) {
                                ForEach(catalog.providers) { provider in
                                    NavigationLink {
                                        ProviderDetail(provider: provider, provenance: catalog.provenance, client: client, onOrdered: { sentAction = $0 })
                                    } label: {
                                        VStack(alignment: .leading, spacing: 6) {
                                            Image(systemName: "storefront").font(.title2).foregroundStyle(Theme.ink)
                                            Text(provider.name).font(.subheadline.weight(.semibold)).lineLimit(2).multilineTextAlignment(.leading)
                                            Text(provider.service.capitalized).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                                            if let from = provider.items.map(\.priceAed).min() {
                                                Text("from \(from.formatted(.currency(code: "AED")))").font(.caption).foregroundStyle(.secondary)
                                            }
                                        }
                                        .padding(12).frame(maxWidth: .infinity, minHeight: 132, alignment: .topLeading)
                                        .background(.background, in: .rect(cornerRadius: 18))
                                    }.buttonStyle(.plain)
                                    .accessibilityLabel("\(provider.name), \(provider.service)")
                                }
                            }
                            if let action = sentAction {
                                ResultCard(action: action, model: TodayModel(), client: client, openAsk: { _ in })
                            }
                        }.padding(20)
                    }.refreshable { if let client = session.client { await model.load(client) } }
                }
            }
            .navigationTitle("Services")
            .toolbar { ToolbarItem(placement: .topBarTrailing) { MeButton() } }
        }
        .task(id: active && session.client != nil ? session.revision : nil) {
            if active, let client = session.client { await model.load(client) }
        }
    }

    private func exploreCard(client: APIClient) -> some View {
        Button(action: openMaps) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Explore near you").font(.subheadline.weight(.semibold))
                AsyncImage(url: client.mapURL(places: [])) { phase in
                    if let image = phase.image { image.resizable().scaledToFit().clipShape(.rect(cornerRadius: 12)) }
                    else { ProgressView().frame(maxWidth: .infinity, minHeight: 90) }
                }
                Text("Live Google places on a Google map.").font(.caption).foregroundStyle(.secondary)
            }
            .padding(14).frame(maxWidth: .infinity, alignment: .leading)
            .background(.background, in: .rect(cornerRadius: 18))
        }.buttonStyle(.plain)
    }

    private var prayerCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Prayer times", systemImage: "moon").font(.subheadline.weight(.semibold))
            Notice(text: "Prayer times arrive with the web baseline; the API has no prayer contract yet, so this phone shows nothing invented.")
        }
        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 18))
    }

    private func reload() { Task { if let client = session.client { await model.load(client) } } }
}

/// Orders & receipts widget: provider-confirmed statuses only. No payment taken.
private struct OrdersWidget: View {
    let client: APIClient
    let latest: ActionDetail?
    @State private var orders: [ActionDetail] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Orders & receipts").font(.subheadline.weight(.semibold))
            Text("No payment taken.").font(.caption).foregroundStyle(.secondary)
            if let latest, !orders.contains(where: { $0.id == latest.id }) {
                orderRow(latest)
            }
            ForEach(orders.prefix(3), id: \.id) { orderRow($0) }
            if orders.isEmpty && latest == nil {
                Notice(text: "No orders yet. Open a provider tile to start one.")
            }
        }
        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 18))
        .task { await load() }
    }

    private func orderRow(_ action: ActionDetail) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(action.recipient?.replacingOccurrences(of: " (sandbox merchant)", with: "") ?? "Order")
                    .font(.caption.weight(.semibold)).lineLimit(1)
                Text(action.status).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            if let total = action.fixedTotalAed ?? action.order?.totalAed {
                Text(total.formatted(.currency(code: "AED"))).font(.caption.weight(.semibold))
            }
        }
    }

    private func load() async {
        do {
            orders = try await client.actions().actions
                .filter { $0.capabilityID == "order.request" && !["DRAFT", "BLOCKED"].contains($0.status) }
                .sorted { ($0.id) > ($1.id) }
        } catch { orders = [] }
    }
}

private struct ProviderDetail: View {
    @Environment(SessionModel.self) private var session
    let provider: Provider
    let provenance: String
    let client: APIClient
    let onOrdered: (ActionDetail) -> Void
    @State private var miniApp: URL?

    var body: some View {
        List {
            Section {
                Notice(text: "Sandbox merchant · \(provenance == "demo_fixture" ? "demo data" : provenance)")
                ForEach(provider.items) { item in
                    LabeledContent(item.name, value: item.priceAed.formatted(.currency(code: "AED")))
                }
            } header: { Text("Published items") }
            Section("Published demo slots") {
                ForEach(provider.slots, id: \.self) { Text($0) }
            }
            Section {
                if let url = miniAppURL {
                    Button("Open \(provider.name) mini-app") { miniApp = url }
                } else {
                    Notice(text: "The mini-app host is unavailable (no widget port from /api/health). Nothing is ordered by viewing this list.")
                }
                Notice(text: "Nothing is ordered or shared until you approve the exact snapshot.")
            }
        }
        .navigationTitle(provider.name).navigationBarTitleDisplayMode(.inline)
        .sheet(item: Binding(get: { miniApp.map { MiniAppURL(url: $0) } }, set: { miniApp = $0?.url })) { entry in
            MiniAppSheet(title: provider.name, url: entry.url, providerID: provider.id, client: client, onOrdered: onOrdered)
        }
    }

    /// Widget origin from `/api/health`'s widget port; entry file per provider.
    /// The provider→entry mapping is provisional until the backend publishes it.
    private var miniAppURL: URL? {
        guard let port = session.health?.widgetPort, port > 0 else { return nil }
        var parts = URLComponents(url: client.address.url, resolvingAgainstBaseURL: false)
        parts?.port = port
        parts?.path = "/miniapps/\(provider.id).html"
        return parts?.url
    }
}

private struct MiniAppURL: Identifiable {
    let id = UUID()
    let url: URL
}

@MainActor @Observable
final class ProfileModel {
    var facts: [SavedFact] = []
    var connections: [AccountConnection] = []
    var error: String?
    var isLoading = false
    private var generation = UUID()

    func load(_ client: APIClient) async {
        let current = UUID()
        generation = current
        facts = []
        connections = []
        error = nil
        isLoading = true
        defer { if generation == current { isLoading = false } }
        do {
            async let memory = client.memory()
            async let accounts = client.connections()
            let result = try await (memory, accounts)
            try Task.checkCancellation()
            guard generation == current else { return }
            facts = result.0.told
            connections = result.1.providers
        } catch {
            if !Task.isCancelled, generation == current { self.error = error.localizedDescription }
        }
    }
}

struct ProfileView: View {
    @Environment(SessionModel.self) private var session
    let active: Bool
    let replayIntro: () -> Void
    @State private var address = ""
    @State private var model = ProfileModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Your connection") {
                    TextField("https://your-api.example", text: $address)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                        .accessibilityLabel("API server address")
                    Button(session.isConnecting ? "Connecting…" : "Connect") {
                        Task { await session.connect(to: address) }
                    }.disabled(session.isConnecting || address.isEmpty)
                    if session.info != nil {
                        Label("Connected · preview session", systemImage: "checkmark.circle").foregroundStyle(Theme.ink)
                        Text(session.baseAddress).font(.caption).foregroundStyle(.secondary)
                    }
                    if let error = session.error { Text(error).font(.footnote).foregroundStyle(.red) }
                    Notice(text: "For a local server, use its network address. On your iPhone, localhost refers to the phone.")
                }
                Section("Saved details") {
                    if model.isLoading { ProgressView() }
                    if model.facts.isEmpty { Notice(text: "Details you tell the assistant will appear here after connecting.") }
                    ForEach(model.facts) { fact in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(fact.value)
                            Text("You told me · \(fact.key.replacingOccurrences(of: "_", with: " "))")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    if let error = model.error { Text(error).font(.footnote).foregroundStyle(.red) }
                }
                Section("Connected accounts") {
                    ForEach(model.connections) { connection in
                        LabeledContent(connection.label, value: connectionLabel(connection))
                    }
                    Notice(text: "This preview uses an anonymous server session. Account sign-in is not available here yet.")
                }
                Section {
                    Button("Replay arrival and introduction", action: replayIntro)
                    Notice(text: "Dubai-io · native preview. Service catalog entries are sandbox data; live places identify Google as their source.")
                }
            }
            .navigationTitle("Me")
            .onAppear { address = session.baseAddress }
            .refreshable { if let client = session.client { await model.load(client) } }
        }
        .task(id: active && session.client != nil ? session.revision : nil) {
            if active, let client = session.client { await model.load(client) }
        }
    }

    private func connectionLabel(_ connection: AccountConnection) -> String {
        switch connection.status {
        case "connected": connection.accountLabel ?? "Connected"
        case "disconnected": "Not connected"
        default: "Not configured"
        }
    }
}
