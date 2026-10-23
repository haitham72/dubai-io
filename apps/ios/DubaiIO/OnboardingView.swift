import SwiftUI

/// First-run introduction on the cyan mesh. Everyday-life identity (PLAN.md, 22 Oct):
/// no arrival/visitor framing. Copy states only what the app actually does.
struct OnboardingView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let complete: () -> Void
    @State private var page = 0

    private let cards = [
        ("Dubai-io", "One assistant for everyday life and work in Dubai.", "sparkles"),
        ("You told me, I remember.", "Details you share are saved where you can see, edit or forget them.", "person.text.rectangle"),
        ("You approve every step.", "Before anything is shared or sent, you see exactly which details go and to whom.", "checkmark.shield"),
        ("Real status only.", "Nothing shows as booked or paid until the provider confirms it.", "checkmark.seal")
    ]

    var body: some View {
        ZStack {
            MeshBackground().ignoresSafeArea()
            VStack(spacing: Space.xl) {
                TabView(selection: $page) {
                    ForEach(cards.indices, id: \.self) { index in
                        card(index).tag(index)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .always))
                GlassEffectContainer(spacing: Space.m) {
                    HStack(spacing: Space.m) {
                        if page < cards.count - 1 {
                            Button("Skip", action: complete).buttonStyle(.glass).controlSize(.large)
                        }
                        Button(page == cards.count - 1 ? "Start" : "Next") {
                            if page == cards.count - 1 { complete() }
                            else { withAnimation(reduceMotion ? nil : .smooth) { page += 1 } }
                        }
                        .buttonStyle(.glassProminent).controlSize(.large)
                    }
                }
                .padding(.bottom, Space.xl)
            }
        }
        .environment(\.colorScheme, .dark)  // white type on the mesh in both modes
    }

    private func card(_ index: Int) -> some View {
        VStack(alignment: .leading, spacing: Space.l) {
            Spacer()
            Image(systemName: cards[index].2).font(.system(size: 56, weight: .semibold)).symbolRenderingMode(.hierarchical)
            Text(cards[index].0).font(.largeTitle.bold())
            Text(cards[index].1).font(.title3).foregroundStyle(.secondary)
            Spacer().frame(height: Space.xxl)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, Space.xl)
    }
}
