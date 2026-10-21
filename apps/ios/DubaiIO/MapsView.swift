import DubaiIOCore
import MapKit
import Observation
import SwiftUI

@MainActor @Observable
final class PlacesModel {
    var category = MapCategory.all
    var option: String?
    var area = "Dubai Marina"
    var results: PlaceResults?
    var error: String?
    var isLoading = false
    private var generation = UUID()
    var queryKey: String { category.searchQuery(option: option, area: area) }

    func choose(_ category: MapCategory, option: String? = nil) {
        self.category = category
        self.option = option
    }

    func load(_ client: APIClient) async {
        let key = queryKey
        let current = UUID()
        generation = current
        results = nil
        error = nil
        isLoading = true
        defer { if generation == current { isLoading = false } }
        do {
            let response = try await client.places(query: key)
            try Task.checkCancellation()
            guard queryKey == key, generation == current else { return }
            results = response
        } catch {
            if !Task.isCancelled, queryKey == key, generation == current { self.error = error.localizedDescription }
        }
    }
}

struct MapsView: View {
    @Environment(SessionModel.self) private var session
    let active: Bool
    let openLink: (String) -> Void
    @State private var model = PlacesModel()
    @State private var mode = "2d"
    @State private var areaDraft = "Dubai Marina"

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Picker("Map view", selection: $mode) {
                        Text("2D · Live Google").tag("2d")
                        Text("3D · Area preview").tag("3d")
                    }.pickerStyle(.segmented)
                    if mode == "2d" {
                        HStack {
                            TextField("Browse an area", text: $areaDraft)
                                .submitLabel(.search).onSubmit(applyArea)
                            Button(action: applyArea) { Image(systemName: "magnifyingglass").frame(width: 44, height: 44) }
                                .accessibilityLabel("Search this area")
                        }.padding(.leading, 14).background(.background, in: .rect(cornerRadius: 16))
                        categories
                        if session.client == nil {
                            ContentUnavailableView("Connect your API", systemImage: "network", description: Text("Open Me to connect and browse live places."))
                        } else if model.isLoading {
                            ProgressView("Finding places…").frame(maxWidth: .infinity, minHeight: 220)
                        } else if let error = model.error {
                            FailureView(message: error) { Task { if let client = session.client { await model.load(client) } } }
                        } else if let results = model.results, let client = session.client {
                            googleMap(results, client: client)
                            Text("\(results.places.count) places · \(model.area)").font(.title2.bold())
                            Notice(text: "Google Maps · checked \(results.asOf)")
                            ForEach(Array(results.places.enumerated()), id: \.element.id) { index, place in
                                placeCard(place, index: index + 1)
                            }
                            if results.places.isEmpty { Notice(text: "No matching places were returned. Try another category or area.") }
                        }
                    } else {
                        Map(initialPosition: .camera(MapCamera(centerCoordinate: CLLocationCoordinate2D(latitude: 25.0805, longitude: 55.1403), distance: 6500, heading: 0, pitch: 55)))
                            .mapStyle(.standard(elevation: .realistic, pointsOfInterest: .excludingAll))
                            .mapControls { MapCompass() }
                            .frame(height: 420).clipShape(.rect(cornerRadius: 24))
                        Notice(text: "Dubai Marina · illustrative 3D area preview. Live Google search results are shown separately in 2D.")
                    }
                }.padding(20)
            }.navigationTitle("Maps")
        }
        .task(id: active && mode == "2d" && session.client != nil ? "\(session.revision)|\(model.queryKey)" : nil) {
            if active, mode == "2d", let client = session.client { await model.load(client) }
        }
    }

    private var categories: some View {
        HStack(alignment: .center, spacing: 8) {
            if model.category != .all {
                Button { model.choose(.all) } label: { Image(systemName: "chevron.left").frame(width: 44, height: 44) }
                    .buttonStyle(.glass).accessibilityLabel("Back to categories")
            }
            ScrollView(.horizontal) {
                HStack {
                    if model.category == .all {
                        ForEach(MapCategory.allCases) { category in
                            chip(category.label, selected: category == .all) { model.choose(category) }
                        }
                    } else {
                        chip("All \(model.category.label.lowercased())", selected: model.option == nil) { model.option = nil }
                        ForEach(model.category.options, id: \.self) { option in
                            chip(option, selected: model.option == option) { model.option = option }
                        }
                    }
                }
            }.scrollIndicators(.hidden)
        }
    }

    private func chip(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title).font(.subheadline.weight(.semibold)).padding(.horizontal, 16).frame(minHeight: 44)
                .foregroundStyle(selected ? Theme.ink : .primary)
                .background(selected ? Theme.soft : Color(uiColor: .secondarySystemGroupedBackground), in: .capsule)
                .overlay(Capsule().strokeBorder(selected ? Theme.cyan : .clear))
        }.buttonStyle(.plain).accessibilityAddTraits(selected ? .isSelected : [])
    }

    private func googleMap(_ results: PlaceResults, client: APIClient) -> some View {
        let located = results.places.filter { $0.lat != nil && $0.lng != nil }
        let center: (Double, Double) = located.isEmpty ? (25.0805, 55.1403) : (
            located.reduce(0) { $0 + ($1.lat ?? 0) } / Double(located.count),
            located.reduce(0) { $0 + ($1.lng ?? 0) } / Double(located.count)
        )
        return AsyncImage(url: client.mapURL(places: results.places, center: center)) { phase in
            if let image = phase.image { image.resizable().scaledToFit().accessibilityLabel("Google map of these places") }
            else if phase.error != nil { Notice(text: "Map image unavailable. The places below are still available.") }
            else { ProgressView("Loading map…").frame(maxWidth: .infinity, minHeight: 180) }
        }
    }

    private func placeCard(_ place: Place, index: Int) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("\(index). \(place.name)").font(.headline)
            if let address = place.shortAddress ?? place.address { Text(address).font(.subheadline).foregroundStyle(.secondary) }
            HStack {
                if let rating = place.rating { Label(rating.formatted(.number.precision(.fractionLength(1))), systemImage: "star.fill") }
                if let open = place.openNow { Text(open ? "Open now" : "Closed now") }
            }.font(.caption).foregroundStyle(.secondary)
            HStack(spacing: 18) {
                if let website = place.website, WebLink.url(website) != nil { Button("Website", systemImage: "globe") { openLink(website) } }
                if let maps = place.mapsUrl, WebLink.url(maps) != nil { Button("Directions", systemImage: "arrow.triangle.turn.up.right.diamond") { openLink(maps) } }
            }.font(.subheadline)
            Text("Google Maps").font(.caption).foregroundStyle(.secondary)
        }.padding(18).frame(maxWidth: .infinity, alignment: .leading).background(.background, in: .rect(cornerRadius: 22))
    }

    private func applyArea() {
        let value = areaDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        if !value.isEmpty { model.area = String(value.prefix(70)) }
    }
}
