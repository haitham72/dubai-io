import DubaiIOCore
import SwiftUI

enum BrowseTab: String, CaseIterable, Identifiable {
    case home, maps, services, me
    var id: Self { self }
    var label: String { switch self { case .home: "io"; case .maps: "Maps"; case .services: "Services"; case .me: "Me" } }
    var symbol: String { switch self { case .home: "sparkles"; case .maps: "map"; case .services: "square.grid.2x2"; case .me: "person.crop.circle" } }
}

struct RootView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage("hasSeenNativeIntro") private var hasSeenIntro = false
    @State private var session = SessionModel()
    @State private var chat = ChatModel()
    @State private var selectedTab = BrowseTab.home
    @State private var chatIsOpen = false
    @State private var browser: BrowserDestination?

    var body: some View {
        ZStack {
            Theme.background.ignoresSafeArea()
            ZStack {
                HomeView(openChat: ask, openServices: { selectedTab = .services }, openSettings: { selectedTab = .me })
                    .opacity(selectedTab == .home ? 1 : 0).allowsHitTesting(selectedTab == .home)
                    .accessibilityHidden(selectedTab != .home)
                MapsView(active: selectedTab == .maps, openLink: openLink)
                    .opacity(selectedTab == .maps ? 1 : 0).allowsHitTesting(selectedTab == .maps)
                    .accessibilityHidden(selectedTab != .maps)
                ServicesView(active: selectedTab == .services)
                    .opacity(selectedTab == .services ? 1 : 0).allowsHitTesting(selectedTab == .services)
                    .accessibilityHidden(selectedTab != .services)
                ProfileView(active: selectedTab == .me, replayIntro: { hasSeenIntro = false })
                    .opacity(selectedTab == .me ? 1 : 0).allowsHitTesting(selectedTab == .me)
                    .accessibilityHidden(selectedTab != .me)
            }
            .opacity(chatIsOpen ? 0 : 1).allowsHitTesting(!chatIsOpen).accessibilityHidden(chatIsOpen)
            if chatIsOpen {
                ChatView(model: chat, close: { transition { chatIsOpen = false } }, openLink: openLink)
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
        }
        .environment(session)
        .safeAreaInset(edge: .bottom) {
            if !chatIsOpen { browseDock.padding(.horizontal, 16).padding(.bottom, 8) }
        }
        .sheet(item: $browser) { SafariSheet(url: $0.url).ignoresSafeArea() }
        .fullScreenCover(isPresented: Binding(get: { !hasSeenIntro }, set: { hasSeenIntro = !$0 })) {
            OnboardingView { hasSeenIntro = true }
        }
        .task {
            if !session.baseAddress.isEmpty { await session.connect(to: session.baseAddress) }
        }
        .onChange(of: session.revision) { _, _ in chat.reset() }
    }

    private var browseDock: some View {
        GlassEffectContainer(spacing: 12) {
            HStack(spacing: 12) {
                HStack(spacing: 0) {
                    ForEach(BrowseTab.allCases) { tab in
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
        transition { chatIsOpen = true }
    }
    private func transition(_ changes: () -> Void) {
        withAnimation(reduceMotion ? nil : .smooth(duration: 0.3), changes)
    }
    private func openLink(_ value: String) {
        guard let url = WebLink.url(value) else { return }
        browser = BrowserDestination(url: url)
    }
}

private struct HomeView: View {
    @Environment(SessionModel.self) private var session
    let openChat: (String?) -> Void
    let openServices: () -> Void
    let openSettings: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack {
                    VStack(alignment: .leading) {
                        Text("Dubai-").foregroundStyle(.primary) + Text("io").foregroundStyle(Theme.cyan)
                        Text("Your Dubai companion").font(.subheadline).foregroundStyle(.secondary)
                    }.font(.largeTitle.bold())
                    Spacer()
                    Button(action: openSettings) { Image(systemName: "person.crop.circle").font(.title) }
                        .buttonStyle(.glass).accessibilityLabel("Your profile and connection")
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
                VStack(alignment: .leading, spacing: 12) {
                    Text("Try asking").font(.title2.bold())
                    suggestion("Guide me through arrivals", symbol: "airplane")
                    suggestion("I need a shirt pressed by 9 tomorrow", symbol: "drop")
                    suggestion("Find coffee near Dubai Marina", symbol: "cup.and.saucer")
                }
                Button(action: openServices) { Label("Explore services", systemImage: "square.grid.2x2").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).controlSize(.large)
                if session.client == nil {
                    Button("Connect your API", action: openSettings).buttonStyle(.bordered)
                    Notice(text: "Choose your server in Me to use live chat and discovery.")
                }
            }.padding(20)
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
