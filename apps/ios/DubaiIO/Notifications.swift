import DubaiIOCore
import Foundation
import Observation
import SwiftUI
import UserNotifications

/// Outbox → local presentation. The backend outbox is the only source:
/// consented, deduped, quiet-hours aware. New delivered messages surface as an
/// in-app banner plus a local notification. APNs comes later and is not claimed.
@MainActor @Observable
final class OutboxPoller {
    var latest: OutboxMessage?
    var bannerVisible = false
    private var seen: Set<String> = []
    private var primed = false
    private var polling = false

    func start(_ client: APIClient) async {
        guard !polling else { return }
        polling = true
        await requestPermission()
        while !Task.isCancelled {
            await poll(client)
            try? await Task.sleep(for: .seconds(30))
        }
        polling = false
    }

    func poll(_ client: APIClient) async {
        do {
            let list = try await client.messages()
            let fresh = list.messages.filter { !seen.contains($0.id) }
            for message in list.messages { seen.insert(message.id) }
            if primed, let first = fresh.first {
                latest = first
                bannerVisible = true
                notify(first)
            }
            primed = true
        } catch { /* polling stays quiet; the hub shows errors */ }
    }

    func dismiss() { bannerVisible = false }

    private func requestPermission() async {
        _ = try? await UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .sound, .badge])
    }

    private func notify(_ message: OutboxMessage) {
        let content = UNMutableNotificationContent()
        content.title = "Dubai-io"
        content.body = String((message.text ?? message.kind).prefix(180))
        content.sound = .default
        let request = UNNotificationRequest(
            identifier: message.dedupeKey ?? message.id,
            content: content, trigger: UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false))
        UNUserNotificationCenter.current().add(request)
    }
}

struct OutboxBanner: View {
    @Bindable var poller: OutboxPoller
    let openTask: (String) -> Void

    var body: some View {
        if poller.bannerVisible, let message = poller.latest {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "bell.badge").foregroundStyle(Theme.ink)
                VStack(alignment: .leading, spacing: 4) {
                    Text(message.text ?? message.kind).font(.subheadline).lineLimit(3)
                    HStack {
                        if let taskID = message.taskID {
                            Button("Open task") { openTask(taskID); poller.dismiss() }.font(.caption.weight(.semibold))
                        }
                        Button("Dismiss") { poller.dismiss() }.font(.caption)
                    }.foregroundStyle(Theme.ink)
                }
                Spacer()
            }
            .padding(14).background(.background, in: .rect(cornerRadius: 18))
            .padding(.horizontal, 16)
            .transition(.move(edge: .top).combined(with: .opacity))
        }
    }
}
