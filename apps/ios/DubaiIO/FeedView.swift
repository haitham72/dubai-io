import DubaiIOCore
import Observation
import SwiftUI

/// Feed: stories rail + Snapchat-style viewer, communities to join,
/// persona posts with nested comments. Seeded content carries a Demo pill;
/// community text is untrusted and never becomes profile facts.
@MainActor @Observable
final class FeedModel {
    var posts: [FeedPost] = []
    var stories: [StoryTray] = []
    var communities: [Community] = []
    var isLoading = false
    var error: String?
    private var generation = UUID()

    var discover: [Community] { communities.filter { $0.joined != true }.prefix(10).map { $0 } }

    func load(_ client: APIClient) async {
        let current = UUID()
        generation = current
        isLoading = true
        error = nil
        defer { if generation == current { isLoading = false } }
        do {
            async let feed = client.feed()
            async let list = client.communities()
            let loaded = try await (feed, list)
            try Task.checkCancellation()
            guard generation == current else { return }
            posts = loaded.0.posts
            stories = loaded.0.stories
            communities = loaded.1.communities
        } catch {
            if !Task.isCancelled, generation == current { self.error = error.localizedDescription }
        }
    }

    func join(_ community: Community, client: APIClient, join: Bool) async {
        do {
            let list = try await (join ? client.joinCommunity(id: community.id) : client.leaveCommunity(id: community.id))
            communities = list.communities
            // Joining carries through to Chat: reload the feed to reorder joined posts first.
            await load(client)
        } catch { self.error = error.localizedDescription }
    }

    func hide(_ post: FeedPost, client: APIClient) async {
        do {
            _ = try await client.hidePost(postID: post.id)
            posts.removeAll { $0.id == post.id }
        } catch { self.error = error.localizedDescription }
    }
}

struct DemoPill: View {
    let provenance: String?
    var body: some View {
        if provenance == "demo_fixture" || provenance == "ai_demo" {
            Text(provenance == "ai_demo" ? "Demo reply" : "Demo data")
                .font(.caption2.weight(.semibold)).foregroundStyle(Theme.ink)
                .padding(.horizontal, 8).padding(.vertical, 4)
                .background(Theme.soft, in: .capsule)
                .accessibilityLabel("Demonstration data, not real people")
        }
    }
}

struct FeedView: View {
    @Environment(SessionModel.self) private var session
    @State private var model = FeedModel()
    @State private var viewer: StoryTray?
    @State private var selectedPost: FeedPost?
    @State private var selectedCommunity: Community?

    var body: some View {
        NavigationStack {
            Group {
                if session.client == nil {
                    ContentUnavailableView("Connect your API", systemImage: "network",
                        description: Text("Open Me to connect and see community stories and posts."))
                } else if model.isLoading && model.posts.isEmpty && model.communities.isEmpty {
                    ProgressView("Loading feed…")
                } else if let error = model.error, model.posts.isEmpty {
                    FailureView(message: error, retry: reload)
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 18) {
                            storiesRail
                            discoverRow
                            posts
                        }.padding(20)
                    }
                    .refreshable { if let client = session.client { await model.load(client) } }
                }
            }
            .navigationTitle("Feed")
            .toolbar { ToolbarItem(placement: .topBarTrailing) { MeButton() } }
            .fullScreenCover(item: $viewer) { tray in
                if let client = session.client { StoryViewer(tray: tray, client: client) }
            }
            .navigationDestination(item: $selectedPost) { post in
                if let client = session.client { PostDetail(post: post, client: client, onHidden: { model.posts.removeAll { $0.id == post.id } }) }
            }
            .navigationDestination(item: $selectedCommunity) { community in
                if let client = session.client {
                    CommunityDetail(community: community, model: model, client: client, openStory: { viewer = $0 }, openPost: { selectedPost = $0 })
                }
            }
        }
        .task(id: session.client != nil ? session.revision : nil) {
            if let client = session.client { await model.load(client) }
        }
    }

    private var storiesRail: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Stories").font(.title3.bold())
            if model.stories.isEmpty {
                Notice(text: "No stories right now.")
            } else {
                ScrollView(.horizontal) {
                    HStack(alignment: .top, spacing: 14) {
                        ForEach(model.stories, id: \.community.id) { tray in
                            Button { viewer = tray } label: {
                                VStack(spacing: 6) {
                                    storyCircle(tray)
                                    Text(tray.community.name).font(.caption2).lineLimit(2).multilineTextAlignment(.center)
                                        .frame(width: 72)
                                }
                            }.buttonStyle(.plain)
                            .accessibilityLabel("Story from \(tray.community.name)")
                        }
                    }
                }.scrollIndicators(.hidden)
            }
        }
    }

    private func storyCircle(_ tray: StoryTray) -> some View {
        let url = session.client?.resourceURL(tray.image)
        return AsyncImage(url: url) { phase in
            if let image = phase.image { image.resizable().scaledToFill() }
            else { Circle().fill(Theme.soft).overlay(Text(tray.community.name.prefix(1)).font(.title2.bold())) }
        }
        .frame(width: 64, height: 64).clipShape(.circle)
        .overlay(Circle().strokeBorder(Theme.cyan, lineWidth: 3))
    }

    private var discoverRow: some View {
        let items = model.discover
        return VStack(alignment: .leading, spacing: 10) {
            Text("Communities to join").font(.title3.bold())
            if items.isEmpty {
                Notice(text: "You joined every community.")
            } else {
                ScrollView(.horizontal) {
                    HStack(spacing: 12) {
                        ForEach(items) { community in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(community.name).font(.subheadline.weight(.semibold)).lineLimit(1)
                                Text("\(community.members ?? 0) members · \(community.topic ?? "")")
                                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                                if let client = session.client {
                                    Button("Join") { Task { await model.join(community, client: client, join: true) } }
                                        .buttonStyle(.bordered).font(.caption)
                                }
                                DemoPill(provenance: community.provenance)
                            }
                            .padding(14).frame(width: 210, alignment: .leading)
                            .background(.background, in: .rect(cornerRadius: 18))
                        }
                    }
                }.scrollIndicators(.hidden)
            }
        }
    }

    private var posts: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(model.posts) { post in
                PostCard(post: post, client: session.client, open: { selectedPost = post })
            }
            if model.posts.isEmpty { Notice(text: "No posts yet. Join a community to see its conversations.") }
        }
    }

    private func reload() { Task { if let client = session.client { await model.load(client) } } }
}

struct PostCard: View {
    let post: FeedPost
    let client: APIClient?
    let open: () -> Void

    var body: some View {
        Button(action: open) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text(post.author.map { "\($0.emoji ?? "") \($0.name)" } ?? "Someone").font(.subheadline.weight(.semibold))
                    Spacer()
                    DemoPill(provenance: post.provenance)
                }
                Text("in \(post.community?.name ?? "Feed")").font(.caption).foregroundStyle(.secondary)
                Text(post.text)
                if let url = client?.resourceURL(post.image) {
                    AsyncImage(url: url) { phase in
                        if let image = phase.image { image.resizable().scaledToFit().clipShape(.rect(cornerRadius: 14)) }
                    }
                    .frame(maxWidth: .infinity)
                }
                HStack {
                    Label("\(post.comments ?? 0)", systemImage: "bubble.right")
                    Label("\(post.likes ?? 0)", systemImage: "heart")
                }.font(.caption).foregroundStyle(.secondary)
            }
            .padding(16).frame(maxWidth: .infinity, alignment: .leading)
            .background(.background, in: .rect(cornerRadius: 20))
        }.buttonStyle(.plain)
    }
}

/// Snapchat-style viewer: one community's frames, tap sides to move.
struct StoryViewer: View {
    let tray: StoryTray
    let client: APIClient
    @Environment(\.dismiss) private var dismiss
    @State private var frames: [StoryFrame] = []
    @State private var index = 0
    @State private var error: String?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            if let frame = frames[safe: index] {
                if let url = client.resourceURL(frame.image) {
                    AsyncImage(url: url) { phase in
                        if let image = phase.image { image.resizable().scaledToFit() }
                        else { ProgressView().tint(.white) }
                    }
                }
                VStack {
                    HStack(spacing: 4) {
                        ForEach(frames.indices, id: \.self) { i in
                            Capsule().fill(i <= index ? .white : .white.opacity(0.35)).frame(height: 3)
                        }
                    }.padding()
                    Spacer()
                    VStack(alignment: .leading, spacing: 6) {
                        Text(frame.author).font(.headline).foregroundStyle(.white)
                        Text(frame.text).foregroundStyle(.white)
                        DemoPill(provenance: frame.provenance)
                    }
                    .padding(20).frame(maxWidth: .infinity, alignment: .leading)
                }
                HStack(spacing: 0) {
                    Button { step(-1) } label: { Color.clear }.frame(maxWidth: .infinity, maxHeight: .infinity)
                    Button { step(1) } label: { Color.clear }.frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            } else if let error {
                Text(error).foregroundStyle(.white).padding()
            } else {
                ProgressView().tint(.white)
            }
            VStack {
                HStack {
                    Spacer()
                    Button { dismiss() } label: { Image(systemName: "xmark").foregroundStyle(.white).frame(width: 44, height: 44) }
                        .accessibilityLabel("Close story")
                }.padding()
                Spacer()
            }
        }
        .task { await load() }
    }

    private func step(_ delta: Int) {
        let next = index + delta
        if next < 0 { return }
        if next >= frames.count { dismiss(); return }
        index = next
    }

    private func load() async {
        do { frames = try await client.stories(communityID: tray.community.id).frames }
        catch { self.error = error.localizedDescription }
    }
}

struct CommunityDetail: View {
    let community: Community
    let model: FeedModel
    let client: APIClient
    let openStory: (StoryTray) -> Void
    let openPost: (FeedPost) -> Void
    @State private var posts: [FeedPost] = []
    @State private var draft = ""
    @State private var error: String?
    @State private var posting = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text(community.about ?? "").foregroundStyle(.secondary)
                DemoPill(provenance: community.provenance)
                HStack {
                    if community.joined == true {
                        Label("Joined", systemImage: "checkmark.circle").font(.subheadline).foregroundStyle(Theme.ink)
                        Button("Leave") { Task { await model.join(community, client: client, join: false) } }
                            .buttonStyle(.bordered).font(.caption)
                    } else {
                        Button("Join community") { Task { await model.join(community, client: client, join: true) } }
                            .buttonStyle(.borderedProminent)
                    }
                }
                if community.joined == true {
                    HStack {
                        TextField("Share something with \(community.name)", text: $draft, axis: .vertical)
                            .lineLimit(1...4).textFieldStyle(.roundedBorder)
                        Button("Post") { post() }.buttonStyle(.borderedProminent).disabled(posting || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                } else {
                    Notice(text: "Join the community before posting.")
                }
                ForEach(posts) { post in PostCard(post: post, client: client, open: { openPost(post) }) }
                if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            }.padding(20)
        }
        .navigationTitle(community.name).navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let tray = model.stories.first(where: { $0.community.id == community.id }) {
                Button("Story") { openStory(tray) }
            }
        }
        .task { await load() }
    }

    private func load() async {
        do { posts = try await client.communityPosts(id: community.id).posts }
        catch { self.error = error.localizedDescription }
    }

    private func post() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        posting = true
        Task {
            do {
                _ = try await client.createPost(communityID: community.id, text: String(text.prefix(500)))
                draft = ""
                await load()
            } catch { self.error = error.localizedDescription }
            posting = false
        }
    }
}

/// Post with Facebook-style nested replies: real parent links, indentation,
/// expand/collapse. Twitter-style mentions never substitute for nesting.
struct PostDetail: View {
    let post: FeedPost
    let client: APIClient
    let onHidden: () -> Void
    @State private var comments: [PostComment] = []
    @State private var draft = ""
    @State private var replyTo: PostComment?
    @State private var collapsed: Set<String> = []
    @State private var error: String?
    @State private var sending = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                PostCard(post: post, client: client, open: {})
                    .allowsHitTesting(false)
                HStack {
                    Button("Hide this post") { hide() }.font(.caption)
                    Spacer()
                    DemoPill(provenance: post.provenance)
                }
                replyBar
                ForEach(roots, id: \.id) { comment in
                    commentTree(comment, depth: 0)
                }
                if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            }.padding(20)
        }
        .navigationTitle("Conversation").navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private var roots: [PostComment] {
        let ids = Set(comments.map(\.id))
        return comments.filter { $0.parentID == nil || !ids.contains($0.parentID ?? "") }
    }

    private func children(of id: String) -> [PostComment] {
        comments.filter { $0.parentID == id }
    }

    private func commentTree(_ comment: PostComment, depth: Int) -> AnyView {
        AnyView(CommentNode(comment: comment, siblings: children(of: comment.id),
            collapsed: collapsed.contains(comment.id),
            toggle: {
                if collapsed.contains(comment.id) { collapsed.remove(comment.id) }
                else { collapsed.insert(comment.id) }
            },
            reply: { replyTo = comment },
            child: { commentTree($0, depth: depth + 1) }, depth: depth))
    }

    private var replyBar: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let target = replyTo {
                HStack {
                    Text("Replying to \(target.author?.name ?? "someone")").font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    Button("Cancel") { replyTo = nil }.font(.caption)
                }
            }
            HStack {
                TextField("Write a reply", text: $draft, axis: .vertical).lineLimit(1...4)
                    .textFieldStyle(.roundedBorder)
                Button("Send") { send() }.buttonStyle(.borderedProminent)
                    .disabled(sending || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            Notice(text: "Replies are yours. Persona replies are generated, labelled, and never facts about you.")
        }
    }

    private func load() async {
        do { comments = try await client.comments(postID: post.id).comments }
        catch { self.error = error.localizedDescription }
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        sending = true
        Task {
            do {
                _ = try await client.addComment(postID: post.id, text: String(text.prefix(500)), parentID: replyTo?.id)
                draft = ""
                replyTo = nil
                await load()
            } catch { self.error = error.localizedDescription }
            sending = false
        }
    }

    private func hide() {
        Task {
            do {
                _ = try await client.hidePost(postID: post.id)
                onHidden()
            } catch { self.error = error.localizedDescription }
        }
    }
}

/// One nested reply node. Real parent links, indentation and expand/collapse.
private struct CommentNode<Child: View>: View {
    let comment: PostComment
    let siblings: [PostComment]
    let collapsed: Bool
    let toggle: () -> Void
    let reply: () -> Void
    let child: (PostComment) -> Child
    let depth: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("\(comment.author?.emoji ?? "") \(comment.author?.name ?? "Someone")")
                        .font(.caption.weight(.semibold))
                    Spacer()
                    DemoPill(provenance: comment.provenance)
                }
                Text(comment.text).font(.subheadline)
                HStack(spacing: 14) {
                    if !siblings.isEmpty {
                        Button(collapsed ? "Expand \(siblings.count)" : "Collapse", action: toggle).font(.caption)
                    }
                    Button("Reply", action: reply).font(.caption)
                }.foregroundStyle(Theme.ink)
            }
            .padding(12)
            .padding(.leading, CGFloat(min(depth, 4)) * 14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.background, in: .rect(cornerRadius: 16))
            .overlay(alignment: .leading) {
                if depth > 0 { RoundedRectangle(cornerRadius: 2).fill(Theme.cyan.opacity(0.5)).frame(width: 3).padding(.vertical, 10) }
            }
            if !collapsed {
                ForEach(siblings) { kid in child(kid) }
            }
        }
    }
}

private extension Array {
    subscript(safe index: Int) -> Element? { indices.contains(index) ? self[index] : nil }
}
