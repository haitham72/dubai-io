import SwiftUI

@main
struct DubaiIOApp: App {
    var body: some Scene {
        WindowGroup { RootView().tint(Theme.cyan) }
    }
}

struct Notice: View {
    let text: String
    var body: some View {
        Text(text).font(.footnote).foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct FailureView: View {
    let message: String
    let retry: () -> Void
    var body: some View {
        ContentUnavailableView {
            Label("Couldn’t load this", systemImage: "wifi.exclamationmark")
        } description: {
            Text(message)
        } actions: {
            Button("Try again", action: retry).buttonStyle(.borderedProminent)
        }
    }
}
