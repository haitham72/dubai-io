import DubaiIOCore
import SwiftUI

struct ChatView: View {
    @Environment(SessionModel.self) private var session
    @Bindable var model: ChatModel
    let close: () -> Void
    let openLink: (String) -> Void
    @FocusState private var composerFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button { composerFocused = false; close() } label: { Image(systemName: "chevron.left").frame(width: 44, height: 44) }
                    .buttonStyle(.glass).accessibilityLabel("Back to browsing")
                VStack(alignment: .leading) {
                    Text("Dubai-io").font(.title2.bold())
                    Text("Your Dubai companion").font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
            }.padding(.horizontal, 16).padding(.vertical, 10)
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 20) {
                        if model.entries.isEmpty {
                            VStack(spacing: 16) {
                                Image(systemName: "sparkles").font(.largeTitle).foregroundStyle(Theme.cyan)
                                Text("What’s your next step?").font(.title.bold())
                                Text("Ask about a place, a service or your plans.").foregroundStyle(.secondary)
                            }.frame(maxWidth: .infinity).padding(.vertical, 70)
                        }
                        ForEach(model.entries) { entry in message(entry).id(entry.id) }
                        if model.isSending { ProgressView("Thinking…").font(.footnote) }
                        if let error = model.error { Label(error, systemImage: "exclamationmark.circle").font(.footnote).foregroundStyle(.red) }
                        Color.clear.frame(height: 1).id("latest")
                    }.padding(20)
                }
                .scrollDismissesKeyboard(.interactively)
                .onChange(of: model.entries.count) { _, _ in proxy.scrollTo("latest", anchor: .bottom) }
                .onChange(of: model.isSending) { _, _ in proxy.scrollTo("latest", anchor: .bottom) }
            }
        }
        .background(Theme.background)
        .safeAreaInset(edge: .bottom) { composer }
        .onAppear { composerFocused = true }
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 10) {
            TextField("Message Dubai-io", text: $model.draft, axis: .vertical)
                .lineLimit(1...5).focused($composerFocused).submitLabel(.send)
                .onSubmit { send() }
                .onChange(of: model.draft) { _, value in if value.count > 600 { model.draft = String(value.prefix(600)) } }
            Button(action: send) { Image(systemName: "arrow.up").font(.title3.bold()).frame(width: 44, height: 44) }
                .buttonStyle(.borderedProminent).buttonBorderShape(.circle)
                .disabled(model.isSending || model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .accessibilityLabel("Send message")
        }
        .padding(10).padding(.leading, 10).glassEffect(.regular, in: .rect(cornerRadius: 28))
        .padding(.horizontal, 12).padding(.bottom, 8)
    }

    @ViewBuilder private func message(_ entry: ChatEntry) -> some View {
        if entry.isUser {
            HStack { Spacer(minLength: 30); Text(entry.text).textSelection(.enabled).padding(16).background(Theme.soft, in: .rect(cornerRadius: 22)) }
        } else {
            VStack(alignment: .leading, spacing: 12) {
                Text(entry.text).textSelection(.enabled)
                if let reply = entry.reply {
                    if reply.intent == "service_offers" {
                        Notice(text: "Compare published demo items in Services. Sending a merchant request is available in the web demo.")
                    }
                    if reply.intent == "places_near" {
                        Notice(text: "Explore live places in Maps.")
                    }
                    if reply.intent == "order_status" {
                        Notice(text: "Check your web order card for merchant-confirmed updates.")
                    }
                    ForEach(reply.products ?? []) { product in
                        Button { openLink(product.link) } label: {
                            VStack(alignment: .leading, spacing: 5) {
                                Text(product.title).font(.headline)
                                if let price = product.price { Text(price).font(.subheadline) }
                                Label("Open on Amazon.ae", systemImage: "arrow.up.right").font(.caption)
                            }.frame(maxWidth: .infinity, alignment: .leading).padding(16).background(.background, in: .rect(cornerRadius: 18))
                        }.buttonStyle(.plain)
                    }
                    ForEach(reply.sources ?? []) { source in
                        Button { openLink(source.url) } label: { Label(source.title, systemImage: "link").font(.footnote).multilineTextAlignment(.leading) }
                    }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func send() { Task { await model.send(using: session.client) } }
}
