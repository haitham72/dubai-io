import SwiftUI

@main
struct DubaiIOApp: App {
    var body: some Scene {
        WindowGroup { RootView().tint(Theme.cyan) }
    }
}

enum Theme {
    static let cyan = Color(red: 0.04, green: 0.61, blue: 0.76)
    static let ink = Color(red: 0.03, green: 0.43, blue: 0.54)
    static let soft = Color(red: 0.89, green: 0.96, blue: 0.98)
    static let fringe = Color(red: 0.57, green: 0.40, blue: 0.85)
    static let background = Color(uiColor: .systemGroupedBackground)
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
