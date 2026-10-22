import DubaiIOCore
import Foundation
import Observation
import SwiftUI

/// Compact Today: decisions, lanes and the deterministic brief.
/// Status comes only from authoritative events; 409 always means reload.
@MainActor @Observable
final class TodayModel {
    var snapshot: TodaySnapshot?
    var routine: BriefRoutine?
    var isLoading = false
    var error: String?
    var conflict: String?
    var results: [ActionDetail] = []
    private var generation = UUID()

    var briefLine: String {
        guard let counts = snapshot?.counts else { return "Connect your API to see Today." }
        var parts: [String] = []
        if counts.running > 0 { parts.append("\(counts.running) moving") }
        if counts.needsYou > 0 { parts.append("\(counts.needsYou) need\(counts.needsYou == 1 ? "s" : "") you") }
        let head = parts.isEmpty ? "Nothing is moving or waiting on you." : parts.joined(separator: " and ") + "."
        return "Morning brief: \(head) \(counts.onList) on your list."
    }

    func load(_ client: APIClient) async {
        let current = UUID()
        generation = current
        isLoading = true
        error = nil
        defer { if generation == current { isLoading = false } }
        do {
            async let today = client.today()
            async let routine = client.briefRoutine()
            let loaded = try await (today, routine)
            try Task.checkCancellation()
            guard generation == current else { return }
            snapshot = loaded.0
            self.routine = loaded.1
        } catch {
            if !Task.isCancelled, generation == current { self.error = error.localizedDescription }
        }
    }

    func approve(_ decision: TaskDecision, client: APIClient) async {
        error = nil
        conflict = nil
        do {
            let action = try await client.action(id: decision.actionID)
            guard action.revision == decision.revision,
                  (action.snapshotHash ?? "") == (decision.snapshotHash ?? "") else {
                conflict = "This decision changed. Reload it before approving."
                await load(client)
                return
            }
            let done = try await client.approveAction(
                id: action.id, revision: action.revision,
                snapshotHash: action.snapshotHash ?? "", idempotencyKey: UUID().uuidString)
            results.insert(done, at: 0)
            await load(client)
        } catch let failure as APIError {
            if case .http(409, _) = failure {
                conflict = "This decision changed. Reload it before approving."
                await load(client)
            } else { self.error = failure.localizedDescription }
        } catch { self.error = error.localizedDescription }
    }

    func notNow(_ decision: TaskDecision, client: APIClient) async {
        await track(actionID: decision.actionID, client: client)
    }

    func discard(_ decision: TaskDecision, client: APIClient) async {
        do {
            _ = try await client.cancelAction(id: decision.actionID)
            await load(client)
        } catch { self.error = error.localizedDescription }
    }

    func keepOnToday(actionID: String, client: APIClient) async {
        await track(actionID: actionID, client: client)
    }

    private func track(actionID: String, client: APIClient) async {
        do {
            _ = try await client.taskFromAction(actionID: actionID)
            await load(client)
        } catch { self.error = error.localizedDescription }
    }

    func sendCommand(_ command: TaskCommand, taskID: String, client: APIClient) async {
        do {
            _ = try await client.sendCommand(command, taskID: taskID)
            await load(client)
        } catch { self.error = error.localizedDescription }
    }
}

struct TodaySection: View {
    @Environment(SessionModel.self) private var session
    @State private var model = TodayModel()
    let openAsk: (String?) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Today").font(.title2.bold())
                Spacer()
                if let asOf = model.snapshot?.asOf { Text("Updated \(shortTime(asOf))").font(.caption).foregroundStyle(.secondary) }
            }
            if session.client == nil {
                Notice(text: "Connect your API in Me to see Today.")
            } else if model.isLoading && model.snapshot == nil {
                ProgressView("Loading Today…")
            } else if let error = model.error, model.snapshot == nil {
                FailureView(message: error, retry: reload)
            } else {
                Text(model.briefLine).font(.subheadline).foregroundStyle(.secondary)
                if let conflict = model.conflict {
                    Label(conflict, systemImage: "exclamationmark.triangle").font(.footnote).foregroundStyle(.orange)
                }
                laneChips
                needsYou
                resultCards
                runningRows
                BriefOptIn(routine: model.routine, save: saveRoutine)
            }
        }
        .task(id: session.client != nil ? session.revision : nil) {
            if let client = session.client { await model.load(client) }
        }
    }

    private var laneChips: some View {
        let counts = model.snapshot?.counts
        return HStack(spacing: 8) {
            chip("Needs you", count: counts?.needsYou)
            chip("Moving", count: counts?.running)
            chip("On list", count: counts?.onList)
            chip("Paused", count: counts?.paused)
        }
    }

    private func chip(_ title: String, count: Int?) -> some View {
        HStack(spacing: 4) {
            Text(title).font(.caption.weight(.semibold))
            if let count, count > 0 { Text("\(count)").font(.caption).foregroundStyle(.secondary) }
        }
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(Theme.soft, in: .capsule)
    }

    private var needsYou: some View {
        let tasks = model.snapshot?.needsYou?.tasks ?? []
        return Group {
            ForEach(tasks, id: \.id) { task in
                if let decision = task.decision, let client = session.client {
                    DecisionCard(task: task, decision: decision, model: model, client: client)
                }
            }
        }
    }

    private var resultCards: some View {
        ForEach(model.results, id: \.id) { action in
            ResultCard(action: action, model: model, client: session.client, openAsk: openAsk)
        }
    }

    private var runningRows: some View {
        let rows = (model.snapshot?.running?.tasks ?? []).prefix(3)
        return Group {
            ForEach(Array(rows), id: \.id) { task in
                VStack(alignment: .leading, spacing: 4) {
                    Text(task.displayTitle).font(.subheadline.weight(.semibold))
                    if let next = task.nextStep { Text(next).font(.caption).foregroundStyle(.secondary) }
                    Text(statusLabel(task)).font(.caption).foregroundStyle(.secondary)
                }
                .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                .background(.background, in: .rect(cornerRadius: 18))
            }
        }
    }

    private func statusLabel(_ task: TodayTask) -> String {
        if task.status == "PAUSED" { return "Paused" }
        return "Moving · \(task.sourceStatus ?? task.status ?? "unknown")"
    }

    private func reload() { Task { if let client = session.client { await model.load(client) } } }

    private func saveRoutine(active: Bool, atTime: String) {
        Task {
            if let client = session.client {
                do { _ = try await client.updateBriefRoutine(active: active, atTime: atTime); await model.load(client) }
                catch { model.error = error.localizedDescription }
            }
        }
    }
}

private func shortTime(_ iso: String) -> String {
    iso.count >= 16 ? String(iso.dropFirst(11).prefix(5)) : iso
}

/// The shared decision card: context chip, amount, title, exact share list,
/// Approve / Not now / Discard. Approve sends the exact revision on screen.
struct DecisionCard: View {
    let task: TodayTask
    let decision: TaskDecision
    let model: TodayModel
    let client: APIClient
    @State private var working = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(kindChip).font(.caption.weight(.semibold))
                    .padding(.horizontal, 10).padding(.vertical, 6)
                    .background(Theme.soft, in: .capsule)
                Spacer()
                if let amount = decision.amountAed {
                    Text(amount.formatted(.currency(code: "AED"))).font(.headline)
                }
            }
            Text(decision.title).font(.headline)
            if let detail = decision.detail { Text(detail).font(.subheadline).foregroundStyle(.secondary) }
            if decision.kind == "approve" {
                ShareList(actionID: decision.actionID, client: client)
            } else {
                Notice(text: "Nothing is shared by viewing this decision.")
            }
            HStack(spacing: 10) {
                Button("Approve") { act { await model.approve(decision, client: client) } }
                    .buttonStyle(.borderedProminent).disabled(working || decision.kind != "approve")
                Button("Not now") { act { await model.notNow(decision, client: client) } }
                    .buttonStyle(.bordered).disabled(working)
                Button("Discard", role: .destructive) { act { await model.discard(decision, client: client) } }
                    .buttonStyle(.bordered).disabled(working)
            }.buttonStyle(.plain).font(.subheadline)
            if decision.kind != "approve" {
                Notice(text: "Only an Approve decision can send. Check and deadline decisions stay on your list.")
            }
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 22))
    }

    private var kindChip: String {
        switch decision.kind {
        case "approve": "Needs approval"
        case "check": "Check before resending"
        case "deadline": "Deadline risk"
        default: decision.kind
        }
    }

    private func act(_ work: @escaping () async -> Void) {
        working = true
        Task { await work(); working = false }
    }
}

/// Exact share list for an Approve decision, read from the canonical action.
private struct ShareList: View {
    let actionID: String
    let client: APIClient
    @State private var keys: [String]?
    @State private var missing = false

    var body: some View {
        Group {
            if let keys {
                if keys.isEmpty {
                    Notice(text: "Never shared: approving sends nothing new beyond the fixed order.")
                } else {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Will be shared:").font(.caption.weight(.semibold))
                        ForEach(keys, id: \.self) { Text("• \($0)").font(.caption) }
                        Text("Never shared: anything else.").font(.caption).foregroundStyle(.secondary)
                    }
                }
            } else if missing {
                Notice(text: "Share list unavailable. Reload before approving.")
            }
        }
        .task { await load() }
    }

    private func load() async {
        do {
            let action = try await client.action(id: actionID)
            keys = action.sharedKeys
        } catch { missing = true }
    }
}

/// Result card: context, title, verdict first, updated time, Keep on Today.
struct ResultCard: View {
    let action: ActionDetail
    let model: TodayModel
    let client: APIClient?
    let openAsk: (String?) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Result").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Text(verdict).font(.headline)
            if let ref = action.evidence?.reference { Text("Reference \(ref)").font(.caption).foregroundStyle(.secondary) }
            Text("Status \(action.status) · \(action.evidence?.provenance ?? "no provider evidence yet")")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                if let client {
                    Button("Keep on Today") { Task { await model.keepOnToday(actionID: action.id, client: client) } }
                        .buttonStyle(.bordered)
                }
                Button("Ask about this") { openAsk("What happened with \(action.recipient ?? "my request")?") }
                    .buttonStyle(.plain).font(.subheadline)
            }
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 22))
    }

    private var verdict: String {
        switch action.status {
        case "SUBMITTED", "ACCEPTED", "READY": "Sent — confirmed by the provider."
        case "DISPATCHING": "Sending — waiting for the provider."
        case "CANCELLED": "Discarded — nothing was sent."
        case "BLOCKED": "Blocked — \(action.blockedReason ?? "no adapter yet")."
        default: "Unknown status — check before retrying."
        }
    }
}

/// Task history + detail with revision-fenced commands. Every command sends
/// `expected_revision` + `command_key`; a 409 means reload, never force.
@MainActor @Observable
final class TaskHistoryModel {
    var tasks: [TaskDetail] = []
    var isLoading = false
    var error: String?
    private var generation = UUID()

    func load(_ client: APIClient) async {
        let current = UUID()
        generation = current
        isLoading = true
        error = nil
        defer { if generation == current { isLoading = false } }
        do {
            let list = try await client.tasks()
            try Task.checkCancellation()
            guard generation == current else { return }
            tasks = list.tasks
        } catch {
            if !Task.isCancelled, generation == current { self.error = error.localizedDescription }
        }
    }
}

struct TaskHistorySection: View {
    @Environment(SessionModel.self) private var session
    @State private var model = TaskHistoryModel()
    @State private var selectedID: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Tasks").font(.title2.bold())
            if session.client == nil {
                Notice(text: "Connect your API in Me to see task history.")
            } else if model.isLoading && model.tasks.isEmpty {
                ProgressView("Loading tasks…")
            } else if let error = model.error, model.tasks.isEmpty {
                FailureView(message: error) { Task { if let client = session.client { await model.load(client) } } }
            } else {
                ForEach(model.tasks, id: \.id) { task in
                    Button { selectedID = task.id } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(task.displayTitle).font(.subheadline.weight(.semibold))
                            Text(taskStatus(task)).font(.caption).foregroundStyle(.secondary)
                        }
                        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                        .background(.background, in: .rect(cornerRadius: 18))
                    }.buttonStyle(.plain)
                }
                if model.tasks.isEmpty { Notice(text: "No tasks yet. Services starts a new task.") }
            }
        }
        .task(id: session.client != nil ? session.revision : nil) {
            if let client = session.client { await model.load(client) }
        }
        .navigationDestination(item: Binding(get: { selectedID.map(TaskRef.init(id:)) }, set: { selectedID = $0?.id })) { ref in
            if let client = session.client { TaskDetailView(taskID: ref.id, client: client) }
        }
    }

    private func taskStatus(_ task: TaskDetail) -> String {
        var parts = [task.status]
        if let due = task.dueState { parts.append(due) }
        return parts.joined(separator: " · ")
    }
}

private struct TaskRef: Identifiable, Hashable {
    let id: String
}

struct TaskDetailView: View {
    let taskID: String
    let client: APIClient
    @State private var detail: TaskDetail?
    @State private var error: String?
    @State private var conflict: String?
    @State private var working = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if let detail {
                    Text(detail.displayTitle).font(.title2.bold())
                    if let next = detail.nextStep { Text(next).foregroundStyle(.secondary) }
                    Text("Status \(detail.status) · revision \(detail.revision)")
                        .font(.caption).foregroundStyle(.secondary)
                    if let conflict {
                        Label(conflict, systemImage: "exclamationmark.triangle").font(.footnote).foregroundStyle(.orange)
                    }
                    commandButtons(detail)
                    if let error { Text(error).font(.footnote).foregroundStyle(.red) }
                } else if let error {
                    FailureView(message: error) { Task { await reload() } }
                } else {
                    ProgressView("Loading task…")
                }
            }.padding(20)
        }
        .navigationTitle("Task").navigationBarTitleDisplayMode(.inline)
        .task { await reload() }
    }

    private func commandButtons(_ task: TaskDetail) -> some View {
        VStack(spacing: 10) {
            if task.status == "PAUSED" {
                Button("Resume") { run(.init(kind: "resume", expectedRevision: task.revision, commandKey: UUID().uuidString)) }
                    .buttonStyle(.borderedProminent).disabled(working)
            } else if task.status == "WAITING_USER" {
                Button("Pause") { run(.init(kind: "pause", expectedRevision: task.revision, commandKey: UUID().uuidString)) }
                    .buttonStyle(.bordered).disabled(working)
                Button("Mark complete") { run(.init(kind: "complete", expectedRevision: task.revision, commandKey: UUID().uuidString)) }
                    .buttonStyle(.bordered).disabled(working)
            }
            if task.checkBackAt != nil {
                Button("Clear check-back") {
                    run(.init(kind: "check_back", expectedRevision: task.revision, commandKey: UUID().uuidString, at: nil))
                }.buttonStyle(.bordered).disabled(working)
            }
            if task.status == "WAITING_USER" {
                Button("Cancel task", role: .destructive) { run(.init(kind: "cancel", expectedRevision: task.revision, commandKey: UUID().uuidString)) }
                    .buttonStyle(.bordered).disabled(working)
            }
        }
    }

    private func run(_ command: TaskCommand) {
        working = true
        Task {
            do {
                let answer = try await client.sendCommand(command, taskID: taskID)
                detail = answer.task
                conflict = nil
            } catch let failure as APIError {
                if case .http(409, _) = failure {
                    conflict = "This task changed. Reloaded the latest state."
                    await reload()
                } else { self.error = failure.localizedDescription }
            } catch { self.error = error.localizedDescription }
            working = false
        }
    }

    private func reload() async {
        do { detail = try await client.task(id: taskID).task }
        catch { self.error = error.localizedDescription }
    }
}

/// Deterministic brief opt-in: 07:00–22:59 Dubai, 30-day expiry.
private struct BriefOptIn: View {
    let routine: BriefRoutine?
    let save: (Bool, String) -> Void
    @State private var time = "08:00"

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Morning brief").font(.subheadline.weight(.semibold))
            if let routine, routine.active {
                Text("On at \(routine.atTime ?? "08:00") Dubai\(routine.expiresAt.map { " · renews by \($0.prefix(10))" } ?? "").")
                    .font(.caption).foregroundStyle(.secondary)
                Button("Turn off") { save(false, routine.atTime ?? "08:00") }.font(.caption)
            } else {
                Text("One deterministic line from Today counts. Never model text.").font(.caption).foregroundStyle(.secondary)
                HStack {
                    TextField("08:00", text: $time).frame(width: 70)
                        .textFieldStyle(.roundedBorder).font(.subheadline)
                    Button("Turn on") { save(true, time) }.buttonStyle(.bordered).font(.subheadline)
                }
            }
        }
        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: .rect(cornerRadius: 18))
        .onAppear { if let at = routine?.atTime { time = at } }
    }
}
