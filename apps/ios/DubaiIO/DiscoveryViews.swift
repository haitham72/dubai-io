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

struct ServicesView: View {
    @Environment(SessionModel.self) private var session
    let active: Bool
    @State private var model = CatalogModel()

    var body: some View {
        NavigationStack {
            Group {
                if session.client == nil {
                    ContentUnavailableView("Connect your API", systemImage: "network", description: Text("Open Me to connect and see the published service catalog."))
                } else if model.isLoading {
                    ProgressView("Loading services…")
                } else if let error = model.error {
                    FailureView(message: error, retry: reload)
                } else if let catalog = model.catalog {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 16) {
                            Notice(text: "Sandbox partners · published demo prices · \(catalog.asOf)")
                            ForEach(catalog.providers) { provider in
                                NavigationLink {
                                    ProviderDetail(provider: provider, provenance: catalog.provenance)
                                } label: {
                                    VStack(alignment: .leading, spacing: 10) {
                                        HStack {
                                            Label(provider.name, systemImage: "storefront").font(.headline)
                                            Spacer()
                                            Image(systemName: "chevron.right").font(.caption)
                                        }
                                        Text(provider.service.capitalized).font(.subheadline).foregroundStyle(.secondary)
                                        if let item = provider.items.first {
                                            Text("\(item.name) · \(item.priceAed.formatted(.currency(code: "AED")))")
                                        }
                                    }.padding(20).frame(maxWidth: .infinity, alignment: .leading)
                                        .background(.background, in: .rect(cornerRadius: 24))
                                }.buttonStyle(.plain)
                            }
                            Notice(text: "Browse the catalog here. Sending merchant requests is available in the web demo.")
                        }.padding(20)
                    }.refreshable { if let client = session.client { await model.load(client) } }
                }
            }
            .navigationTitle("Services")
        }
        .task(id: active && session.client != nil ? session.revision : nil) {
            if active, let client = session.client { await model.load(client) }
        }
    }
    private func reload() { Task { if let client = session.client { await model.load(client) } } }
}

private struct ProviderDetail: View {
    let provider: Provider
    let provenance: String

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
                Notice(text: "Nothing is ordered or shared by viewing this catalog. Merchant requests are available in the web demo.")
            }
        }.navigationTitle(provider.name).navigationBarTitleDisplayMode(.inline)
    }
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
