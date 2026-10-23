import SwiftUI
import UIKit

/// The one place for colors, spacing and glass rules (docs/plan/ios-upgrade.md §1–2).
/// Every color adapts to light/dark; nothing else in the app hard-codes a color.
enum Theme {
    static let cyan = Color(red: 0.04, green: 0.61, blue: 0.76)
    /// Accent text and icons: deep teal in light, bright cyan in dark.
    static let ink = adaptive(light: (0.03, 0.43, 0.54), dark: (0.45, 0.85, 0.95))
    /// Tinted fills (selected chips, own bubbles, pills): pale cyan in light, deep teal in dark.
    static let soft = adaptive(light: (0.89, 0.96, 0.98), dark: (0.05, 0.22, 0.27))
    static let fringe = Color(red: 0.57, green: 0.40, blue: 0.85)
    static let background = Color(uiColor: .systemGroupedBackground)
    static let card = Color(uiColor: .secondarySystemGroupedBackground)

    /// Intro/hero mesh in the cyan family (two palettes, 3x3, row-major).
    static let meshA: [Color] = [cyan.opacity(0.95), ink, cyan.opacity(0.7), ink, cyan, soft, cyan.opacity(0.7), soft, ink]
    static let meshB: [Color] = [ink, cyan.opacity(0.7), cyan, soft, ink, cyan.opacity(0.9), cyan, ink, soft]

    private static func adaptive(light: (Double, Double, Double), dark: (Double, Double, Double)) -> Color {
        Color(uiColor: UIColor { traits in
            let c = traits.userInterfaceStyle == .dark ? dark : light
            return UIColor(red: c.0, green: c.1, blue: c.2, alpha: 1)
        })
    }
}

enum Space {
    static let xs: CGFloat = 4, s: CGFloat = 8, m: CGFloat = 12, l: CGFloat = 16, xl: CGFloat = 24, xxl: CGFloat = 32
}

/// Animated mesh background; still under Reduce Motion. Pattern from ShipSwift
/// `SWAnimatedMeshGradient` (MIT, SignerLabs), rewritten for our palette.
struct MeshBackground: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var duration: Double = 6
    @State private var flipped = false

    var body: some View {
        MeshGradient(width: 3, height: 3, points: [
            [0, 0], [0.5, 0], [1, 0],
            [0, 0.5], [0.5, 0.5], [1, 0.5],
            [0, 1], [0.5, 1], [1, 1]
        ], colors: flipped ? Theme.meshA : Theme.meshB)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.easeInOut(duration: duration).repeatForever(autoreverses: true)) { flipped = true }
        }
    }
}

extension View {
    /// Glass for floating controls only, never for scrolling content rows.
    func glassControl<S: Shape>(in shape: S = Capsule()) -> some View {
        glassEffect(.regular.interactive(), in: shape)
    }
}
