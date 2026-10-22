import DubaiIOCore
import SwiftUI

enum AppTab: String, CaseIterable, Identifiable {
    case home, chat, services, feed
    var id: Self { self }
    var label: String {
        switch self { case .home: "Home"; case .chat: "Chat"; case .services: "Services"; case .feed: "Feed" }
    }
    var symbol: String {
        switch self {
        case .home: "house"
        case .chat: "bubble.left.and.bubble.right"
        case .services: "square.grid.2x2"
        case .feed: "newspaper"
        }
    }
}

/// App shell: Home | Chat | Services | Feed tab bar, a separate Ask button,
/// profile top-right on each tab, full-screen gradient onboarding.
/// Maps opens on demand (sheet), never as a tab.
struct RootView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage("hasSeenNativeIntro") private var hasSeenIntro = false
    @State private var session = SessionModel()
    @State private var chat = ChatModel()
    @State private var selectedTab = AppTab.home
    @State private var askOpen = false
    @State private var mapsOpen = false
    @State private var profileOpen = false
    @State private var browser: BrowserDestination?
    @State private var poller = OutboxPoller()
    @State private var openTaskID: String?

    var body: some View {
        ZStack {
            Theme.background.ignoresSafeArea()
            Group {
                switch selectedTab {
                case .home: HomeView(openChat: ask, openServices: { selectedTab = .services })
                case .chat: ChatHubView(openAsk: { ask(nil) })
                case .services: ServicesView(active: true, openMaps: { mapsOpen = true })
                case .feed: FeedView()
                }
            }
            .opacity(askOpen ? 0 : 1).allowsHitTesting(!askOpen).accessibilityHidden(askOpen)
            if askOpen {
                ChatView(model: chat, close: { transition { askOpen = false } }, openLink: openLink, openMaps: { mapsOpen = true })
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
        }
        .environment(session)
        .safeAreaInset(edge: .bottom) {
            if !askOpen { tabBar.padding(.horizontal, 16).padding(.bottom, 8) }
        }
        .overlay(alignment: .top) {
            OutboxBanner(poller: poller) { openTaskID = $0 }
        }
        .sheet(item: $browser) { SafariSheet(url: $0.url).ignoresSafeArea() }
        .sheet(isPresented: $mapsOpen) {
            NavigationStack { MapsView(openLink: openLink) }
        }
        .sheet(isPresented: $profileOpen) {
            NavigationStack { ProfileView(active: true, replayIntro: { hasSeenIntro = false }) }
        }
        .sheet(item: Binding(get: { openTaskID.map(TaskRef2.init(id:)) }, set: { openTaskID = $0?.id })) { ref in
            NavigationStack {
                if let client = session.client { TaskDetailView(taskID: ref.id, client: client) }
            }
        }
        .fullScreenCover(isPresented: Binding(get: { !hasSeenIntro }, set: { hasSeenIntro = !$0 })) {
            OnboardingView { hasSeenIntro = true }
        }
        .task {
            if !session.baseAddress.isEmpty { await session.connect(to: session.baseAddress) }
        }
        .task(id: session.client != nil ? session.revision : nil) {
            if let client = session.client { await poller.start(client) }
        }
        .onChange(of: session.revision) { _, _ in chat.reset() }
    }

    private var tabBar: some View {
        GlassEffectContainer(spacing: 12) {
            HStack(spacing: 12) {
                HStack(spacing: 0) {
                    ForEach(AppTab.allCases) { tab in
                        Button { transition { selectedTab = tab } } label: {
                            VStack(spacing: 4) {
                                Image(systemName: tab.symbol).font(.title3)
                                Text(tab.label).font(.caption2)
                            }
                            .foregroundStyle(selectedTab == tab ? Theme.ink : .secondary)
                            .frame(maxWidth: .infinity).padding(.vertical, 10)
                            .background(selectedTab == tab ? Theme.soft : .clear, in: .capsule)
                        }
                        .accessibilityLabel(tab.label)
                        .accessibilityAddTraits(selectedTab == tab ? .isSelected : [])
                    }
                }.padding(5).glassEffect(.regular, in: .capsule)
                Button { ask(nil) } label: {
                    VStack(spacing: 4) {
                        Image(systemName: "magnifyingglass").font(.title3)
                        Text("Ask").font(.caption2)
                    }.frame(width: 64, height: 64)
                }.glassEffect(.regular.interactive(), in: .circle).accessibilityLabel("Ask Dubai-io")
            }.buttonStyle(.plain)
        }
    }

    private func ask(_ text: String?) {
        if let text { chat.draft = text }
        transition { askOpen = true }
    }
    private func transition(_ changes: () -> Void) {
        withAnimation(reduceMotion ? nil : .smooth(duration: 0.3), changes)
    }
    private func openLink(_ value: String) {
        guard let url = WebLink.url(value) else { return }
        browser = BrowserDestination(url: url)
    }
}

private struct TaskRef2: Identifiable, Hashable {
    let id: String
}

/// Profile button, top-right on every tab.
struct MeButton: View {
    @Environment(SessionModel.self) private var session
    @State private var open = false

    var body: some View {
        Button {
            open = true
        } label: {
            Image(systemName: session.info == nil ? "person.crop.circle" : "person.crop.circle.fill")
                .font(.title2)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Your profile and connection")
        .sheet(isPresented: $open) {
            NavigationStack { ProfileView(active: true, replayIntro: {}) }
        }
    }
}

private struct HomeView: View {
    @Environment(SessionModel.self) private var session
    let openChat: (String?) -> Void
    let openServices: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    HStack {
                        VStack(alignment: .leading) {
                            Text("Dubai-").foregroundStyle(.primary) + Text("io").foregroundStyle(Theme.cyan)
                            Text("Your Dubai companion").font(.subheadline).foregroundStyle(.secondary)
                        }.font(.largeTitle.bold())
                        Spacer()
                        MeButton()
                    }
                    VStack(alignment: .leading, spacing: 18) {
                        Text("YOUR NEXT STEP").font(.caption.weight(.semibold)).tracking(2)
                        Text("Hello, visitor.").font(.largeTitle.bold())
                        Text("One companion.\nYour next step in Dubai.").font(.title3)
                        Button("Plan my next step", systemImage: "sparkles") { openChat(nil) }.buttonStyle(.glass)
                    }
                    .foregroundStyle(.white).padding(28).frame(maxWidth: .infinity, minHeight: 250, alignment: .leading)
                    .background {
                        Image("Arrival").resizable().scaledToFill()
                            .overlay(LinearGradient(colors: [.black.opacity(0.7), Theme.ink.opacity(0.35)], startPoint: .topLeading, endPoint: .bottomTrailing))
                    }.clipShape(.rect(cornerRadius: 30))
                    TodaySection(openAsk: openChat)
                    TaskHistorySection()
                    HomeNewsCard(openChat: openChat)
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Try asking").font(.title2.bold())
                        suggestion("Guide me through arrivals", symbol: "airplane")
                        suggestion("I need a shirt pressed by 9 tomorrow", symbol: "drop")
                        suggestion("Find coffee near Dubai Marina", symbol: "cup.and.saucer")
                    }
                    Button(action: openServices) { Label("Explore services", systemImage: "square.grid.2x2").frame(maxWidth: .infinity) }
                        .buttonStyle(.borderedProminent).controlSize(.large)
                    if session.client == nil {
                        Button("Connect your API") { openChat(nil) }.buttonStyle(.bordered)
                        Notice(text: "Choose your server in Me to use live chat, Today and discovery.")
                    }
                }.padding(20)
            }
            .navigationTitle("Home").navigationBarHidden(true)
        }
    }
    private func suggestion(_ title: String, symbol: String) -> some View {
        Button { openChat(title) } label: {
            HStack { Image(systemName: symbol).foregroundStyle(Theme.ink); Text(title); Spacer(); Image(systemName: "chevron.right").font(.caption) }
                .padding(16).frame(maxWidth: .infinity, alignment: .leading)
                .background(.background, in: .rect(cornerRadius: 18))
        }.buttonStyle(.plain)
    }
}

@MainActor @Observable
private final class HomeNewsModel {
    var article: ReadingArticle?
    var attribution: String?
    var failed = false
    private var loaded = false

    func load(_ client: APIClient) async {
        guard !loaded else { return }
        loaded = true
        do {
            let news = try await client.reading()
            article = news.articles.first
            attribution = news.attribution
        } catch { failed = true }
    }
}

/// Compact Home news: one large image, title, subtitle, source and real link.
private struct HomeNewsCard: View {
    @Environment(SessionModel.self) private var session
    let openChat: (String?) -> Void
    @State private var model = HomeNewsModel()
    @State private var browser: BrowserDestination?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("News").font(.title2.bold())
            if let article = model.article, let client = session.client {
                VStack(alignment: .leading, spacing: 8) {
                    if let url = client.resourceURL(article.thumbnail?.url) {
                        AsyncImage(url: url) { phase in
                            if let image = phase.image { image.resizable().scaledToFit().clipShape(.rect(cornerRadius: 14)) }
                        }.frame(maxWidth: .infinity)
                    }
                    Text(article.title).font(.headline)
                    Text("\(article.source ?? "Publisher") · \(article.publishedAt ?? "")")
                        .font(.caption).foregroundStyle(.secondary)
                    if WebLink.url(article.url) != nil {
                        Button("Read at publisher") { browser = BrowserDestination(url: URL(string: article.url)!) }
                            .font(.subheadline)
                    }
                }
                .padding(16).frame(maxWidth: .infinity, alignment: .leading)
                .background(.background, in: .rect(cornerRadius: 20))
            } else if model.failed {
                Notice(text: "News is unavailable right now. Headlines return when the reader recovers.")
            }
        }
        .task(id: session.client != nil ? session.revision : nil) {
            if let client = session.client { await model.load(client) }
        }
        .sheet(item: $browser) { SafariSheet(url: $0.url).ignoresSafeArea() }
    }
}
