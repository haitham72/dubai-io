import DubaiIOCore
import Observation
import SwiftUI
import UIKit

/// Chat hub: All | Unread | Groups | Communities, pinned assistant opening Ask,
/// group/community threads, Contacts with an in-app call log and dialer handoff.
/// iOS cannot read the system call log; only calls started here are listed.
@MainActor @Observable
final class ChatHubModel {
    var threads: [ChatThread] = []
    var unreadTotal = 0
    var filter = "all"
    var isLoading = false
    var error: String?
    private var generation = UUID()

    var visible: [ChatThread] {
        switch filter {
        case "unread": return threads.filter { ($0.unread ?? 0) > 0 }
        case "groups": return threads.filter { $0.kind == "group" || $0.kind == "direct" }
        case "communities": return threads.filter { $0.kind == "community" }
        default: return threads
        }
    }

    func load(_ client: APIClient, serverFilter: String) async {
        let current = UUID()
        generation = current
        isLoading = true
        error = nil
        defer { if generation == current { isLoading = false } }
        do {
            let list = try await client.chats(filter: serverFilter)
            try Task.checkCancellation()
            guard generation == current else { return }
            threads = list.threads
            unreadTotal = list.unread
        } catch {
            if !Task.isCancelled, generation == current { self.error = error.localizedDescription }
        }
    }
}

struct ChatHubView: View {
    @Environment(SessionModel.self) private var session
    @State private var model = ChatHubModel()
    @State private var thread: ChatThread?
    @State private var contactsOpen = false
    let openAsk: () -> Void

    var body: some View {
        NavigationStack {
            Group {
                if session.client == nil {
                    ContentUnavailableView("Connect your API", systemImage: "network",
                        description: Text("Open Me to connect and see your conversations."))
                } else if model.isLoading && model.threads.isEmpty {
                    ProgressView("Loading chats…")
                } else if let error = model.error, model.threads.isEmpty {
                    FailureView(message: error, retry: reload)
                } else {
                    List {
                        Section {
                            Button {
                                openAsk()
                            } label: {
                                HStack {
                                    Image(systemName: "sparkles").foregroundStyle(Theme.ink)
                                    VStack(alignment: .leading) {
                                        Text("Dubai-io assistant").font(.headline)
                                        Text("Pinned · opens Ask").font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary)
                                }
                            }.buttonStyle(.plain)
                            Button { contactsOpen = true } label: {
                                HStack {
                                    Image(systemName: "person.2").foregroundStyle(Theme.ink)
                                    VStack(alignment: .leading) {
                                        Text("Contacts").font(.headline)
                                        Text("People you add · calls you start here").font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary)
                                }
                            }.buttonStyle(.plain)
                        }
                        Section(model.filter == "unread" ? "Unread" : "Threads") {
                            ForEach(model.visible) { item in
                                Button { thread = item } label: {
                                    HStack {
                                        Circle().fill(Theme.soft)
                                            .overlay(Text(item.title?.prefix(1) ?? "?").font(.headline))
                                            .frame(width: 44, height: 44)
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(item.title ?? "Conversation").font(.subheadline.weight(.semibold)).lineLimit(1)
                                            Text(item.last ?? "").font(.caption).foregroundStyle(.secondary).lineLimit(1)
                                        }
                                        Spacer()
                                        if let unread = item.unread, unread > 0 {
                                            Text("\(unread)").font(.caption2.weight(.bold))
                                                .foregroundStyle(.white).padding(6).background(Theme.cyan, in: .circle)
                                                .accessibilityLabel("\(unread) unread")
                                        }
                                    }
                                }.buttonStyle(.plain)
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                    .refreshable { if let client = session.client { await model.load(client, serverFilter: "all") } }
                }
            }
            .navigationTitle("Chat")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { MeButton() }
            }
            .navigationDestination(item: $thread) { item in
                if let client = session.client { ThreadView(thread: item, client: client, reloadHub: reload) }
            }
            .navigationDestination(isPresented: $contactsOpen) {
                if let client = session.client { ContactsView(client: client) }
            }
        }
        .task(id: session.client != nil ? session.revision : nil) {
            if let client = session.client { await model.load(client, serverFilter: "all") }
        }
        .onAppear {
            model.filter = "all"
        }
    }

    private func reload() { Task { if let client = session.client { await model.load(client, serverFilter: "all") } } }
}

/// Segment control lives above the hub list when connected.
struct ChatSegments: View {
    @Binding var selection: String
    let options = ["all": "All", "unread": "Unread", "groups": "Groups", "communities": "Communities"]

    var body: some View {
        Picker("Chats", selection: $selection) {
            ForEach(options.keys.sorted(), id: \.self) { key in Text(options[key] ?? key).tag(key) }
        }.pickerStyle(.segmented)
    }
}

struct ThreadView: View {
    let thread: ChatThread
    let client: APIClient
    let reloadHub: () -> Void
    @State private var messages: [ChatMessage] = []
    @State private var draft = ""
    @State private var error: String?
    @State private var sending = false

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        if let communityID = thread.communityID {
                            Notice(text: "Community conversation · \(communityID). Posts here are from members, not Dubai-io.")
                        }
                        ForEach(messages) { message in
                            messageRow(message).id(message.id)
                        }
                        if let error { Text(error).font(.footnote).foregroundStyle(.red) }
                        Color.clear.frame(height: 1).id("latest")
                    }.padding(16)
                }
                .onChange(of: messages.count) { _, _ in proxy.scrollTo("latest", anchor: .bottom) }
            }
            HStack {
                TextField("Message", text: $draft, axis: .vertical).lineLimit(1...4)
                    .textFieldStyle(.roundedBorder)
                Button("Send") { send() }.buttonStyle(.borderedProminent)
                    .disabled(sending || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }.padding(12)
        }
        .navigationTitle(thread.title ?? "Conversation").navigationBarTitleDisplayMode(.inline)
        .task { await load(); reloadHub() }
    }

    private func messageRow(_ message: ChatMessage) -> some View {
        HStack {
            if message.mine == true { Spacer(minLength: 40) }
            VStack(alignment: .leading, spacing: 4) {
                if message.mine != true { Text(message.author ?? "Someone").font(.caption.weight(.semibold)) }
                Text(message.text)
                DemoPill(provenance: message.provenance)
            }
            .padding(12)
            .background(message.mine == true ? Theme.soft : Theme.background, in: .rect(cornerRadius: 18))
            if message.mine != true { Spacer(minLength: 40) }
        }
        .frame(maxWidth: .infinity, alignment: message.mine == true ? .trailing : .leading)
    }

    private func load() async {
        do { messages = try await client.chatMessages(id: thread.id).messages }
        catch { self.error = error.localizedDescription }
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        sending = true
        Task {
            do {
                _ = try await client.sendChatMessage(threadID: thread.id, text: String(text.prefix(500)))
                draft = ""
                await load()
            } catch { self.error = error.localizedDescription }
            sending = false
        }
    }
}

/// Contacts the user adds, plus the log of calls started from the app.
/// Calls use the dialer (`tel:`); nothing here can connect a call by itself.
struct ContactsView: View {
    let client: APIClient
    @State private var contacts: [Contact] = []
    @State private var calls: [CallEntry] = []
    @State private var name = ""
    @State private var phone = ""
    @State private var error: String?

    var body: some View {
        List {
            Section("Calls started from Dubai-io") {
                if calls.isEmpty {
                    Notice(text: "No calls yet. Starting a call below logs it here after the dialer opens.")
                }
                ForEach(calls) { call in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(call.name ?? call.phone ?? "Unknown").font(.subheadline.weight(.semibold))
                        Text("\(call.at ?? "") · \(call.source == "started_in_dubai_io" ? "started in Dubai-io" : "logged")")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            Section("Contacts") {
                ForEach(contacts) { contact in
                    HStack {
                        VStack(alignment: .leading) {
                            Text(contact.name).font(.subheadline.weight(.semibold))
                            Text(contact.phone).font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button { Task { await startCall(contact) } } label: {
                            Image(systemName: "phone").frame(width: 44, height: 44)
                        }.buttonStyle(.plain).accessibilityLabel("Call \(contact.name)")
                    }
                    .swipeActions { Button("Delete", role: .destructive) { Task { await remove(contact) } } }
                }
            }
            Section("Add contact") {
                TextField("Name", text: $name)
                TextField("Phone", text: $phone).keyboardType(.phonePad)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                Button("Add") { Task { await add() } }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty || phone.trimmingCharacters(in: .whitespaces).isEmpty)
                if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            }
        }
        .navigationTitle("Contacts").navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        do {
            async let list = client.contacts()
            async let log = client.calls()
            contacts = try await list.contacts
            calls = try await log.calls
        } catch { self.error = error.localizedDescription }
    }

    private func add() async {
        do {
            _ = try await client.addContact(
                name: name.trimmingCharacters(in: .whitespaces),
                phone: phone.trimmingCharacters(in: .whitespaces))
            name = ""
            phone = ""
            await load()
        } catch { self.error = error.localizedDescription }
    }

    private func remove(_ contact: Contact) async {
        do {
            _ = try await client.deleteContact(id: contact.id)
            await load()
        } catch { self.error = error.localizedDescription }
    }

    /// Honest dialer handoff: log first, then open `tel:`. The dialer places it.
    private func startCall(_ contact: Contact) async {
        do {
            let handoff = try await client.logCall(contactID: contact.id)
            await load()
            guard let url = URL(string: handoff.tel), url.scheme == "tel" else {
                self.error = "The call handoff was not a dialer link."
                return
            }
            // The dialer places the call; a simulator or Mac has no dialer.
            if await UIApplication.shared.open(url) == false {
                self.error = "Logged here. No dialer is available on this device to place it."
            }
        } catch { self.error = error.localizedDescription }
    }
}
