import SwiftUI

struct OnboardingView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let complete: () -> Void
    @State private var stage = 0
    @State private var page = 0
    @State private var flowing = false

    private let cards = [
        ("I’m Dubai-io.", "Your companion for a stay in Dubai. Share the details that help me with your next step.", "sparkles"),
        ("I remember what you tell me.", "Your hotel, your plans, the details you choose to share. You can review your saved details.", "person.text.rectangle"),
        ("You choose what gets shared.", "Review the shop, fixed total and shared details before sending a request. The merchant demo is a sandbox.", "checkmark.shield"),
        ("Published prices.", "Clear choices, with no haggling. Real status comes from the provider.", "tag")
    ]

    var body: some View {
        ZStack {
            Theme.soft.ignoresSafeArea()
            if stage == 0 {
                VStack(spacing: 24) {
                    Image(systemName: "airplane.arrival").font(.system(size: 60)).foregroundStyle(Theme.ink)
                    Text("Welcome to Dubai").font(.largeTitle.bold())
                    Text("Your arrival, one step at a time.").foregroundStyle(.secondary)
                    VStack(spacing: 16) {
                        Label("Airport Wi-Fi", systemImage: "wifi").font(.title2.bold())
                        Text("Arrival preview").font(.caption).foregroundStyle(Theme.ink)
                        Button("Join demo Wi-Fi") { stage = 1 }.buttonStyle(.borderedProminent).controlSize(.large)
                        Text("This preview does not change your Wi-Fi connection.").font(.footnote).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    }.padding(28).background(.background, in: .rect(cornerRadius: 28))
                }.padding(28)
            } else if stage == 1 {
                VStack(spacing: 24) {
                    Image(systemName: "sparkles").font(.system(size: 72)).foregroundStyle(Theme.cyan)
                    Text("Meet your companion").font(.largeTitle.bold()).multilineTextAlignment(.center)
                    Text("A little introduction before your next step.").foregroundStyle(.secondary)
                    Button("Open Dubai-io") { stage = 2 }.buttonStyle(.borderedProminent).controlSize(.large)
                }.padding(28)
            } else {
                VStack(spacing: 16) {
                    HStack { Text("Dubai-io").font(.title2.bold()); Spacer(); Text("\(page + 1) / \(cards.count)").foregroundStyle(.secondary) }.padding(.horizontal, 26)
                    TabView(selection: $page) {
                        ForEach(cards.indices, id: \.self) { index in
                            introCard(index).padding(.horizontal, 26).tag(index)
                        }
                    }.tabViewStyle(.page(indexDisplayMode: .always))
                    Button(page == cards.count - 1 ? "Start" : "Next") {
                        if page == cards.count - 1 { complete() }
                        else { withAnimation(reduceMotion ? nil : .smooth) { page += 1 } }
                    }.buttonStyle(.borderedProminent).controlSize(.large).padding(.bottom, 30)
                }.padding(.top, 24)
            }
        }
        .animation(reduceMotion ? nil : .smooth, value: stage)
        .onAppear { if !reduceMotion { flowing = true } }
    }

    private func introCard(_ index: Int) -> some View {
        VStack(alignment: .leading, spacing: 24) {
            ZStack {
                LinearGradient(colors: [Theme.ink, Theme.cyan, Color.cyan.opacity(0.5), Theme.fringe], startPoint: flowing ? .topLeading : .bottomLeading, endPoint: flowing ? .bottomTrailing : .topTrailing)
                Ellipse().fill(.white.opacity(0.18)).frame(width: 260, height: 340)
                    .rotationEffect(.degrees(flowing ? 55 : -20)).offset(x: flowing ? 85 : -85)
                Image(systemName: cards[index].2).font(.system(size: 70)).foregroundStyle(.white)
            }
            .frame(height: 260).clipped()
            .animation(reduceMotion ? nil : .easeInOut(duration: 9).repeatForever(autoreverses: true), value: flowing)
            VStack(alignment: .leading, spacing: 16) {
                Text(cards[index].0).font(.largeTitle.bold())
                Text(cards[index].1).font(.title3).foregroundStyle(.secondary)
            }.padding(.horizontal, 24).padding(.bottom, 30)
        }.frame(maxWidth: .infinity).background(.background, in: .rect(cornerRadius: 30)).clipShape(.rect(cornerRadius: 30))
    }
}
